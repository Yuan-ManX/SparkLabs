"""
SparkLabs Engine - Crafting System

Manages recipe-based item crafting with material consumption,
crafting stations, skill-based success rates, recipe discovery,
and timed crafting operations. Supports item combination, material
substitution, batch crafting, and quality rolls.

Designed for RPG survival, and adventure games where players gather
materials and transform them into weapons, tools, potions, and
equipment. Integrates with the inventory system and resource system.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


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
    return max(lo, min(hi, value))


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
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_RECIPES = 3000
_MAX_STATIONS = 500
_MAX_CRAFTS = 5000
_MAX_EVENTS = 5000
_MAX_DISCOVERIES = 2000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StationType(str, Enum):
    """Type of crafting station."""
    WORKBENCH = "workbench"
    FORGE = "forge"
    ALCHEMY = "alchemy"
    COOKING = "cooking"
    ENCHANTING = "enchanting"
    TAILORING = "tailoring"
    CARPENTRY = "carpentry"
    SMELTING = "smelting"
    LOOM = "loom"
    ANVIL = "anvil"
    CUSTOM = "custom"


class CraftStatus(str, Enum):
    """Status of a crafting operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecipeCategory(str, Enum):
    """Category of crafting recipe."""
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    TOOL = "tool"
    MATERIAL = "material"
    DECORATION = "decoration"
    QUEST = "quest"
    CUSTOM = "custom"


class CraftEventKind(str, Enum):
    RECIPE_REGISTERED = "recipe_registered"
    RECIPE_REMOVED = "recipe_removed"
    RECIPE_UNLOCKED = "recipe_unlocked"
    RECIPE_DISCOVERED = "recipe_discovered"
    STATION_REGISTERED = "station_registered"
    STATION_REMOVED = "station_removed"
    CRAFT_STARTED = "craft_started"
    CRAFT_COMPLETED = "craft_completed"
    CRAFT_FAILED = "craft_failed"
    CRAFT_CANCELLED = "craft_cancelled"
    CRAFT_PROGRESS = "craft_progress"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MaterialEntry:
    """A single material requirement in a recipe."""
    item_id: str
    quantity: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OutputEntry:
    """A single output item from a recipe."""
    item_id: str
    quantity: int = 1
    quality_min: float = 0.5
    quality_max: float = 1.0
    chance: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftRecipe:
    """A crafting recipe definition."""
    recipe_id: str
    name: str = ""
    category: str = RecipeCategory.CUSTOM.value
    description: str = ""
    inputs: List[MaterialEntry] = field(default_factory=list)
    outputs: List[OutputEntry] = field(default_factory=list)
    required_station: str = StationType.WORKBENCH.value
    required_skill: str = ""
    required_skill_level: int = 0
    craft_time: float = 1.0
    success_rate: float = 1.0
    unlocked: bool = True
    discoverable: bool = False
    discovery_hint: str = ""
    batch_size: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftStation:
    """A crafting station instance."""
    station_id: str
    name: str = ""
    station_type: str = StationType.WORKBENCH.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    enabled: bool = True
    efficiency: float = 1.0
    bonus_success_rate: float = 0.0
    bonus_quality: float = 0.0
    skill_bonus: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftOperation:
    """An in-progress or completed crafting operation."""
    craft_id: str
    recipe_id: str
    crafter_id: str = ""
    station_id: str = ""
    status: str = CraftStatus.PENDING.value
    progress: float = 0.0
    elapsed: float = 0.0
    total_time: float = 1.0
    inputs_consumed: List[Dict[str, Any]] = field(default_factory=list)
    outputs_produced: List[Dict[str, Any]] = field(default_factory=list)
    quality: float = 0.5
    started_at: float = 0.0
    completed_at: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftConfig:
    max_recipes: int = 500
    max_stations: int = 100
    max_concurrent_crafts: int = 50
    default_success_rate: float = 0.95
    skill_check_enabled: bool = True
    quality_variance: float = 0.2
    auto_complete: bool = True
    tick_rate_hz: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftStats:
    total_recipes: int = 0
    unlocked_recipes: int = 0
    total_stations: int = 0
    total_crafts_started: int = 0
    total_crafts_completed: int = 0
    total_crafts_failed: int = 0
    total_crafts_cancelled: int = 0
    total_discoveries: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftSnapshot:
    recipes: List[Dict[str, Any]] = field(default_factory=list)
    stations: List[Dict[str, Any]] = field(default_factory=list)
    active_crafts: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CraftEvent:
    event_id: str
    kind: str
    timestamp: float
    recipe_id: Optional[str] = None
    station_id: Optional[str] = None
    craft_id: Optional[str] = None
    crafter_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Crafting System
# ---------------------------------------------------------------------------

class CraftingSystem:
    """Manages crafting recipes, stations, and crafting operations."""

    _instance: Optional["CraftingSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._recipes: Dict[str, CraftRecipe] = {}
        self._stations: Dict[str, CraftStation] = {}
        self._crafts: Dict[str, CraftOperation] = {}
        self._events: List[CraftEvent] = []
        self._stats = CraftStats()
        self._config = CraftConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._craft_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "CraftingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample recipes and stations."""
        # Iron Sword recipe
        iron_sword = CraftRecipe(
            recipe_id="rcp_iron_sword",
            name="Iron Sword",
            category=RecipeCategory.WEAPON.value,
            description="A sturdy iron sword for combat.",
            inputs=[
                MaterialEntry(item_id="mat_iron_ingot", quantity=3),
                MaterialEntry(item_id="mat_wood_plank", quantity=1),
                MaterialEntry(item_id="mat_leather_strip", quantity=2),
            ],
            outputs=[OutputEntry(item_id="wpn_iron_sword", quantity=1, quality_min=0.6, quality_max=1.0)],
            required_station=StationType.ANVIL.value,
            required_skill="smithing",
            required_skill_level=2,
            craft_time=5.0,
            success_rate=0.9,
        )
        self._recipes[iron_sword.recipe_id] = iron_sword

        # Health Potion recipe
        health_potion = CraftRecipe(
            recipe_id="rcp_health_potion",
            name="Health Potion",
            category=RecipeCategory.CONSUMABLE.value,
            description="Restores health when consumed.",
            inputs=[
                MaterialEntry(item_id="mat_herb_red", quantity=2),
                MaterialEntry(item_id="mat_water_vial", quantity=1),
                MaterialEntry(item_id="mat_honey", quantity=1),
            ],
            outputs=[OutputEntry(item_id="potion_health_minor", quantity=1, quality_min=0.5, quality_max=1.0)],
            required_station=StationType.ALCHEMY.value,
            required_skill="alchemy",
            required_skill_level=1,
            craft_time=2.0,
            success_rate=0.95,
            batch_size=3,
        )
        self._recipes[health_potion.recipe_id] = health_potion

        # Leather Armor recipe
        leather_armor = CraftRecipe(
            recipe_id="rcp_leather_armor",
            name="Leather Armor",
            category=RecipeCategory.ARMOR.value,
            description="Light armor made from tanned leather.",
            inputs=[
                MaterialEntry(item_id="mat_leather_hide", quantity=4),
                MaterialEntry(item_id="mat_thread", quantity=2),
                MaterialEntry(item_id="mat_iron_buckle", quantity=1),
            ],
            outputs=[OutputEntry(item_id="arm_leather_chest", quantity=1, quality_min=0.5, quality_max=1.0)],
            required_station=StationType.TAILORING.value,
            required_skill="tailoring",
            required_skill_level=1,
            craft_time=4.0,
            success_rate=0.92,
        )
        self._recipes[leather_armor.recipe_id] = leather_armor

        # Secret recipe (discoverable)
        ancient_blade = CraftRecipe(
            recipe_id="rcp_ancient_blade",
            name="Ancient Blade",
            category=RecipeCategory.WEAPON.value,
            description="A blade forged with ancient techniques.",
            inputs=[
                MaterialEntry(item_id="mat_ancient_ore", quantity=5),
                MaterialEntry(item_id="mat_dragon_scale", quantity=1),
                MaterialEntry(item_id="mat_enchant_dust", quantity=3),
            ],
            outputs=[OutputEntry(item_id="wpn_ancient_blade", quantity=1, quality_min=0.8, quality_max=1.0)],
            required_station=StationType.FORGE.value,
            required_skill="smithing",
            required_skill_level=8,
            craft_time=15.0,
            success_rate=0.7,
            unlocked=False,
            discoverable=True,
            discovery_hint="Found in ancient ruins.",
        )
        self._recipes[ancient_blade.recipe_id] = ancient_blade

        # Stations
        stations = [
            CraftStation(station_id="stn_workbench_01", name="Village Workbench", station_type=StationType.WORKBENCH.value, position=(10.0, 0.0, 5.0), efficiency=1.0),
            CraftStation(station_id="stn_forge_01", name="Blacksmith Forge", station_type=StationType.FORGE.value, position=(25.0, 0.0, 10.0), efficiency=1.1, bonus_success_rate=0.05),
            CraftStation(station_id="stn_anvil_01", name="Master Anvil", station_type=StationType.ANVIL.value, position=(26.0, 0.0, 12.0), efficiency=1.15, bonus_success_rate=0.08, bonus_quality=0.1, skill_bonus=1),
            CraftStation(station_id="stn_alchemy_01", name="Alchemy Table", station_type=StationType.ALCHEMY.value, position=(40.0, 0.0, 3.0), efficiency=1.0),
            CraftStation(station_id="stn_tailoring_01", name="Tailoring Bench", station_type=StationType.TAILORING.value, position=(15.0, 0.0, 20.0), efficiency=1.0),
        ]
        for stn in stations:
            self._stations[stn.station_id] = stn

        self._stats.total_recipes = len(self._recipes)
        self._stats.unlocked_recipes = sum(1 for r in self._recipes.values() if r.unlocked)
        self._stats.total_stations = len(self._stations)
        self._initialized = True

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"cevt_{self._event_counter:08d}"

    def _next_craft_id(self) -> str:
        self._craft_counter += 1
        return f"craft_{self._craft_counter:08d}"

    def _record_event(self, kind: str, **kwargs: Any) -> CraftEvent:
        event = CraftEvent(
            event_id=self._next_event_id(),
            kind=kind,
            timestamp=_now(),
            **kwargs,
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return event

    # ------------------------------------------------------------------
    # Recipe Management
    # ------------------------------------------------------------------

    def register_recipe(self, recipe: CraftRecipe) -> Dict[str, Any]:
        if len(self._recipes) >= _MAX_RECIPES and recipe.recipe_id not in self._recipes:
            oldest_id = next(iter(self._recipes))
            self._recipes.pop(oldest_id, None)
        was_new = recipe.recipe_id not in self._recipes
        self._recipes[recipe.recipe_id] = recipe
        self._stats.total_recipes = len(self._recipes)
        self._stats.unlocked_recipes = sum(1 for r in self._recipes.values() if r.unlocked)
        self._record_event(
            CraftEventKind.RECIPE_REGISTERED if was_new else CraftEventKind.CONFIG_UPDATED,
            recipe_id=recipe.recipe_id,
            details={"name": recipe.name, "category": recipe.category},
        )
        return {"recipe_id": recipe.recipe_id, "registered": True}

    def remove_recipe(self, recipe_id: str) -> Dict[str, Any]:
        if recipe_id not in self._recipes:
            return {"recipe_id": recipe_id, "removed": False, "reason": "not found"}
        self._recipes.pop(recipe_id)
        self._stats.total_recipes = len(self._recipes)
        self._stats.unlocked_recipes = sum(1 for r in self._recipes.values() if r.unlocked)
        self._record_event(CraftEventKind.RECIPE_REMOVED, recipe_id=recipe_id)
        return {"recipe_id": recipe_id, "removed": True}

    def get_recipe(self, recipe_id: str) -> Optional[CraftRecipe]:
        return self._recipes.get(recipe_id)

    def list_recipes(self, category: Optional[str] = None, unlocked: Optional[bool] = None, station: Optional[str] = None, limit: int = 100) -> List[CraftRecipe]:
        results: List[CraftRecipe] = []
        for r in self._recipes.values():
            if category is not None and r.category != category:
                continue
            if unlocked is not None and r.unlocked != unlocked:
                continue
            if station is not None and r.required_station != station:
                continue
            results.append(r)
        return results[:max(0, min(limit, len(results)))]

    def unlock_recipe(self, recipe_id: str) -> Dict[str, Any]:
        r = self._recipes.get(recipe_id)
        if r is None:
            return {"recipe_id": recipe_id, "unlocked": False, "reason": "not found"}
        was_locked = not r.unlocked
        r.unlocked = True
        self._stats.unlocked_recipes = sum(1 for x in self._recipes.values() if x.unlocked)
        if was_locked:
            self._record_event(CraftEventKind.RECIPE_UNLOCKED, recipe_id=recipe_id)
        return {"recipe_id": recipe_id, "unlocked": True}

    def discover_recipe(self, recipe_id: str, crafter_id: str = "") -> Dict[str, Any]:
        r = self._recipes.get(recipe_id)
        if r is None:
            return {"recipe_id": recipe_id, "discovered": False, "reason": "not found"}
        if not r.discoverable:
            return {"recipe_id": recipe_id, "discovered": False, "reason": "not discoverable"}
        if r.unlocked:
            return {"recipe_id": recipe_id, "discovered": False, "reason": "already known"}
        r.unlocked = True
        self._stats.unlocked_recipes = sum(1 for x in self._recipes.values() if x.unlocked)
        self._stats.total_discoveries += 1
        self._record_event(CraftEventKind.RECIPE_DISCOVERED, recipe_id=recipe_id, crafter_id=crafter_id)
        return {"recipe_id": recipe_id, "discovered": True, "name": r.name}

    # ------------------------------------------------------------------
    # Station Management
    # ------------------------------------------------------------------

    def register_station(self, station: CraftStation) -> Dict[str, Any]:
        if len(self._stations) >= _MAX_STATIONS and station.station_id not in self._stations:
            oldest_id = next(iter(self._stations))
            self._stations.pop(oldest_id, None)
        was_new = station.station_id not in self._stations
        self._stations[station.station_id] = station
        self._stats.total_stations = len(self._stations)
        self._record_event(
            CraftEventKind.STATION_REGISTERED if was_new else CraftEventKind.CONFIG_UPDATED,
            station_id=station.station_id,
            details={"name": station.name, "type": station.station_type},
        )
        return {"station_id": station.station_id, "registered": True}

    def remove_station(self, station_id: str) -> Dict[str, Any]:
        if station_id not in self._stations:
            return {"station_id": station_id, "removed": False, "reason": "not found"}
        self._stations.pop(station_id)
        self._stats.total_stations = len(self._stations)
        self._record_event(CraftEventKind.STATION_REMOVED, station_id=station_id)
        return {"station_id": station_id, "removed": True}

    def get_station(self, station_id: str) -> Optional[CraftStation]:
        return self._stations.get(station_id)

    def list_stations(self, station_type: Optional[str] = None, enabled: Optional[bool] = None, limit: int = 100) -> List[CraftStation]:
        results: List[CraftStation] = []
        for s in self._stations.values():
            if station_type is not None and s.station_type != station_type:
                continue
            if enabled is not None and s.enabled != enabled:
                continue
            results.append(s)
        return results[:max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Crafting Operations
    # ------------------------------------------------------------------

    def start_craft(self, recipe_id: str, crafter_id: str = "", station_id: str = "", skill_level: int = 0, available_materials: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Start a crafting operation. Returns the craft_id or error."""
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return {"started": False, "reason": "recipe not found"}
        if not recipe.unlocked:
            return {"started": False, "reason": "recipe locked"}

        # Check station
        station: Optional[CraftStation] = None
        if station_id:
            station = self._stations.get(station_id)
            if station is None:
                return {"started": False, "reason": "station not found"}
            if not station.enabled:
                return {"started": False, "reason": "station disabled"}
            if station.station_type != recipe.required_station:
                return {"started": False, "reason": "wrong station type"}
        else:
            # Find any matching station
            for s in self._stations.values():
                if s.enabled and s.station_type == recipe.required_station:
                    station = s
                    station_id = s.station_id
                    break
            if station is None and recipe.required_station != StationType.WORKBENCH.value:
                return {"started": False, "reason": "no suitable station"}

        # Check skill
        effective_skill = skill_level + (station.skill_bonus if station else 0)
        if self._config.skill_check_enabled and recipe.required_skill_level > 0 and effective_skill < recipe.required_skill_level:
            return {"started": False, "reason": "skill level too low", "required": recipe.required_skill_level, "actual": effective_skill}

        # Check materials
        if available_materials is not None:
            for mat in recipe.inputs:
                found = 0
                for avail in available_materials:
                    if avail.get("item_id") == mat.item_id:
                        found += _safe_int(avail.get("quantity"), 0)
                if found < mat.quantity:
                    return {"started": False, "reason": "insufficient materials", "missing": mat.item_id, "needed": mat.quantity, "available": found}

        # Check concurrent craft limit
        active_count = sum(1 for c in self._crafts.values() if c.status == CraftStatus.IN_PROGRESS.value)
        if active_count >= self._config.max_concurrent_crafts:
            return {"started": False, "reason": "too many concurrent crafts"}

        # Compute effective stats
        efficiency = station.efficiency if station else 1.0
        success_rate = recipe.success_rate
        if station:
            success_rate += station.bonus_success_rate
        success_rate = _clamp(success_rate, 0.0, 1.0)

        total_time = recipe.craft_time / max(efficiency, 0.1)
        craft = CraftOperation(
            craft_id=self._next_craft_id(),
            recipe_id=recipe_id,
            crafter_id=crafter_id,
            station_id=station_id,
            status=CraftStatus.IN_PROGRESS.value,
            progress=0.0,
            elapsed=0.0,
            total_time=total_time,
            inputs_consumed=[m.to_dict() for m in recipe.inputs],
            started_at=_now(),
        )
        self._crafts[craft.craft_id] = craft
        self._stats.total_crafts_started += 1
        self._record_event(
            CraftEventKind.CRAFT_STARTED,
            recipe_id=recipe_id,
            station_id=station_id,
            craft_id=craft.craft_id,
            crafter_id=crafter_id,
            details={"total_time": total_time, "success_rate": success_rate},
        )

        # If craft time is 0, complete immediately
        if total_time <= 0:
            return self._complete_craft(craft.craft_id, success_rate, station)

        return {"started": True, "craft_id": craft.craft_id, "total_time": total_time, "success_rate": success_rate}

    def _complete_craft(self, craft_id: str, success_rate: float, station: Optional[CraftStation]) -> Dict[str, Any]:
        """Complete a craft operation with success/failure roll."""
        craft = self._crafts.get(craft_id)
        if craft is None:
            return {"completed": False, "reason": "craft not found"}
        recipe = self._recipes.get(craft.recipe_id)
        if recipe is None:
            return {"completed": False, "reason": "recipe not found"}

        # Roll success
        import random as _random
        success = _random.random() < success_rate
        craft.completed_at = _now()

        if success:
            craft.status = CraftStatus.COMPLETED.value
            craft.progress = 1.0
            # Generate outputs with quality roll
            quality_bonus = station.bonus_quality if station else 0.0
            for output in recipe.outputs:
                if _random.random() < output.chance:
                    quality = _random.uniform(output.quality_min, output.quality_max) + quality_bonus
                    quality = _clamp(quality, 0.0, 1.0)
                    qty = output.quantity * recipe.batch_size
                    craft.outputs_produced.append({
                        "item_id": output.item_id,
                        "quantity": qty,
                        "quality": quality,
                    })
            self._stats.total_crafts_completed += 1
            self._record_event(
                CraftEventKind.CRAFT_COMPLETED,
                recipe_id=recipe.recipe_id,
                craft_id=craft_id,
                crafter_id=craft.crafter_id,
                details={"outputs": craft.outputs_produced},
            )
        else:
            craft.status = CraftStatus.FAILED.value
            craft.error_message = "Crafting failed - materials lost."
            self._stats.total_crafts_failed += 1
            self._record_event(
                CraftEventKind.CRAFT_FAILED,
                recipe_id=recipe.recipe_id,
                craft_id=craft_id,
                crafter_id=craft.crafter_id,
                details={"reason": "skill_check_failed"},
            )

        return {"craft_id": craft_id, "status": craft.status, "outputs": craft.outputs_produced}

    def cancel_craft(self, craft_id: str) -> Dict[str, Any]:
        craft = self._crafts.get(craft_id)
        if craft is None:
            return {"craft_id": craft_id, "cancelled": False, "reason": "not found"}
        if craft.status != CraftStatus.IN_PROGRESS.value:
            return {"craft_id": craft_id, "cancelled": False, "reason": "not in progress"}
        craft.status = CraftStatus.CANCELLED.value
        craft.completed_at = _now()
        self._stats.total_crafts_cancelled += 1
        self._record_event(CraftEventKind.CRAFT_CANCELLED, craft_id=craft_id, crafter_id=craft.crafter_id)
        return {"craft_id": craft_id, "cancelled": True}

    def get_craft(self, craft_id: str) -> Optional[CraftOperation]:
        return self._crafts.get(craft_id)

    def list_crafts(self, status: Optional[str] = None, crafter_id: Optional[str] = None, limit: int = 100) -> List[CraftOperation]:
        results: List[CraftOperation] = []
        for c in self._crafts.values():
            if status is not None and c.status != status:
                continue
            if crafter_id is not None and c.crafter_id != crafter_id:
                continue
            results.append(c)
        return list(reversed(results))[:max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Tick / lifecycle
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.1) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        completed_ids: List[str] = []
        for craft_id, craft in list(self._crafts.items()):
            if craft.status != CraftStatus.IN_PROGRESS.value:
                continue
            craft.elapsed += delta_time
            craft.progress = _clamp(craft.elapsed / max(craft.total_time, 1e-6), 0.0, 1.0)
            if craft.progress >= 1.0:
                # Find recipe and station for completion
                recipe = self._recipes.get(craft.recipe_id)
                station = self._stations.get(craft.station_id) if craft.station_id else None
                if recipe is not None:
                    success_rate = recipe.success_rate
                    if station:
                        success_rate += station.bonus_success_rate
                    success_rate = _clamp(success_rate, 0.0, 1.0)
                    self._complete_craft(craft_id, success_rate, station)
                    completed_ids.append(craft_id)
                else:
                    craft.status = CraftStatus.FAILED.value
                    craft.error_message = "recipe removed during craft"
                self._record_event(
                    CraftEventKind.CRAFT_PROGRESS,
                    craft_id=craft_id,
                    recipe_id=craft.recipe_id,
                    details={"progress": craft.progress, "completed": craft_id in completed_ids},
                )
        self._record_event(CraftEventKind.TICK, details={"delta_time": delta_time, "tick": self._tick_count, "completed": len(completed_ids)})
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return {"tick": self._tick_count, "delta_time": delta_time, "completed": len(completed_ids)}

    def get_config(self) -> CraftConfig:
        return self._config

    def set_config(self, config: CraftConfig) -> Dict[str, Any]:
        self._config = config
        self._record_event(CraftEventKind.CONFIG_UPDATED, details={"max_recipes": config.max_recipes})
        return {"updated": True}

    def list_events(self, recipe_id: Optional[str] = None, station_id: Optional[str] = None, craft_id: Optional[str] = None, limit: int = 100) -> List[CraftEvent]:
        results: List[CraftEvent] = []
        for e in self._events:
            if recipe_id is not None and e.recipe_id != recipe_id:
                continue
            if station_id is not None and e.station_id != station_id:
                continue
            if craft_id is not None and e.craft_id != craft_id:
                continue
            results.append(e)
        return list(reversed(results))[:max(0, min(limit, len(results)))]

    def get_stats(self) -> CraftStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_recipes": len(self._recipes),
            "unlocked_recipes": sum(1 for r in self._recipes.values() if r.unlocked),
            "total_stations": len(self._stations),
            "active_crafts": sum(1 for c in self._crafts.values() if c.status == CraftStatus.IN_PROGRESS.value),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> CraftSnapshot:
        return CraftSnapshot(
            recipes=[r.to_dict() for r in self._recipes.values()],
            stations=[s.to_dict() for s in self._stations.values()],
            active_crafts=[c.to_dict() for c in self._crafts.values() if c.status == CraftStatus.IN_PROGRESS.value],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        self._recipes.clear()
        self._stations.clear()
        self._crafts.clear()
        self._events.clear()
        self._stats = CraftStats()
        self._tick_count = 0
        self._event_counter = 0
        self._craft_counter = 0
        self._initialized = False
        self._seed()
        self._record_event(CraftEventKind.RESET)
        return {"reset": True, "initialized": self._initialized}


def get_crafting_system() -> CraftingSystem:
    return CraftingSystem.get_instance()
