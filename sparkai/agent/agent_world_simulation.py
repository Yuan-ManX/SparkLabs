"""
SparkLabs Agent - Autonomous World Simulation Engine

Comprehensive autonomous world simulation system for the SparkLabs
AI-Native Game Engine. Provides stepped time progression, population
dynamics, resource economy, emergent event generation, world state
snapshots, and causal chain tracking for narrative generation.

Architecture:
  AgentWorldSimulation (Singleton)
    |-- SimulationClock (stepped time progression with multiple time scales)
    |-- PopulationManager (NPC lifecycle: spawn, age, migrate, die)
    |-- ResourceSystem (resource nodes, production, consumption, depletion)
    |-- EventGenerator (emergent world events from state conditions)
    |-- WorldStateSnapshot (serializable world state for save/load)
    |-- CausalChain (track cause-effect relationships between events)

Key Features:
  - Configurable simulation speed (PAUSED, REAL_TIME, X2, X5, X10, X100)
  - Day/night cycle, season tracking, year progression
  - NPC spawning with traits, aging, reproduction, migration, death
  - Resource nodes with production, consumption, depletion, trade
  - Emergent events: weather, disasters, discoveries, conflicts
  - Full world state serialization with snapshot rollback
  - Causal graph tracking for narrative generation

Usage:
    sim = get_agent_world_simulation()
    sim.create_region("Verdant Plains", RegionType.PLAINS)
    sim.create_entity("Elder Oak", "tree_ent", "region_1")
    sim.add_resource_node("region_1", ResourceType.FOOD, 500.0)
    sim.advance_time(ticks=100)
    snapshot = sim.take_snapshot()
    events = sim.get_events(since_tick=0)
    stats = sim.get_stats()
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


# =============================================================================
# Enums
# =============================================================================


class SimulationSpeed(Enum):
    PAUSED = "paused"
    REAL_TIME = "real_time"
    X2 = "x2"
    X5 = "x5"
    X10 = "x10"
    X100 = "x100"


class DayPhase(Enum):
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class Season(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class ResourceType(Enum):
    FOOD = "food"
    WOOD = "wood"
    STONE = "stone"
    METAL = "metal"
    MANA = "mana"
    GOLD = "gold"
    POPULATION = "population"


class EventCategory(Enum):
    NATURAL = "natural"
    SOCIAL = "social"
    ECONOMIC = "economic"
    MAGICAL = "magical"
    MILITARY = "military"
    DISCOVERY = "discovery"


class EntityState(Enum):
    ALIVE = "alive"
    AGING = "aging"
    MIGRATING = "migrating"
    DECEASED = "deceased"
    FROZEN = "frozen"


class RegionType(Enum):
    PLAINS = "plains"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    DESERT = "desert"
    COASTAL = "coastal"
    URBAN = "urban"
    UNDERGROUND = "underground"


# =============================================================================
# Simulation Constants
# =============================================================================

_SPEED_MULTIPLIERS: Dict[str, int] = {
    SimulationSpeed.PAUSED.value: 0,
    SimulationSpeed.REAL_TIME.value: 1,
    SimulationSpeed.X2.value: 2,
    SimulationSpeed.X5.value: 5,
    SimulationSpeed.X10.value: 10,
    SimulationSpeed.X100.value: 100,
}

_TICKS_PER_DAY = 24
_TICKS_PER_SEASON = 90
_TICKS_PER_YEAR = 360
_DAYS_PER_SEASON = _TICKS_PER_SEASON // _TICKS_PER_DAY

_DAY_PHASE_MAP: Dict[int, str] = {
    0: DayPhase.MIDNIGHT.value,
    1: DayPhase.MIDNIGHT.value,
    2: DayPhase.NIGHT.value,
    3: DayPhase.NIGHT.value,
    4: DayPhase.DAWN.value,
    5: DayPhase.DAWN.value,
    6: DayPhase.MORNING.value,
    7: DayPhase.MORNING.value,
    8: DayPhase.MORNING.value,
    9: DayPhase.MORNING.value,
    10: DayPhase.NOON.value,
    11: DayPhase.NOON.value,
    12: DayPhase.NOON.value,
    13: DayPhase.NOON.value,
    14: DayPhase.AFTERNOON.value,
    15: DayPhase.AFTERNOON.value,
    16: DayPhase.AFTERNOON.value,
    17: DayPhase.AFTERNOON.value,
    18: DayPhase.DUSK.value,
    19: DayPhase.DUSK.value,
    20: DayPhase.NIGHT.value,
    21: DayPhase.NIGHT.value,
    22: DayPhase.NIGHT.value,
    23: DayPhase.MIDNIGHT.value,
}

_REGION_RESOURCE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    RegionType.PLAINS.value: {
        ResourceType.FOOD.value: 1.5,
        ResourceType.WOOD.value: 0.8,
        ResourceType.STONE.value: 0.8,
        ResourceType.METAL.value: 0.5,
        ResourceType.MANA.value: 0.8,
        ResourceType.GOLD.value: 0.7,
    },
    RegionType.FOREST.value: {
        ResourceType.FOOD.value: 1.2,
        ResourceType.WOOD.value: 2.0,
        ResourceType.STONE.value: 0.6,
        ResourceType.METAL.value: 0.4,
        ResourceType.MANA.value: 1.5,
        ResourceType.GOLD.value: 0.5,
    },
    RegionType.MOUNTAIN.value: {
        ResourceType.FOOD.value: 0.5,
        ResourceType.WOOD.value: 0.5,
        ResourceType.STONE.value: 2.0,
        ResourceType.METAL.value: 2.0,
        ResourceType.MANA.value: 1.2,
        ResourceType.GOLD.value: 1.5,
    },
    RegionType.DESERT.value: {
        ResourceType.FOOD.value: 0.3,
        ResourceType.WOOD.value: 0.2,
        ResourceType.STONE.value: 1.2,
        ResourceType.METAL.value: 1.0,
        ResourceType.MANA.value: 1.8,
        ResourceType.GOLD.value: 1.2,
    },
    RegionType.COASTAL.value: {
        ResourceType.FOOD.value: 1.8,
        ResourceType.WOOD.value: 0.7,
        ResourceType.STONE.value: 0.7,
        ResourceType.METAL.value: 0.6,
        ResourceType.MANA.value: 1.0,
        ResourceType.GOLD.value: 1.0,
    },
    RegionType.URBAN.value: {
        ResourceType.FOOD.value: 0.6,
        ResourceType.WOOD.value: 0.4,
        ResourceType.STONE.value: 0.5,
        ResourceType.METAL.value: 1.5,
        ResourceType.MANA.value: 0.5,
        ResourceType.GOLD.value: 2.0,
    },
    RegionType.UNDERGROUND.value: {
        ResourceType.FOOD.value: 0.4,
        ResourceType.WOOD.value: 0.1,
        ResourceType.STONE.value: 1.5,
        ResourceType.METAL.value: 2.0,
        ResourceType.MANA.value: 2.0,
        ResourceType.GOLD.value: 1.8,
    },
}

_REGION_POPULATION_CAPS: Dict[str, int] = {
    RegionType.PLAINS.value: 500,
    RegionType.FOREST.value: 300,
    RegionType.MOUNTAIN.value: 150,
    RegionType.DESERT.value: 80,
    RegionType.COASTAL.value: 400,
    RegionType.URBAN.value: 1000,
    RegionType.UNDERGROUND.value: 200,
}

_SEASON_EFFECTS: Dict[str, Dict[str, float]] = {
    Season.SPRING.value: {
        "food_regen_bonus": 1.3,
        "birth_rate_bonus": 1.5,
        "wood_regen_bonus": 1.2,
        "disaster_chance": 0.05,
        "migration_chance": 0.03,
    },
    Season.SUMMER.value: {
        "food_regen_bonus": 1.0,
        "birth_rate_bonus": 1.0,
        "wood_regen_bonus": 1.0,
        "disaster_chance": 0.08,
        "migration_chance": 0.05,
    },
    Season.AUTUMN.value: {
        "food_regen_bonus": 1.5,
        "birth_rate_bonus": 0.5,
        "wood_regen_bonus": 0.8,
        "disaster_chance": 0.06,
        "migration_chance": 0.04,
    },
    Season.WINTER.value: {
        "food_regen_bonus": 0.3,
        "birth_rate_bonus": 0.1,
        "wood_regen_bonus": 0.5,
        "disaster_chance": 0.10,
        "migration_chance": 0.02,
    },
}

_ENTITY_TYPE_TRAITS: Dict[str, List[str]] = {
    "human": ["adaptable", "social", "crafty", "ambitious"],
    "elf": ["graceful", "long_lived", "magical", "perceptive"],
    "dwarf": ["sturdy", "industrious", "stubborn", "loyal"],
    "orc": ["strong", "aggressive", "tribal", "resilient"],
    "goblin": ["cunning", "nimble", "greedy", "numerous"],
    "beast": ["feral", "territorial", "instinctive", "wild"],
    "dragon": ["ancient", "powerful", "hoarding", "solitary"],
    "spirit": ["ethereal", "ancient", "mysterious", "bound"],
    "tree_ent": ["ancient", "guardian", "rooted", "wise"],
    "merchant": ["shrewd", "mobile", "neutral", "resourceful"],
    "monster": ["hostile", "territorial", "mutating", "hungry"],
    "villager": ["simple", "hardworking", "social", "traditional"],
}

_EVENT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "event_type": "drought",
        "category": EventCategory.NATURAL.value,
        "base_severity": 0.6,
        "description_template": "A severe drought strikes {region}, depleting food and water supplies.",
        "affected_resources": [ResourceType.FOOD.value],
        "resource_impact": -0.4,
        "trigger_conditions": {"min_population": 20, "season": Season.SUMMER.value},
    },
    {
        "event_type": "storm",
        "category": EventCategory.NATURAL.value,
        "base_severity": 0.5,
        "description_template": "A violent storm ravages {region}, damaging infrastructure.",
        "affected_resources": [ResourceType.WOOD.value, ResourceType.STONE.value],
        "resource_impact": -0.25,
        "trigger_conditions": {"min_population": 10, "season": Season.AUTUMN.value},
    },
    {
        "event_type": "blizzard",
        "category": EventCategory.NATURAL.value,
        "base_severity": 0.7,
        "description_template": "A devastating blizzard freezes {region}, halting all outdoor activity.",
        "affected_resources": [ResourceType.FOOD.value, ResourceType.WOOD.value],
        "resource_impact": -0.35,
        "trigger_conditions": {"min_population": 5, "season": Season.WINTER.value},
    },
    {
        "event_type": "earthquake",
        "category": EventCategory.NATURAL.value,
        "base_severity": 0.8,
        "description_template": "The earth trembles beneath {region}, collapsing structures and mines.",
        "affected_resources": [ResourceType.STONE.value, ResourceType.METAL.value],
        "resource_impact": -0.3,
        "trigger_conditions": {"min_population": 10},
    },
    {
        "event_type": "resource_boom",
        "category": EventCategory.ECONOMIC.value,
        "base_severity": 0.3,
        "description_template": "A rich vein of resources is discovered in {region}, boosting the local economy.",
        "affected_resources": [ResourceType.GOLD.value, ResourceType.METAL.value],
        "resource_impact": 0.5,
        "trigger_conditions": {"min_population": 30},
    },
    {
        "event_type": "famine",
        "category": EventCategory.ECONOMIC.value,
        "base_severity": 0.7,
        "description_template": "Food stores run critically low in {region}, sparking unrest.",
        "affected_resources": [ResourceType.FOOD.value],
        "resource_impact": -0.5,
        "trigger_conditions": {"min_population": 50, "food_below_ratio": 0.2},
    },
    {
        "event_type": "trade_caravan",
        "category": EventCategory.ECONOMIC.value,
        "base_severity": 0.2,
        "description_template": "A trade caravan arrives in {region}, bringing exotic goods and wealth.",
        "affected_resources": [ResourceType.GOLD.value],
        "resource_impact": 0.3,
        "trigger_conditions": {"min_population": 40},
    },
    {
        "event_type": "population_boom",
        "category": EventCategory.SOCIAL.value,
        "base_severity": 0.3,
        "description_template": "A baby boom sweeps through {region}, rapidly increasing the population.",
        "affected_resources": [ResourceType.POPULATION.value],
        "resource_impact": 0.2,
        "trigger_conditions": {"min_population": 50, "season": Season.SPRING.value},
    },
    {
        "event_type": "migration_wave",
        "category": EventCategory.SOCIAL.value,
        "base_severity": 0.4,
        "description_template": "A wave of migrants arrives in {region}, seeking new opportunities.",
        "affected_resources": [ResourceType.POPULATION.value],
        "resource_impact": 0.15,
        "trigger_conditions": {"min_population": 30},
    },
    {
        "event_type": "plague",
        "category": EventCategory.SOCIAL.value,
        "base_severity": 0.9,
        "description_template": "A terrible plague spreads through {region}, decimating the population.",
        "affected_resources": [ResourceType.POPULATION.value],
        "resource_impact": -0.3,
        "trigger_conditions": {"min_population": 100},
    },
    {
        "event_type": "festival",
        "category": EventCategory.SOCIAL.value,
        "base_severity": 0.1,
        "description_template": "A grand festival is held in {region}, boosting morale and trade.",
        "affected_resources": [ResourceType.GOLD.value, ResourceType.FOOD.value],
        "resource_impact": 0.1,
        "trigger_conditions": {"min_population": 80},
    },
    {
        "event_type": "mana_surge",
        "category": EventCategory.MAGICAL.value,
        "base_severity": 0.5,
        "description_template": "A surge of magical energy flows through {region}, empowering all mana sources.",
        "affected_resources": [ResourceType.MANA.value],
        "resource_impact": 0.6,
        "trigger_conditions": {"min_population": 10},
    },
    {
        "event_type": "arcane_anomaly",
        "category": EventCategory.MAGICAL.value,
        "base_severity": 0.6,
        "description_template": "An arcane anomaly disrupts the magical balance in {region}.",
        "affected_resources": [ResourceType.MANA.value],
        "resource_impact": -0.3,
        "trigger_conditions": {"min_population": 15},
    },
    {
        "event_type": "monster_invasion",
        "category": EventCategory.MILITARY.value,
        "base_severity": 0.8,
        "description_template": "A horde of monsters invades {region}, threatening all inhabitants.",
        "affected_resources": [ResourceType.POPULATION.value, ResourceType.FOOD.value],
        "resource_impact": -0.2,
        "trigger_conditions": {"min_population": 50},
    },
    {
        "event_type": "faction_conflict",
        "category": EventCategory.MILITARY.value,
        "base_severity": 0.7,
        "description_template": "Rival factions clash in {region}, disrupting the peace.",
        "affected_resources": [ResourceType.POPULATION.value, ResourceType.GOLD.value],
        "resource_impact": -0.15,
        "trigger_conditions": {"min_population": 100},
    },
    {
        "event_type": "discovery_ruins",
        "category": EventCategory.DISCOVERY.value,
        "base_severity": 0.3,
        "description_template": "Ancient ruins are discovered in {region}, revealing lost knowledge and treasures.",
        "affected_resources": [ResourceType.GOLD.value, ResourceType.MANA.value],
        "resource_impact": 0.4,
        "trigger_conditions": {"min_population": 20},
    },
    {
        "event_type": "technological_breakthrough",
        "category": EventCategory.DISCOVERY.value,
        "base_severity": 0.4,
        "description_template": "A technological breakthrough in {region} revolutionizes resource production.",
        "affected_resources": [ResourceType.METAL.value, ResourceType.WOOD.value],
        "resource_impact": 0.3,
        "trigger_conditions": {"min_population": 100},
    },
    {
        "event_type": "herbal_bloom",
        "category": EventCategory.DISCOVERY.value,
        "base_severity": 0.2,
        "description_template": "Rare medicinal herbs bloom across {region}, improving health and vitality.",
        "affected_resources": [ResourceType.FOOD.value],
        "resource_impact": 0.25,
        "trigger_conditions": {"min_population": 10, "season": Season.SPRING.value},
    },
]

_CAUSAL_CHAIN_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "drought": [
        {"effect_event": "famine", "probability": 0.6, "delay_ticks": 10},
        {"effect_event": "migration_wave", "probability": 0.3, "delay_ticks": 15},
    ],
    "famine": [
        {"effect_event": "plague", "probability": 0.3, "delay_ticks": 8},
        {"effect_event": "faction_conflict", "probability": 0.4, "delay_ticks": 5},
        {"effect_event": "migration_wave", "probability": 0.5, "delay_ticks": 10},
    ],
    "storm": [
        {"effect_event": "famine", "probability": 0.2, "delay_ticks": 12},
    ],
    "blizzard": [
        {"effect_event": "famine", "probability": 0.5, "delay_ticks": 5},
        {"effect_event": "migration_wave", "probability": 0.2, "delay_ticks": 20},
    ],
    "earthquake": [
        {"effect_event": "faction_conflict", "probability": 0.2, "delay_ticks": 10},
    ],
    "resource_boom": [
        {"effect_event": "migration_wave", "probability": 0.5, "delay_ticks": 8},
        {"effect_event": "population_boom", "probability": 0.3, "delay_ticks": 15},
    ],
    "monster_invasion": [
        {"effect_event": "migration_wave", "probability": 0.6, "delay_ticks": 5},
        {"effect_event": "famine", "probability": 0.3, "delay_ticks": 8},
    ],
    "faction_conflict": [
        {"effect_event": "migration_wave", "probability": 0.5, "delay_ticks": 8},
        {"effect_event": "famine", "probability": 0.2, "delay_ticks": 10},
    ],
    "plague": [
        {"effect_event": "migration_wave", "probability": 0.4, "delay_ticks": 15},
        {"effect_event": "famine", "probability": 0.3, "delay_ticks": 5},
    ],
    "mana_surge": [
        {"effect_event": "arcane_anomaly", "probability": 0.2, "delay_ticks": 12},
    ],
    "population_boom": [
        {"effect_event": "famine", "probability": 0.2, "delay_ticks": 20},
        {"effect_event": "resource_boom", "probability": 0.1, "delay_ticks": 25},
    ],
}

_DEFAULT_ENTITY_MAX_AGE: Dict[str, int] = {
    "human": 80,
    "elf": 800,
    "dwarf": 250,
    "orc": 50,
    "goblin": 30,
    "beast": 40,
    "dragon": 2000,
    "spirit": 5000,
    "tree_ent": 3000,
    "merchant": 70,
    "monster": 100,
    "villager": 75,
}

_DEFAULT_BASE_CONSUMPTION: Dict[str, float] = {
    ResourceType.FOOD.value: 1.0,
    ResourceType.WOOD.value: 0.3,
    ResourceType.STONE.value: 0.1,
    ResourceType.METAL.value: 0.05,
    ResourceType.MANA.value: 0.02,
    ResourceType.GOLD.value: 0.5,
}

_DEFAULT_BASE_REGEN: Dict[str, float] = {
    ResourceType.FOOD.value: 2.0,
    ResourceType.WOOD.value: 1.5,
    ResourceType.STONE.value: 0.2,
    ResourceType.METAL.value: 0.1,
    ResourceType.MANA.value: 1.0,
    ResourceType.GOLD.value: 0.5,
}


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class SimEntity:
    """A simulated entity (NPC, creature, or other living being) in the world.

    Attributes:
        id: Unique entity identifier (auto-generated).
        name: Display name of the entity.
        entity_type: Category of entity (human, elf, dwarf, beast, etc.).
        region_id: The region this entity currently resides in.
        age: Current age in simulation ticks.
        max_age: Maximum natural lifespan in ticks.
        traits: List of behavioral traits.
        state: Current lifecycle state.
        position: (x, y) coordinates within the region.
        resources: Resources carried or owned by this entity.
        created_at: Tick when the entity was spawned.
        relationships: Map of entity_id to relationship value (-1.0 to 1.0).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    entity_type: str = "human"
    region_id: str = ""
    age: int = 0
    max_age: int = 80
    traits: List[str] = field(default_factory=list)
    state: EntityState = EntityState.ALIVE
    position: Tuple[float, float] = (0.0, 0.0)
    resources: Dict[str, float] = field(default_factory=dict)
    created_at: int = 0
    relationships: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "region_id": self.region_id,
            "age": self.age,
            "max_age": self.max_age,
            "traits": list(self.traits),
            "state": self.state.value,
            "position": list(self.position),
            "resources": dict(self.resources),
            "created_at": self.created_at,
            "relationships": dict(self.relationships),
        }


@dataclass
class ResourceNode:
    """A resource node in a region that produces or stores resources.

    Attributes:
        id: Unique resource node identifier (auto-generated).
        resource_type: Type of resource this node provides.
        region_id: The region this node is located in.
        amount: Current amount of resource available.
        max_amount: Maximum capacity of this resource node.
        regen_rate: Amount regenerated per tick.
        position: (x, y) coordinates within the region.
        quality: Quality multiplier (0.0-1.0) affecting regen rate.
        depletion_threshold: Below this ratio, regen rate is halved.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    resource_type: ResourceType = ResourceType.FOOD
    region_id: str = ""
    amount: float = 0.0
    max_amount: float = 100.0
    regen_rate: float = 1.0
    position: Tuple[float, float] = (0.0, 0.0)
    quality: float = 0.5
    depletion_threshold: float = 0.2

    @property
    def is_depleted(self) -> bool:
        return self.amount <= 0.0

    @property
    def depletion_ratio(self) -> float:
        if self.max_amount <= 0:
            return 0.0
        return self.amount / self.max_amount

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "region_id": self.region_id,
            "amount": round(self.amount, 2),
            "max_amount": round(self.max_amount, 2),
            "regen_rate": round(self.regen_rate, 4),
            "position": list(self.position),
            "quality": round(self.quality, 2),
            "depletion_threshold": round(self.depletion_threshold, 2),
            "is_depleted": self.is_depleted,
            "depletion_ratio": round(self.depletion_ratio, 2),
        }


@dataclass
class SimulationEvent:
    """A world event that occurred during simulation.

    Attributes:
        id: Unique event identifier (auto-generated).
        event_type: Type of event (drought, storm, migration, etc.).
        category: Category of event (natural, social, economic, etc.).
        region_id: The region where the event occurred.
        description: Human-readable description of the event.
        severity: Severity score (0.0-1.0).
        affected_entities: List of entity IDs affected.
        affected_resources: List of resource types affected.
        timestamp: Tick when the event occurred.
        causal_parent_id: The event that caused this event (if any).
        causal_children: List of child event IDs caused by this event.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = ""
    category: EventCategory = EventCategory.NATURAL
    region_id: str = ""
    description: str = ""
    severity: float = 0.0
    affected_entities: List[str] = field(default_factory=list)
    affected_resources: List[str] = field(default_factory=list)
    timestamp: int = 0
    causal_parent_id: Optional[str] = None
    causal_children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "category": self.category.value,
            "region_id": self.region_id,
            "description": self.description,
            "severity": round(self.severity, 2),
            "affected_entities": list(self.affected_entities),
            "affected_resources": list(self.affected_resources),
            "timestamp": self.timestamp,
            "causal_parent_id": self.causal_parent_id,
            "causal_children": list(self.causal_children),
        }


@dataclass
class WorldStateSnapshot:
    """A complete snapshot of the world state at a point in time.

    Attributes:
        id: Unique snapshot identifier (auto-generated).
        sim_time: Current simulation tick.
        day: Current day of the year (0-360).
        season: Current season.
        year: Current simulation year.
        population_count: Total number of living entities.
        resource_totals: Map of resource type to total amount across all nodes.
        active_events: List of active event IDs.
        entities: Serialized entity data.
        regions: Serialized region data.
        timestamp: Real-world time when the snapshot was taken.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sim_time: int = 0
    day: int = 0
    season: str = Season.SPRING.value
    year: int = 0
    population_count: int = 0
    resource_totals: Dict[str, float] = field(default_factory=dict)
    active_events: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    regions: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sim_time": self.sim_time,
            "day": self.day,
            "season": self.season,
            "year": self.year,
            "population_count": self.population_count,
            "resource_totals": dict(self.resource_totals),
            "active_events": list(self.active_events),
            "entities": list(self.entities),
            "regions": list(self.regions),
            "timestamp": self.timestamp,
        }


@dataclass
class CausalLink:
    """A causal relationship between two simulation events.

    Attributes:
        id: Unique causal link identifier (auto-generated).
        cause_event_id: The event that is the cause.
        effect_event_id: The event that is the effect.
        probability: The estimated probability of this causal relationship.
        description: Description of the causal relationship.
        confidence: Confidence score (0.0-1.0) in this causal link.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cause_event_id: str = ""
    effect_event_id: str = ""
    probability: float = 0.0
    description: str = ""
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cause_event_id": self.cause_event_id,
            "effect_event_id": self.effect_event_id,
            "probability": round(self.probability, 2),
            "description": self.description,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class Region:
    """A geographical region in the simulation world.

    Attributes:
        id: Unique region identifier (auto-generated).
        name: Display name of the region.
        region_type: Type of region (plains, forest, mountain, etc.).
        population_cap: Maximum population this region can support.
        resource_multipliers: Multipliers applied to resource regen rates.
        special_traits: Special properties of this region.
        connected_regions: IDs of regions connected to this one.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    region_type: RegionType = RegionType.PLAINS
    population_cap: int = 500
    resource_multipliers: Dict[str, float] = field(default_factory=dict)
    special_traits: List[str] = field(default_factory=list)
    connected_regions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "region_type": self.region_type.value,
            "population_cap": self.population_cap,
            "resource_multipliers": dict(self.resource_multipliers),
            "special_traits": list(self.special_traits),
            "connected_regions": list(self.connected_regions),
        }


# =============================================================================
# AgentWorldSimulation (Singleton)
# =============================================================================


class AgentWorldSimulation:
    """Autonomous world simulation engine for the SparkLabs AI-Native Game Engine.

    Manages a complete simulated world with regions, entities, resources,
    events, and causal chains. Supports stepped time progression at multiple
    speeds, population dynamics, resource economy, and emergent event generation.

    Usage:
        sim = AgentWorldSimulation.get_instance()
        sim.create_region("Verdant Plains", RegionType.PLAINS)
        sim.advance_time(ticks=100)
        stats = sim.get_stats()
    """

    _instance: Optional["AgentWorldSimulation"] = None
    _lock = threading.RLock()

    MAX_ENTITIES = 10000
    MAX_REGIONS = 100
    MAX_EVENTS = 5000
    MAX_SNAPSHOTS = 100
    MAX_RESOURCE_NODES = 1000

    def __init__(self) -> None:
        # Simulation clock
        self._tick: int = 0
        self._speed: SimulationSpeed = SimulationSpeed.PAUSED
        self._paused: bool = True

        # World state
        self._regions: Dict[str, Region] = {}
        self._entities: Dict[str, SimEntity] = {}
        self._resource_nodes: Dict[str, ResourceNode] = {}
        self._events: List[SimulationEvent] = []
        self._causal_links: List[CausalLink] = []
        self._snapshots: List[WorldStateSnapshot] = []

        # Pending causal events (delay_ticks -> [(event_type, parent_event_id, region_id)])
        self._pending_causal: Dict[int, List[Tuple[str, str, str]]] = {}

        # Statistics tracking
        self._stats: Dict[str, Any] = {
            "total_ticks_advanced": 0,
            "total_entities_spawned": 0,
            "total_entities_died": 0,
            "total_events_generated": 0,
            "total_snapshots_taken": 0,
            "total_births": 0,
            "total_natural_deaths": 0,
            "total_migrations": 0,
            "peak_population": 0,
            "total_resource_consumed": 0.0,
            "total_resource_produced": 0.0,
            "events_by_category": {},
            "events_by_type": {},
            "entity_count_by_type": {},
            "entity_count_by_region": {},
        }

    @classmethod
    def get_instance(cls) -> "AgentWorldSimulation":
        """Get or create the singleton instance with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # =========================================================================
    # Time & Simulation Control
    # =========================================================================

    def advance_time(self, ticks: int = 1) -> Dict[str, Any]:
        """Advance the simulation by the specified number of ticks.

        Each tick processes:
          1. Resource regeneration
          2. Resource consumption by population
          3. Entity aging
          4. Birth and death checks
          5. Migration checks
          6. Event generation (including causal chain events)
          7. Pending causal event resolution

        Args:
            ticks: Number of simulation ticks to advance.

        Returns:
            A summary dict of what happened during this advancement.
        """
        if self._paused:
            return {"ticks_advanced": 0, "reason": "simulation_paused"}

        multiplier = _SPEED_MULTIPLIERS.get(self._speed.value, 1)
        effective_ticks = ticks * multiplier

        summary: Dict[str, Any] = {
            "ticks_advanced": effective_ticks,
            "events_generated": 0,
            "entities_born": 0,
            "entities_died": 0,
            "entities_migrated": 0,
            "resources_consumed": 0.0,
            "resources_produced": 0.0,
        }

        for _ in range(effective_ticks):
            self._tick += 1
            self._stats["total_ticks_advanced"] += 1

            # Step 1: Resource regeneration
            produced = self._regenerate_resources()
            summary["resources_produced"] += produced

            # Step 2: Resource consumption
            consumed = self._consume_resources()
            summary["resources_consumed"] += consumed

            # Step 3: Entity aging
            self._age_entities()

            # Step 4: Birth and death
            births, deaths = self._process_population()
            summary["entities_born"] += births
            summary["entities_died"] += deaths

            # Step 5: Migration
            migrated = self._process_migration()
            summary["entities_migrated"] += migrated

            # Step 6: Event generation
            new_events = self._generate_events()
            summary["events_generated"] += len(new_events)

            # Step 7: Resolve pending causal events
            self._resolve_pending_causal()

            # Update peak population
            alive_count = sum(
                1 for e in self._entities.values() if e.state != EntityState.DECEASED
            )
            if alive_count > self._stats["peak_population"]:
                self._stats["peak_population"] = alive_count

        return summary

    def set_speed(self, speed: SimulationSpeed) -> None:
        """Change the simulation speed.

        Args:
            speed: The new simulation speed. Use PAUSED to pause.
        """
        self._speed = speed
        self._paused = speed == SimulationSpeed.PAUSED

    def pause(self) -> None:
        """Pause the simulation."""
        self._paused = True
        self._speed = SimulationSpeed.PAUSED

    def resume(self) -> None:
        """Resume the simulation at real-time speed."""
        self._paused = False
        self._speed = SimulationSpeed.REAL_TIME

    @property
    def current_tick(self) -> int:
        return self._tick

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def current_speed(self) -> SimulationSpeed:
        return self._speed

    def get_current_day(self) -> int:
        """Get the current day of the simulation year (0-indexed)."""
        return self._tick % _TICKS_PER_YEAR

    def get_current_season(self) -> Season:
        """Get the current season based on the simulation tick."""
        day_of_year = self._tick % _TICKS_PER_YEAR
        if day_of_year < _TICKS_PER_SEASON:
            return Season.SPRING
        elif day_of_year < _TICKS_PER_SEASON * 2:
            return Season.SUMMER
        elif day_of_year < _TICKS_PER_SEASON * 3:
            return Season.AUTUMN
        else:
            return Season.WINTER

    def get_current_year(self) -> int:
        """Get the current simulation year."""
        return self._tick // _TICKS_PER_YEAR

    def get_day_phase(self) -> DayPhase:
        """Get the current day phase based on the simulation tick."""
        hour_of_day = self._tick % _TICKS_PER_DAY
        phase_value = _DAY_PHASE_MAP.get(hour_of_day, DayPhase.NOON.value)
        return DayPhase(phase_value)

    # =========================================================================
    # Region Management
    # =========================================================================

    def create_region(
        self,
        name: str,
        region_type: RegionType,
        population_cap: Optional[int] = None,
        resource_multipliers: Optional[Dict[str, float]] = None,
        special_traits: Optional[List[str]] = None,
        connected_regions: Optional[List[str]] = None,
    ) -> Region:
        """Create a new geographical region in the simulation.

        Args:
            name: Display name of the region.
            region_type: Type of region (plains, forest, mountain, etc.).
                Accepts both RegionType enum and string values.
            population_cap: Max population; defaults to region type default.
            resource_multipliers: Custom resource multipliers.
            special_traits: Special properties of this region.
            connected_regions: IDs of connected regions.

        Returns:
            The created Region object.

        Raises:
            RuntimeError: If maximum region count is exceeded.
        """
        if len(self._regions) >= self.MAX_REGIONS:
            raise RuntimeError(
                f"Maximum region count ({self.MAX_REGIONS}) exceeded"
            )

        # Accept both string and enum for region_type
        if isinstance(region_type, str):
            region_type = RegionType(region_type)
        region_type_value = region_type.value

        cap = (
            population_cap
            if population_cap is not None
            else _REGION_POPULATION_CAPS.get(region_type_value, 500)
        )
        multipliers = (
            dict(resource_multipliers)
            if resource_multipliers
            else dict(_REGION_RESOURCE_MULTIPLIERS.get(region_type_value, {}))
        )

        region = Region(
            name=name,
            region_type=region_type,
            population_cap=cap,
            resource_multipliers=multipliers,
            special_traits=list(special_traits) if special_traits else [],
            connected_regions=list(connected_regions) if connected_regions else [],
        )
        self._regions[region.id] = region
        return region

    def get_region(self, region_id: str) -> Optional[Region]:
        """Get a region by its ID."""
        return self._regions.get(region_id)

    def list_regions(self) -> List[Region]:
        """List all regions in the simulation."""
        return list(self._regions.values())

    def connect_regions(self, region_a_id: str, region_b_id: str) -> bool:
        """Create a bidirectional connection between two regions.

        Args:
            region_a_id: First region ID.
            region_b_id: Second region ID.

        Returns:
            True if both regions exist and were connected, False otherwise.
        """
        region_a = self._regions.get(region_a_id)
        region_b = self._regions.get(region_b_id)
        if not region_a or not region_b:
            return False
        if region_b_id not in region_a.connected_regions:
            region_a.connected_regions.append(region_b_id)
        if region_a_id not in region_b.connected_regions:
            region_b.connected_regions.append(region_a_id)
        return True

    # =========================================================================
    # Entity Management
    # =========================================================================

    def create_entity(
        self,
        name: str,
        entity_type: str,
        region_id: str,
        position: Optional[Tuple[float, float]] = None,
        traits: Optional[List[str]] = None,
        max_age: Optional[int] = None,
        resources: Optional[Dict[str, float]] = None,
    ) -> Optional[SimEntity]:
        """Spawn a new entity in the simulation.

        Args:
            name: Display name of the entity.
            entity_type: Category of entity (human, elf, dwarf, etc.).
            region_id: The region to spawn the entity in.
            position: (x, y) coordinates within the region.
            traits: Behavioral traits. Defaults from entity type template.
            max_age: Max natural lifespan in ticks. Defaults from entity type.
            resources: Initial resources carried by the entity.

        Returns:
            The created SimEntity, or None if limits are exceeded.
        """
        if region_id not in self._regions:
            return None
        if len(self._entities) >= self.MAX_ENTITIES:
            return None

        region = self._regions[region_id]
        alive_in_region = sum(
            1
            for e in self._entities.values()
            if e.region_id == region_id and e.state != EntityState.DECEASED
        )
        if alive_in_region >= region.population_cap:
            return None

        default_traits = _ENTITY_TYPE_TRAITS.get(entity_type, ["generic"])
        default_max_age = _DEFAULT_ENTITY_MAX_AGE.get(entity_type, 80)

        entity = SimEntity(
            name=name,
            entity_type=entity_type,
            region_id=region_id,
            age=0,
            max_age=max_age if max_age is not None else default_max_age,
            traits=list(traits) if traits else list(default_traits),
            state=EntityState.ALIVE,
            position=position if position else (random.uniform(0, 100), random.uniform(0, 100)),
            resources=dict(resources) if resources else {},
            created_at=self._tick,
        )
        self._entities[entity.id] = entity
        self._stats["total_entities_spawned"] += 1
        self._stats["entity_count_by_type"][entity_type] = (
            self._stats["entity_count_by_type"].get(entity_type, 0) + 1
        )
        self._stats["entity_count_by_region"][region_id] = (
            self._stats["entity_count_by_region"].get(region_id, 0) + 1
        )
        return entity

    def get_entity(self, entity_id: str) -> Optional[SimEntity]:
        """Get an entity by its ID."""
        return self._entities.get(entity_id)

    def list_entities(
        self,
        region_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        state: Optional[EntityState] = None,
    ) -> List[SimEntity]:
        """List entities filtered by optional criteria.

        Args:
            region_id: Filter by region.
            entity_type: Filter by entity type.
            state: Filter by entity state.

        Returns:
            List of matching SimEntity objects.
        """
        results: List[SimEntity] = []
        for entity in self._entities.values():
            if region_id is not None and entity.region_id != region_id:
                continue
            if entity_type is not None and entity.entity_type != entity_type:
                continue
            if state is not None and entity.state != state:
                continue
            results.append(entity)
        return results

    def move_entity(self, entity_id: str, target_region_id: str) -> bool:
        """Move an entity from its current region to a target region.

        Args:
            entity_id: ID of the entity to move.
            target_region_id: ID of the destination region.

        Returns:
            True if the move was successful, False otherwise.
        """
        entity = self._entities.get(entity_id)
        target_region = self._regions.get(target_region_id)
        if not entity or not target_region:
            return False
        if entity.state == EntityState.DECEASED:
            return False

        alive_in_target = sum(
            1
            for e in self._entities.values()
            if e.region_id == target_region_id and e.state != EntityState.DECEASED
        )
        if alive_in_target >= target_region.population_cap:
            return False

        entity.region_id = target_region_id
        entity.state = EntityState.ALIVE
        return True

    # =========================================================================
    # Resource Management
    # =========================================================================

    def add_resource_node(
        self,
        region_id: str,
        resource_type: ResourceType,
        amount: float,
        max_amount: Optional[float] = None,
        regen_rate: Optional[float] = None,
        position: Optional[Tuple[float, float]] = None,
        quality: float = 0.5,
        depletion_threshold: float = 0.2,
    ) -> Optional[ResourceNode]:
        """Add a resource node to a region.

        Args:
            region_id: The region to place the node in.
            resource_type: Type of resource.
            amount: Initial amount of resource available.
            max_amount: Maximum capacity. Defaults to amount if not set.
            regen_rate: Amount regenerated per tick. Defaults from region multipliers.
            position: (x, y) coordinates within the region.
            quality: Quality multiplier (0.0-1.0).
            depletion_threshold: Below this ratio, regen is halved.

        Returns:
            The created ResourceNode, or None if limits are exceeded.
        """
        if region_id not in self._regions:
            return None
        if len(self._resource_nodes) >= self.MAX_RESOURCE_NODES:
            return None

        # Convert string to enum if needed
        if isinstance(resource_type, str):
            try:
                resource_type = ResourceType(resource_type)
            except ValueError:
                return None

        region = self._regions[region_id]
        multiplier = region.resource_multipliers.get(resource_type.value, 1.0)
        default_regen = _DEFAULT_BASE_REGEN.get(resource_type.value, 1.0)

        node = ResourceNode(
            resource_type=resource_type,
            region_id=region_id,
            amount=amount,
            max_amount=max_amount if max_amount is not None else amount,
            regen_rate=(
                regen_rate
                if regen_rate is not None
                else default_regen * multiplier * quality
            ),
            position=position if position else (random.uniform(0, 100), random.uniform(0, 100)),
            quality=quality,
            depletion_threshold=depletion_threshold,
        )
        self._resource_nodes[node.id] = node
        return node

    def get_resource_node(self, node_id: str) -> Optional[ResourceNode]:
        """Get a resource node by its ID."""
        return self._resource_nodes.get(node_id)

    def list_resource_nodes(
        self,
        region_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> List[ResourceNode]:
        """List resource nodes filtered by optional criteria.

        Args:
            region_id: Filter by region.
            resource_type: Filter by resource type.

        Returns:
            List of matching ResourceNode objects.
        """
        results: List[ResourceNode] = []
        for node in self._resource_nodes.values():
            if region_id is not None and node.region_id != region_id:
                continue
            if resource_type is not None and node.resource_type != resource_type:
                continue
            results.append(node)
        return results

    def consume_resource(
        self, region_id: str, resource_type: ResourceType, amount: float
    ) -> float:
        """Consume a resource amount from nodes in a region.

        Draws from the richest node first.

        Args:
            region_id: The region to consume from.
            resource_type: Type of resource to consume.
            amount: Amount to consume.

        Returns:
            The amount actually consumed (may be less than requested if insufficient).
        """
        nodes = sorted(
            [
                n
                for n in self._resource_nodes.values()
                if n.region_id == region_id and n.resource_type == resource_type
            ],
            key=lambda n: n.amount,
            reverse=True,
        )

        remaining = amount
        consumed = 0.0

        for node in nodes:
            if remaining <= 0:
                break
            take = min(node.amount, remaining)
            node.amount -= take
            consumed += take
            remaining -= take

        return consumed

    def get_resource_total(
        self, region_id: Optional[str] = None, resource_type: Optional[ResourceType] = None
    ) -> float:
        """Get the total amount of resources across nodes.

        Args:
            region_id: Optionally filter by region.
            resource_type: Optionally filter by resource type.

        Returns:
            Total resource amount.
        """
        total = 0.0
        for node in self._resource_nodes.values():
            if region_id is not None and node.region_id != region_id:
                continue
            if resource_type is not None and node.resource_type != resource_type:
                continue
            total += node.amount
        return total

    # =========================================================================
    # Internal Simulation Logic
    # =========================================================================

    def _regenerate_resources(self) -> float:
        """Regenerate resources for all resource nodes.

        Returns:
            Total amount of resources regenerated.
        """
        total_regen = 0.0
        season = self.get_current_season()
        season_effects = _SEASON_EFFECTS.get(season.value, {})

        for node in self._resource_nodes.values():
            if node.is_depleted:
                continue

            effective_regen = node.regen_rate

            # Apply season bonuses
            if node.resource_type == ResourceType.FOOD:
                effective_regen *= season_effects.get("food_regen_bonus", 1.0)
            elif node.resource_type == ResourceType.WOOD:
                effective_regen *= season_effects.get("wood_regen_bonus", 1.0)

            # Halve regen if below depletion threshold
            if node.depletion_ratio < node.depletion_threshold:
                effective_regen *= 0.5

            regen_amount = min(effective_regen, node.max_amount - node.amount)
            node.amount += regen_amount
            total_regen += regen_amount

        self._stats["total_resource_produced"] += total_regen
        return total_regen

    def _consume_resources(self) -> float:
        """Consume resources based on population.

        Each living entity consumes a base amount of resources per tick.

        Returns:
            Total amount of resources consumed.
        """
        total_consumed = 0.0
        alive_entities = [
            e for e in self._entities.values() if e.state == EntityState.ALIVE
        ]

        for entity in alive_entities:
            for res_type, base_rate in _DEFAULT_BASE_CONSUMPTION.items():
                consumed = self.consume_resource(
                    entity.region_id,
                    ResourceType(res_type),
                    base_rate,
                )
                total_consumed += consumed

        self._stats["total_resource_consumed"] += total_consumed
        return total_consumed

    def _age_entities(self) -> None:
        """Age all living entities by one tick."""
        for entity in self._entities.values():
            if entity.state == EntityState.DECEASED:
                continue
            entity.age += 1
            if entity.age >= entity.max_age * 0.7:
                entity.state = EntityState.AGING

    def _process_population(self) -> Tuple[int, int]:
        """Process births and deaths for the current tick.

        Returns:
            Tuple of (births, deaths).
        """
        births = 0
        deaths = 0
        season = self.get_current_season()
        birth_bonus = _SEASON_EFFECTS.get(season.value, {}).get("birth_rate_bonus", 1.0)

        # Track entities to remove (died of old age)
        to_remove: List[str] = []

        for entity in self._entities.values():
            if entity.state == EntityState.DECEASED:
                continue

            # Natural death from old age
            if entity.age >= entity.max_age:
                entity.state = EntityState.DECEASED
                to_remove.append(entity.id)
                deaths += 1
                self._stats["total_natural_deaths"] += 1
                continue

            # Death from starvation (no food in region)
            food_total = self.get_resource_total(
                region_id=entity.region_id, resource_type=ResourceType.FOOD
            )
            alive_in_region = sum(
                1
                for e in self._entities.values()
                if e.region_id == entity.region_id and e.state != EntityState.DECEASED
            )
            if food_total <= 0 and alive_in_region > 0 and random.random() < 0.02:
                entity.state = EntityState.DECEASED
                to_remove.append(entity.id)
                deaths += 1
                continue

            # Reproduction chance
            if entity.state == EntityState.ALIVE and entity.age >= 20 and entity.age <= entity.max_age * 0.6:
                base_birth_chance = 0.005 * birth_bonus
                region = self._regions.get(entity.region_id)
                if region:
                    alive_in_region = sum(
                        1
                        for e in self._entities.values()
                        if e.region_id == entity.region_id
                        and e.state != EntityState.DECEASED
                    )
                    capacity_ratio = alive_in_region / max(1, region.population_cap)
                    if capacity_ratio < 0.8 and random.random() < base_birth_chance:
                        baby_name = f"{entity.name}'s child"
                        self.create_entity(
                            name=baby_name,
                            entity_type=entity.entity_type,
                            region_id=entity.region_id,
                            position=(
                                entity.position[0] + random.uniform(-5, 5),
                                entity.position[1] + random.uniform(-5, 5),
                            ),
                        )
                        births += 1
                        self._stats["total_births"] += 1

        self._stats["total_entities_died"] += deaths
        return births, deaths

    def _process_migration(self) -> int:
        """Process migration between connected regions.

        Entities may migrate to connected regions based on population pressure
        and resource availability.

        Returns:
            Number of entities that migrated.
        """
        migrated = 0
        season = self.get_current_season()
        migration_chance = _SEASON_EFFECTS.get(season.value, {}).get("migration_chance", 0.03)

        for region in self._regions.values():
            if not region.connected_regions:
                continue

            alive_in_region = sum(
                1
                for e in self._entities.values()
                if e.region_id == region.id and e.state != EntityState.DECEASED
            )
            capacity_ratio = alive_in_region / max(1, region.population_cap)

            # Overcrowded regions push entities out
            if capacity_ratio > 0.85:
                for entity in list(self._entities.values()):
                    if entity.region_id != region.id:
                        continue
                    if entity.state == EntityState.DECEASED:
                        continue
                    if random.random() < migration_chance * (capacity_ratio - 0.8):
                        target_region_id = random.choice(region.connected_regions)
                        if self.move_entity(entity.id, target_region_id):
                            entity.state = EntityState.MIGRATING
                            migrated += 1
                            self._stats["total_migrations"] += 1

        return migrated

    def _generate_events(self) -> List[SimulationEvent]:
        """Generate emergent world events based on current state conditions.

        Evaluates event templates against current world state and triggers
        events that meet their conditions.

        Returns:
            List of newly generated SimulationEvent objects.
        """
        new_events: List[SimulationEvent] = []
        season = self.get_current_season()

        for region in self._regions.values():
            alive_in_region = sum(
                1
                for e in self._entities.values()
                if e.region_id == region.id and e.state != EntityState.DECEASED
            )
            food_total = self.get_resource_total(
                region_id=region.id, resource_type=ResourceType.FOOD
            )
            living_entities = [
                e
                for e in self._entities.values()
                if e.region_id == region.id and e.state != EntityState.DECEASED
            ]

            for template in _EVENT_TEMPLATES:
                conditions = template.get("trigger_conditions", {})

                # Check population minimum
                min_pop = conditions.get("min_population", 0)
                if alive_in_region < min_pop:
                    continue

                # Check season condition
                required_season = conditions.get("season")
                if required_season and required_season != season.value:
                    continue

                # Check food ratio condition
                food_below = conditions.get("food_below_ratio")
                if food_below is not None:
                    max_possible_food = alive_in_region * 10.0
                    food_ratio = food_total / max(1.0, max_possible_food)
                    if food_ratio >= food_below:
                        continue

                # Event trigger probability based on severity and conditions
                base_chance = 0.01
                severity = template.get("base_severity", 0.5)
                disaster_chance = _SEASON_EFFECTS.get(season.value, {}).get(
                    "disaster_chance", 0.05
                )

                if template["category"] == EventCategory.NATURAL.value:
                    trigger_chance = base_chance + disaster_chance * severity
                elif template["category"] == EventCategory.ECONOMIC.value:
                    trigger_chance = base_chance + 0.005 * (alive_in_region / 100.0)
                elif template["category"] == EventCategory.SOCIAL.value:
                    trigger_chance = base_chance + 0.003 * (alive_in_region / 50.0)
                elif template["category"] == EventCategory.MAGICAL.value:
                    mana_total = self.get_resource_total(
                        region_id=region.id, resource_type=ResourceType.MANA
                    )
                    trigger_chance = base_chance + 0.002 * (mana_total / 100.0)
                elif template["category"] == EventCategory.MILITARY.value:
                    trigger_chance = base_chance + 0.002 * (alive_in_region / 100.0)
                else:
                    trigger_chance = base_chance + 0.001 * (alive_in_region / 100.0)

                if random.random() >= trigger_chance:
                    continue

                # Generate the event
                description = template["description_template"].format(region=region.name)
                affected_resources = list(template.get("affected_resources", []))
                affected_entities = [
                    e.id
                    for e in random.sample(
                        living_entities,
                        min(len(living_entities), max(1, int(alive_in_region * severity))),
                    )
                ] if living_entities else []

                event = SimulationEvent(
                    event_type=template["event_type"],
                    category=EventCategory(template["category"]),
                    region_id=region.id,
                    description=description,
                    severity=severity + random.uniform(-0.1, 0.1),
                    affected_entities=affected_entities,
                    affected_resources=affected_resources,
                    timestamp=self._tick,
                )

                # Apply resource impact
                resource_impact = template.get("resource_impact", 0.0)
                for res_type_str in affected_resources:
                    res_type = ResourceType(res_type_str)
                    if res_type == ResourceType.POPULATION:
                        if resource_impact < 0:
                            # Kill some entities
                            kill_count = max(
                                1, int(alive_in_region * abs(resource_impact) * severity)
                            )
                            for entity in random.sample(
                                living_entities,
                                min(len(living_entities), kill_count),
                            ):
                                entity.state = EntityState.DECEASED
                                self._stats["total_entities_died"] += 1
                        else:
                            # Population boost via spawning
                            spawn_count = max(
                                1, int(alive_in_region * resource_impact * severity)
                            )
                            for _ in range(min(spawn_count, 10)):
                                self.create_entity(
                                    name=f"{region.name} settler",
                                    entity_type=random.choice(["human", "villager", "merchant"]),
                                    region_id=region.id,
                                )
                    else:
                        # Apply to resource nodes
                        for node in self._resource_nodes.values():
                            if node.region_id == region.id and node.resource_type == res_type:
                                change = node.max_amount * resource_impact * severity
                                node.amount = max(
                                    0.0, min(node.max_amount, node.amount + change)
                                )

                self._events.append(event)
                new_events.append(event)
                self._stats["total_events_generated"] += 1
                self._stats["events_by_category"][event.category.value] = (
                    self._stats["events_by_category"].get(event.category.value, 0) + 1
                )
                self._stats["events_by_type"][event.event_type] = (
                    self._stats["events_by_type"].get(event.event_type, 0) + 1
                )

                # Schedule causal chain events
                self._schedule_causal_chain(event)

                # Limit events per tick per region to avoid event spam
                if len(new_events) >= 3:
                    break

        return new_events

    def _schedule_causal_chain(self, parent_event: SimulationEvent) -> None:
        """Schedule potential causal chain events from a parent event.

        Args:
            parent_event: The event that may cause subsequent events.
        """
        chain_templates = _CAUSAL_CHAIN_TEMPLATES.get(parent_event.event_type, [])
        for chain in chain_templates:
            if random.random() < chain["probability"]:
                delay = chain["delay_ticks"]
                scheduled_tick = self._tick + delay
                if scheduled_tick not in self._pending_causal:
                    self._pending_causal[scheduled_tick] = []
                self._pending_causal[scheduled_tick].append(
                    (chain["effect_event"], parent_event.id, parent_event.region_id)
                )

    def _resolve_pending_causal(self) -> None:
        """Resolve any causal events scheduled for the current tick."""
        if self._tick not in self._pending_causal:
            return

        pending = self._pending_causal.pop(self._tick)
        for effect_type, parent_id, region_id in pending:
            region = self._regions.get(region_id)
            if not region:
                continue

            parent_event = None
            for evt in self._events:
                if evt.id == parent_id:
                    parent_event = evt
                    break
            if not parent_event:
                continue

            # Find the template for this effect event type
            template = None
            for tpl in _EVENT_TEMPLATES:
                if tpl["event_type"] == effect_type:
                    template = tpl
                    break
            if not template:
                continue

            alive_in_region = sum(
                1
                for e in self._entities.values()
                if e.region_id == region_id and e.state != EntityState.DECEASED
            )
            living_entities = [
                e
                for e in self._entities.values()
                if e.region_id == region_id and e.state != EntityState.DECEASED
            ]

            description = template["description_template"].format(region=region.name)
            severity = template.get("base_severity", 0.5) * parent_event.severity

            affected_entities = (
                [
                    e.id
                    for e in random.sample(
                        living_entities,
                        min(len(living_entities), max(1, int(alive_in_region * severity))),
                    )
                ]
                if living_entities
                else []
            )

            child_event = SimulationEvent(
                event_type=effect_type,
                category=EventCategory(template["category"]),
                region_id=region_id,
                description=description,
                severity=min(1.0, severity),
                affected_entities=affected_entities,
                affected_resources=list(template.get("affected_resources", [])),
                timestamp=self._tick,
                causal_parent_id=parent_id,
            )

            # Apply resource impact
            resource_impact = template.get("resource_impact", 0.0)
            for res_type_str in template.get("affected_resources", []):
                res_type = ResourceType(res_type_str)
                if res_type == ResourceType.POPULATION:
                    if resource_impact < 0:
                        kill_count = max(1, int(alive_in_region * abs(resource_impact) * severity))
                        for entity in random.sample(
                            living_entities,
                            min(len(living_entities), kill_count),
                        ):
                            entity.state = EntityState.DECEASED
                            self._stats["total_entities_died"] += 1
                else:
                    for node in self._resource_nodes.values():
                        if node.region_id == region_id and node.resource_type == res_type:
                            change = node.max_amount * resource_impact * severity
                            node.amount = max(0.0, min(node.max_amount, node.amount + change))

            self._events.append(child_event)
            parent_event.causal_children.append(child_event.id)
            self._stats["total_events_generated"] += 1
            self._stats["events_by_category"][child_event.category.value] = (
                self._stats["events_by_category"].get(child_event.category.value, 0) + 1
            )
            self._stats["events_by_type"][child_event.event_type] = (
                self._stats["events_by_type"].get(child_event.event_type, 0) + 1
            )

            # Create causal link
            link = CausalLink(
                cause_event_id=parent_id,
                effect_event_id=child_event.id,
                probability=0.5,
                description=f"'{parent_event.event_type}' led to '{effect_type}' in {region.name}",
                confidence=min(1.0, parent_event.severity),
            )
            self._causal_links.append(link)

    # =========================================================================
    # World State & Snapshots
    # =========================================================================

    def get_state(self) -> Dict[str, Any]:
        """Get a summary of the current world state.

        Returns:
            A dict with current simulation state summary.
        """
        season = self.get_current_season()
        day_phase = self.get_day_phase()
        alive_count = sum(
            1 for e in self._entities.values() if e.state != EntityState.DECEASED
        )
        resource_totals: Dict[str, float] = {}
        for rt in ResourceType:
            if rt == ResourceType.POPULATION:
                continue
            resource_totals[rt.value] = self.get_resource_total(resource_type=rt)

        return {
            "tick": self._tick,
            "day": self.get_current_day(),
            "year": self.get_current_year(),
            "season": season.value,
            "day_phase": day_phase.value,
            "speed": self._speed.value,
            "is_paused": self._paused,
            "region_count": len(self._regions),
            "entity_count": len(self._entities),
            "alive_count": alive_count,
            "resource_node_count": len(self._resource_nodes),
            "event_count": len(self._events),
            "resource_totals": resource_totals,
        }

    def take_snapshot(self) -> WorldStateSnapshot:
        """Create a complete world state snapshot for save/load/rollback.

        Returns:
            A WorldStateSnapshot with full serializable world state.
        """
        if len(self._snapshots) >= self.MAX_SNAPSHOTS:
            self._snapshots.pop(0)

        season = self.get_current_season()
        alive_count = sum(
            1 for e in self._entities.values() if e.state != EntityState.DECEASED
        )
        resource_totals: Dict[str, float] = {}
        for rt in ResourceType:
            if rt == ResourceType.POPULATION:
                continue
            resource_totals[rt.value] = self.get_resource_total(resource_type=rt)

        snapshot = WorldStateSnapshot(
            sim_time=self._tick,
            day=self.get_current_day(),
            season=season.value,
            year=self.get_current_year(),
            population_count=alive_count,
            resource_totals=resource_totals,
            active_events=[e.id for e in self._events[-20:]],
            entities=[e.to_dict() for e in self._entities.values()],
            regions=[r.to_dict() for r in self._regions.values()],
            timestamp=_time_module.time(),
        )
        self._snapshots.append(snapshot)
        self._stats["total_snapshots_taken"] += 1
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[WorldStateSnapshot]:
        """Get a specific snapshot by its ID."""
        for snap in self._snapshots:
            if snap.id == snapshot_id:
                return snap
        return None

    def list_snapshots(self) -> List[WorldStateSnapshot]:
        """List all snapshots in chronological order."""
        return list(self._snapshots)

    def get_delta_between_snapshots(
        self, snapshot_a_id: str, snapshot_b_id: str
    ) -> Optional[Dict[str, Any]]:
        """Compute the delta between two snapshots.

        Args:
            snapshot_a_id: ID of the earlier snapshot.
            snapshot_b_id: ID of the later snapshot.

        Returns:
            A dict describing the differences, or None if not found.
        """
        snap_a = self.get_snapshot(snapshot_a_id)
        snap_b = self.get_snapshot(snapshot_b_id)
        if not snap_a or not snap_b:
            return None

        return {
            "ticks_elapsed": snap_b.sim_time - snap_a.sim_time,
            "population_delta": snap_b.population_count - snap_a.population_count,
            "resource_deltas": {
                k: round(snap_b.resource_totals.get(k, 0) - snap_a.resource_totals.get(k, 0), 2)
                for k in set(snap_a.resource_totals) | set(snap_b.resource_totals)
            },
            "new_events_count": len(snap_b.active_events) - len(snap_a.active_events),
            "from_tick": snap_a.sim_time,
            "to_tick": snap_b.sim_time,
        }

    # =========================================================================
    # Event Queries
    # =========================================================================

    def get_events(
        self,
        since_tick: Optional[int] = None,
        category: Optional[EventCategory] = None,
        region_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[SimulationEvent]:
        """Query events with optional filters.

        Args:
            since_tick: Only return events after this tick.
            category: Filter by event category.
            region_id: Filter by region.
            event_type: Filter by event type.
            limit: Maximum number of events to return.

        Returns:
            List of matching SimulationEvent objects.
        """
        results: List[SimulationEvent] = []
        for event in reversed(self._events):
            if since_tick is not None and event.timestamp < since_tick:
                continue
            if category is not None and event.category != category:
                continue
            if region_id is not None and event.region_id != region_id:
                continue
            if event_type is not None and event.event_type != event_type:
                continue
            results.append(event)
            if len(results) >= limit:
                break
        return list(reversed(results))

    def get_causal_chain(self, event_id: str) -> Dict[str, Any]:
        """Trace the causal chain for a specific event.

        Walks both upstream (causes) and downstream (effects) to build
        a complete causal graph.

        Args:
            event_id: The event to trace from.

        Returns:
            A dict with upstream_causes, downstream_effects, and chain_graph.
        """
        event = None
        for evt in self._events:
            if evt.id == event_id:
                event = evt
                break
        if not event:
            return {"error": f"Event '{event_id}' not found"}

        # Trace upstream
        upstream: List[Dict[str, Any]] = []
        current = event
        while current.causal_parent_id:
            parent = None
            for evt in self._events:
                if evt.id == current.causal_parent_id:
                    parent = evt
                    break
            if not parent:
                break
            link = None
            for cl in self._causal_links:
                if cl.cause_event_id == parent.id and cl.effect_event_id == current.id:
                    link = cl
                    break
            upstream.append({
                "event_id": parent.id,
                "event_type": parent.event_type,
                "description": parent.description,
                "severity": parent.severity,
                "timestamp": parent.timestamp,
                "confidence": link.confidence if link else 0.0,
            })
            current = parent

        # Trace downstream
        downstream: List[Dict[str, Any]] = []
        queue = list(event.causal_children)
        visited: Set[str] = set()
        while queue:
            child_id = queue.pop(0)
            if child_id in visited:
                continue
            visited.add(child_id)
            child = None
            for evt in self._events:
                if evt.id == child_id:
                    child = evt
                    break
            if not child:
                continue
            link = None
            for cl in self._causal_links:
                if cl.cause_event_id == event_id and cl.effect_event_id == child.id:
                    link = cl
                    break
            downstream.append({
                "event_id": child.id,
                "event_type": child.event_type,
                "description": child.description,
                "severity": child.severity,
                "timestamp": child.timestamp,
                "confidence": link.confidence if link else 0.0,
            })
            queue.extend(child.causal_children)

        return {
            "root_event": event.to_dict(),
            "upstream_causes": upstream,
            "downstream_effects": downstream,
            "total_chain_length": len(upstream) + len(downstream),
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_population_stats(self) -> Dict[str, Any]:
        """Get detailed population statistics.

        Returns:
            A dict with population breakdowns.
        """
        alive = [e for e in self._entities.values() if e.state != EntityState.DECEASED]
        type_counts: Dict[str, int] = {}
        region_counts: Dict[str, int] = {}
        state_counts: Dict[str, int] = {}
        age_groups: Dict[str, int] = {"young": 0, "adult": 0, "elder": 0, "ancient": 0}

        for entity in alive:
            type_counts[entity.entity_type] = type_counts.get(entity.entity_type, 0) + 1
            region_counts[entity.region_id] = region_counts.get(entity.region_id, 0) + 1
            state_counts[entity.state.value] = state_counts.get(entity.state.value, 0) + 1

            if entity.max_age > 0:
                age_ratio = entity.age / entity.max_age
                if age_ratio < 0.25:
                    age_groups["young"] += 1
                elif age_ratio < 0.6:
                    age_groups["adult"] += 1
                elif age_ratio < 0.9:
                    age_groups["elder"] += 1
                else:
                    age_groups["ancient"] += 1

        return {
            "total_population": len(alive),
            "total_deceased": sum(
                1 for e in self._entities.values() if e.state == EntityState.DECEASED
            ),
            "by_type": type_counts,
            "by_region": region_counts,
            "by_state": state_counts,
            "age_groups": age_groups,
            "average_age": sum(e.age for e in alive) / max(1, len(alive)),
            "births": self._stats["total_births"],
            "natural_deaths": self._stats["total_natural_deaths"],
            "migrations": self._stats["total_migrations"],
            "peak_population": self._stats["peak_population"],
        }

    def get_resource_stats(self) -> Dict[str, Any]:
        """Get detailed resource statistics.

        Returns:
            A dict with resource breakdowns.
        """
        by_type: Dict[str, Dict[str, Any]] = {}
        for rt in ResourceType:
            if rt == ResourceType.POPULATION:
                continue
            nodes = [
                n for n in self._resource_nodes.values() if n.resource_type == rt
            ]
            if not nodes:
                continue
            total_amount = sum(n.amount for n in nodes)
            total_max = sum(n.max_amount for n in nodes)
            by_type[rt.value] = {
                "total_amount": round(total_amount, 2),
                "total_max": round(total_max, 2),
                "fill_ratio": round(total_amount / max(1.0, total_max), 2),
                "node_count": len(nodes),
                "depleted_nodes": sum(1 for n in nodes if n.is_depleted),
                "avg_quality": round(sum(n.quality for n in nodes) / len(nodes), 2),
            }

        by_region: Dict[str, Dict[str, float]] = {}
        for region in self._regions.values():
            region_resources: Dict[str, float] = {}
            for rt in ResourceType:
                if rt == ResourceType.POPULATION:
                    continue
                total = self.get_resource_total(region_id=region.id, resource_type=rt)
                if total > 0:
                    region_resources[rt.value] = round(total, 2)
            if region_resources:
                by_region[region.name] = region_resources

        return {
            "by_type": by_type,
            "by_region": by_region,
            "total_produced": round(self._stats["total_resource_produced"], 2),
            "total_consumed": round(self._stats["total_resource_consumed"], 2),
            "net_flow": round(
                self._stats["total_resource_produced"]
                - self._stats["total_resource_consumed"],
                2,
            ),
        }

    def get_event_stats(self) -> Dict[str, Any]:
        """Get detailed event statistics.

        Returns:
            A dict with event breakdowns.
        """
        return {
            "total_events": len(self._events),
            "by_category": dict(self._stats["events_by_category"]),
            "by_type": dict(self._stats["events_by_type"]),
            "causal_links": len(self._causal_links),
            "recent_events": [e.to_dict() for e in self._events[-10:]],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive simulation statistics.

        Returns:
            A dict with all simulation statistics combined.
        """
        return {
            "total_ticks": self._tick,
            "time": {
                "tick": self._tick,
                "day": self.get_current_day(),
                "year": self.get_current_year(),
                "season": self.get_current_season().value,
                "day_phase": self.get_day_phase().value,
                "speed": self._speed.value,
                "is_paused": self._paused,
            },
            "population": self.get_population_stats(),
            "resources": self.get_resource_stats(),
            "events": self.get_event_stats(),
            "world": {
                "region_count": len(self._regions),
                "entity_count": len(self._entities),
                "resource_node_count": len(self._resource_nodes),
                "snapshot_count": len(self._snapshots),
            },
            "cumulative": {
                "total_ticks_advanced": self._stats["total_ticks_advanced"],
                "total_entities_spawned": self._stats["total_entities_spawned"],
                "total_entities_died": self._stats["total_entities_died"],
                "total_events_generated": self._stats["total_events_generated"],
                "total_snapshots_taken": self._stats["total_snapshots_taken"],
            },
        }

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire simulation state to a dict.

        Returns:
            A dict containing the full serializable simulation state.
        """
        return {
            "tick": self._tick,
            "speed": self._speed.value,
            "is_paused": self._paused,
            "regions": {rid: r.to_dict() for rid, r in self._regions.items()},
            "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
            "resource_nodes": {nid: n.to_dict() for nid, n in self._resource_nodes.items()},
            "events": [e.to_dict() for e in self._events],
            "causal_links": [c.to_dict() for c in self._causal_links],
            "snapshots": [s.to_dict() for s in self._snapshots],
            "stats": dict(self._stats),
        }

    def reset(self) -> None:
        """Reset the entire simulation to its initial state."""
        self._tick = 0
        self._speed = SimulationSpeed.PAUSED
        self._paused = True
        self._regions.clear()
        self._entities.clear()
        self._resource_nodes.clear()
        self._events.clear()
        self._causal_links.clear()
        self._snapshots.clear()
        self._pending_causal.clear()
        self._stats = {
            "total_ticks_advanced": 0,
            "total_entities_spawned": 0,
            "total_entities_died": 0,
            "total_events_generated": 0,
            "total_snapshots_taken": 0,
            "total_births": 0,
            "total_natural_deaths": 0,
            "total_migrations": 0,
            "peak_population": 0,
            "total_resource_consumed": 0.0,
            "total_resource_produced": 0.0,
            "events_by_category": {},
            "events_by_type": {},
            "entity_count_by_type": {},
            "entity_count_by_region": {},
        }


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_agent_world_simulation() -> AgentWorldSimulation:
    """Get the singleton AgentWorldSimulation instance.

    Returns:
        The global simulation engine instance.
    """
    return AgentWorldSimulation.get_instance()