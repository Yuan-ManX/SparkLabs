"""
SparkLabs Engine - Civilization Evolution Simulation Engine

A long-term societal development simulation module for the AI-native game
engine. Models technology progression across historical eras, cultural
drift, government transitions, demographic dynamics, and inter-civilization
diplomatic relations over simulated time.

Architecture:
  CivilizationEvolutionEngine (Singleton)
    |-- TechnologyNode      — single researchable technology within a tech tree
    |-- CulturalIdentity    — evolving cultural profile of a civilization
    |-- CivilizationState   — full runtime state of one civilization
    |-- DiplomaticEvent     — recorded relation change between two civilizations
    |-- CivilizationSnapshot— compact historical record of civilization state

Core Capabilities:
  - create_civilization: Found a new civilization with starting parameters
  - research_technology: Unlock a technology node from the tech tree
  - change_government: Transition to a new government type
  - evolve_culture: Shift a specific cultural aspect over time
  - establish_relation: Set the diplomatic relation between two civilizations
  - simulate_tick: Advance a civilization by one simulation step
  - simulate_ticks: Advance a civilization by multiple simulation steps
  - assess_stability: Analyze the factors contributing to stability
  - get_stats: Global engine statistics and health summary

Usage:
    engine = get_civilization_engine()
    civ = engine.create_civilization(
        name="Aurelia",
        starting_era=TechEra.STONE_AGE,
        government=GovernmentType.TRIBAL,
        population=120,
        territory_size=10.0,
        resources={"food": 200, "wood": 80, "stone": 40},
    )
    engine.research_technology(civ.civ_id, "stone_tools")
    snapshots = engine.simulate_ticks(civ.civ_id, 50)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TechEra(Enum):
    """Chronological technology eras ordered from earliest to latest."""
    STONE_AGE = "stone_age"
    BRONZE_AGE = "bronze_age"
    IRON_AGE = "iron_age"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    INDUSTRIAL = "industrial"
    MODERN = "modern"
    INFORMATION = "information"
    FUTURE = "future"


class GovernmentType(Enum):
    """Forms of government that a civilization may adopt."""
    TRIBAL = "tribal"
    MONARCHY = "monarchy"
    REPUBLIC = "republic"
    THEOCRACY = "theocracy"
    OLIGARCHY = "oligarchy"
    DEMOCRACY = "democracy"
    EMPIRE = "empire"
    FEDERATION = "federation"


class RelationStatus(Enum):
    """Diplomatic relation states between two civilizations."""
    ALLIANCE = "alliance"
    TRADE_PACT = "trade_pact"
    NEUTRAL = "neutral"
    RIVALRY = "rivalry"
    COLD_WAR = "cold_war"
    WAR = "war"
    VASSAL = "vassal"


class CulturalAspect(Enum):
    """Discrete aspects of a civilization's cultural identity."""
    LANGUAGE = "language"
    RELIGION = "religion"
    ART = "art"
    ARCHITECTURE = "architecture"
    CUISINE = "cuisine"
    CUSTOMS = "customs"
    VALUES = "values"


# ---------------------------------------------------------------------------
# Era Configuration
# ---------------------------------------------------------------------------

# Ordered list of eras used for advancement checks.
_ERA_ORDER: List[TechEra] = [
    TechEra.STONE_AGE,
    TechEra.BRONZE_AGE,
    TechEra.IRON_AGE,
    TechEra.MEDIEVAL,
    TechEra.RENAISSANCE,
    TechEra.INDUSTRIAL,
    TechEra.MODERN,
    TechEra.INFORMATION,
    TechEra.FUTURE,
]

# Tech level thresholds required to advance into each era.
_ERA_TECH_THRESHOLDS: Dict[TechEra, float] = {
    TechEra.STONE_AGE: 0.0,
    TechEra.BRONZE_AGE: 3.0,
    TechEra.IRON_AGE: 7.0,
    TechEra.MEDIEVAL: 12.0,
    TechEra.RENAISSANCE: 18.0,
    TechEra.INDUSTRIAL: 25.0,
    TechEra.MODERN: 34.0,
    TechEra.INFORMATION: 44.0,
    TechEra.FUTURE: 56.0,
}

# ---------------------------------------------------------------------------
# Government Modifiers
# ---------------------------------------------------------------------------

# Each government type applies modifiers to stability, military, economy,
# research, and culture. Values are multiplicative factors centered on 1.0.
_GOVERNMENT_MODIFIERS: Dict[GovernmentType, Dict[str, float]] = {
    GovernmentType.TRIBAL: {
        "stability": 1.10, "military": 0.85, "economy": 0.70,
        "research": 0.60, "culture": 0.80,
    },
    GovernmentType.MONARCHY: {
        "stability": 1.00, "military": 1.15, "economy": 0.95,
        "research": 0.85, "culture": 1.00,
    },
    GovernmentType.REPUBLIC: {
        "stability": 1.05, "military": 0.95, "economy": 1.10,
        "research": 1.10, "culture": 1.05,
    },
    GovernmentType.THEOCRACY: {
        "stability": 1.15, "military": 0.90, "economy": 0.85,
        "research": 0.75, "culture": 1.20,
    },
    GovernmentType.OLIGARCHY: {
        "stability": 0.90, "military": 1.00, "economy": 1.25,
        "research": 1.00, "culture": 0.95,
    },
    GovernmentType.DEMOCRACY: {
        "stability": 1.05, "military": 0.90, "economy": 1.15,
        "research": 1.20, "culture": 1.10,
    },
    GovernmentType.EMPIRE: {
        "stability": 0.85, "military": 1.35, "economy": 1.05,
        "research": 0.95, "culture": 1.05,
    },
    GovernmentType.FEDERATION: {
        "stability": 1.10, "military": 1.05, "economy": 1.20,
        "research": 1.15, "culture": 1.15,
    },
}

# ---------------------------------------------------------------------------
# Relation Impact on Stability
# ---------------------------------------------------------------------------

# Stability delta applied per tick for each active relation type.
_RELATION_STABILITY_IMPACT: Dict[RelationStatus, float] = {
    RelationStatus.ALLIANCE: 0.012,
    RelationStatus.TRADE_PACT: 0.008,
    RelationStatus.NEUTRAL: 0.0,
    RelationStatus.RIVALRY: -0.010,
    RelationStatus.COLD_WAR: -0.020,
    RelationStatus.WAR: -0.060,
    RelationStatus.VASSAL: -0.015,
}

# ---------------------------------------------------------------------------
# Default Technology Tree
# ---------------------------------------------------------------------------

# A curated set of technology nodes spanning all eras. Each node lists its
# prerequisites (tech_ids that must be unlocked first) and effects applied
# to the civilization upon unlocking.
_DEFAULT_TECH_TREE: List[Dict[str, Any]] = [
    # -- Stone Age --
    {
        "tech_id": "stone_tools", "name": "Stone Tools", "era": TechEra.STONE_AGE,
        "description": "Basic knapped tool production from flint and obsidian.",
        "prerequisites": [], "research_cost": 2.0,
        "effects": {"military": 0.05, "economy": 0.05, "research": 0.02},
    },
    {
        "tech_id": "fire_mastery", "name": "Fire Mastery", "era": TechEra.STONE_AGE,
        "description": "Controlled fire for cooking, warmth, and protection.",
        "prerequisites": [], "research_cost": 2.0,
        "effects": {"stability": 0.05, "economy": 0.03, "culture": 0.02},
    },
    {
        "tech_id": "basic_agriculture", "name": "Basic Agriculture", "era": TechEra.STONE_AGE,
        "description": "Domestication of staple crops enabling settled life.",
        "prerequisites": ["stone_tools"], "research_cost": 3.0,
        "effects": {"economy": 0.10, "stability": 0.05, "population_growth": 0.05},
    },
    # -- Bronze Age --
    {
        "tech_id": "bronze_working", "name": "Bronze Working", "era": TechEra.BRONZE_AGE,
        "description": "Smelting copper and tin alloys for durable tools and weapons.",
        "prerequisites": ["fire_mastery"], "research_cost": 4.0,
        "effects": {"military": 0.10, "economy": 0.05, "research": 0.03},
    },
    {
        "tech_id": "pottery", "name": "Pottery", "era": TechEra.BRONZE_AGE,
        "description": "Fired ceramic vessels for storage and trade.",
        "prerequisites": ["fire_mastery"], "research_cost": 3.0,
        "effects": {"economy": 0.05, "culture": 0.05},
    },
    {
        "tech_id": "writing", "name": "Writing", "era": TechEra.BRONZE_AGE,
        "description": "Symbolic record-keeping accelerating knowledge transfer.",
        "prerequisites": ["pottery"], "research_cost": 5.0,
        "effects": {"research": 0.15, "culture": 0.10, "stability": 0.03},
    },
    # -- Iron Age --
    {
        "tech_id": "iron_working", "name": "Iron Working", "era": TechEra.IRON_AGE,
        "description": "Smelting iron ore for superior weaponry and implements.",
        "prerequisites": ["bronze_working"], "research_cost": 6.0,
        "effects": {"military": 0.15, "economy": 0.08},
    },
    {
        "tech_id": "masonry", "name": "Masonry", "era": TechEra.IRON_AGE,
        "description": "Cut-stone construction for fortifications and monuments.",
        "prerequisites": ["pottery"], "research_cost": 5.0,
        "effects": {"stability": 0.05, "culture": 0.08, "military": 0.05},
    },
    {
        "tech_id": "currency", "name": "Currency", "era": TechEra.IRON_AGE,
        "description": "Standardized coinage replacing barter exchange.",
        "prerequisites": ["writing"], "research_cost": 6.0,
        "effects": {"economy": 0.15, "culture": 0.03},
    },
    # -- Medieval --
    {
        "tech_id": "feudalism", "name": "Feudalism", "era": TechEra.MEDIEVAL,
        "description": "Hierarchical land tenure organizing military and labor.",
        "prerequisites": ["iron_working", "masonry"], "research_cost": 8.0,
        "effects": {"stability": 0.08, "military": 0.10, "economy": 0.05},
    },
    {
        "tech_id": "mechanical_clock", "name": "Mechanical Clock", "era": TechEra.MEDIEVAL,
        "description": "Precision timekeeping enabling scheduled labor and trade.",
        "prerequisites": ["iron_working"], "research_cost": 7.0,
        "effects": {"economy": 0.05, "research": 0.05, "culture": 0.05},
    },
    {
        "tech_id": "windmills", "name": "Windmills", "era": TechEra.MEDIEVAL,
        "description": "Wind-powered milling and drainage infrastructure.",
        "prerequisites": ["masonry"], "research_cost": 7.0,
        "effects": {"economy": 0.10, "stability": 0.03},
    },
    # -- Renaissance --
    {
        "tech_id": "printing_press", "name": "Printing Press", "era": TechEra.RENAISSANCE,
        "description": "Movable type mass reproduction of texts and ideas.",
        "prerequisites": ["mechanical_clock"], "research_cost": 9.0,
        "effects": {"research": 0.20, "culture": 0.15, "stability": 0.03},
    },
    {
        "tech_id": "navigation", "name": "Navigation", "era": TechEra.RENAISSANCE,
        "description": "Celestial navigation opening long-distance maritime trade.",
        "prerequisites": ["currency"], "research_cost": 9.0,
        "effects": {"economy": 0.15, "culture": 0.08, "military": 0.05},
    },
    {
        "tech_id": "gunpowder", "name": "Gunpowder", "era": TechEra.RENAISSANCE,
        "description": "Explosive propellants transforming warfare.",
        "prerequisites": ["feudalism"], "research_cost": 10.0,
        "effects": {"military": 0.25, "stability": -0.03},
    },
    # -- Industrial --
    {
        "tech_id": "steam_engine", "name": "Steam Engine", "era": TechEra.INDUSTRIAL,
        "description": "Pressurized steam power driving mechanized production.",
        "prerequisites": ["printing_press", "gunpowder"], "research_cost": 12.0,
        "effects": {"economy": 0.25, "military": 0.10, "research": 0.05},
    },
    {
        "tech_id": "railways", "name": "Railways", "era": TechEra.INDUSTRIAL,
        "description": "Steel rail networks moving goods and people at scale.",
        "prerequisites": ["steam_engine"], "research_cost": 11.0,
        "effects": {"economy": 0.15, "stability": 0.05, "military": 0.08},
    },
    {
        "tech_id": "telegraph", "name": "Telegraph", "era": TechEra.INDUSTRIAL,
        "description": "Electrical long-distance instantaneous communication.",
        "prerequisites": ["steam_engine"], "research_cost": 10.0,
        "effects": {"research": 0.10, "military": 0.08, "economy": 0.08},
    },
    # -- Modern --
    {
        "tech_id": "electric_grid", "name": "Electric Grid", "era": TechEra.MODERN,
        "description": "Distributed electrical power for industry and households.",
        "prerequisites": ["telegraph"], "research_cost": 13.0,
        "effects": {"economy": 0.20, "research": 0.10, "stability": 0.05},
    },
    {
        "tech_id": "internal_combustion", "name": "Internal Combustion",
        "era": TechEra.MODERN,
        "description": "Petroleum-fueled engines powering vehicles and aircraft.",
        "prerequisites": ["electric_grid"], "research_cost": 14.0,
        "effects": {"military": 0.20, "economy": 0.15},
    },
    {
        "tech_id": "antibiotics", "name": "Antibiotics", "era": TechEra.MODERN,
        "description": "Bacterial infection treatment dramatically extending lifespans.",
        "prerequisites": ["electric_grid"], "research_cost": 13.0,
        "effects": {"population_growth": 0.15, "stability": 0.08},
    },
    # -- Information --
    {
        "tech_id": "computing", "name": "Computing", "era": TechEra.INFORMATION,
        "description": "Programmable electronic computation automating analysis.",
        "prerequisites": ["electric_grid"], "research_cost": 16.0,
        "effects": {"research": 0.30, "economy": 0.15, "military": 0.10},
    },
    {
        "tech_id": "internet", "name": "Internet", "era": TechEra.INFORMATION,
        "description": "Global packet-switched networking linking all knowledge.",
        "prerequisites": ["computing"], "research_cost": 18.0,
        "effects": {"research": 0.25, "culture": 0.20, "economy": 0.15},
    },
    {
        "tech_id": "satellites", "name": "Satellites", "era": TechEra.INFORMATION,
        "description": "Orbital platforms for communication, navigation, and imaging.",
        "prerequisites": ["internal_combustion", "computing"], "research_cost": 17.0,
        "effects": {"military": 0.15, "research": 0.10, "economy": 0.08},
    },
    # -- Future --
    {
        "tech_id": "fusion_power", "name": "Fusion Power", "era": TechEra.FUTURE,
        "description": "Controlled hydrogen fusion providing abundant clean energy.",
        "prerequisites": ["satellites"], "research_cost": 22.0,
        "effects": {"economy": 0.30, "stability": 0.10, "research": 0.15},
    },
    {
        "tech_id": "genetic_engineering", "name": "Genetic Engineering",
        "era": TechEra.FUTURE,
        "description": "Directed genome modification for health and agriculture.",
        "prerequisites": ["antibiotics", "computing"], "research_cost": 21.0,
        "effects": {"population_growth": 0.20, "stability": 0.08, "research": 0.10},
    },
    {
        "tech_id": "quantum_computing", "name": "Quantum Computing",
        "era": TechEra.FUTURE,
        "description": "Superposition-based computation solving intractable problems.",
        "prerequisites": ["internet", "fusion_power"], "research_cost": 24.0,
        "effects": {"research": 0.40, "military": 0.15, "economy": 0.15},
    },
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TechnologyNode:
    """A single researchable technology within a civilization's tech tree.

    Tracks the research cost, prerequisite technologies, and the effects
    applied to the civilization once the technology is unlocked.
    """
    tech_id: str
    name: str
    era: TechEra
    description: str
    prerequisites: List[str] = field(default_factory=list)
    effects: Dict[str, float] = field(default_factory=dict)
    research_cost: float = 1.0
    unlocked: bool = False
    research_progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tech_id": self.tech_id,
            "name": self.name,
            "era": self.era.value,
            "description": self.description,
            "prerequisites": list(self.prerequisites),
            "effects": dict(self.effects),
            "research_cost": self.research_cost,
            "unlocked": self.unlocked,
            "research_progress": round(self.research_progress, 3),
            "progress_percent": round(
                min(100.0, (self.research_progress / max(0.01, self.research_cost)) * 100.0),
                2,
            ),
        }


@dataclass
class CulturalIdentity:
    """Evolving cultural profile of a civilization.

    Each aspect drifts over time according to the drift_rate, producing
    organic cultural divergence between civilizations.
    """
    culture_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    civilization_id: str = ""
    language: str = "Proto-Tongue"
    religion: str = "Animism"
    art_style: str = "Tribal Motifs"
    architecture_style: str = "Wattle and Daub"
    cuisine: str = "Foraged Staples"
    customs: List[str] = field(default_factory=lambda: ["oral_tradition", "communal_labor"])
    core_values: List[str] = field(default_factory=lambda: ["kinship", "survival"])
    drift_rate: float = 0.02

    def to_dict(self) -> Dict[str, Any]:
        return {
            "culture_id": self.culture_id,
            "civilization_id": self.civilization_id,
            "language": self.language,
            "religion": self.religion,
            "art_style": self.art_style,
            "architecture_style": self.architecture_style,
            "cuisine": self.cuisine,
            "customs": list(self.customs),
            "core_values": list(self.core_values),
            "drift_rate": self.drift_rate,
        }


@dataclass
class CivilizationState:
    """Full runtime state of a single civilization.

    Holds demographic, technological, economic, military, cultural, and
    diplomatic data along with the per-tick simulation accumulator.
    """
    civ_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Unnamed Civilization"
    era: TechEra = TechEra.STONE_AGE
    government: GovernmentType = GovernmentType.TRIBAL
    population: float = 100.0
    territory_size: float = 10.0
    tech_level: float = 0.0
    military_strength: float = 10.0
    economic_power: float = 10.0
    cultural_influence: float = 5.0
    stability: float = 0.70
    resources: Dict[str, float] = field(default_factory=dict)
    tech_tree: Dict[str, TechnologyNode] = field(default_factory=dict)
    relations: Dict[str, RelationStatus] = field(default_factory=dict)
    culture_id: str = ""
    tick: int = 0
    founded_tick: int = 0
    # Aggregate effect multipliers accumulated from unlocked technologies.
    tech_effects: Dict[str, float] = field(default_factory=dict)
    # Per-tick research throughput accumulator.
    research_output: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "civ_id": self.civ_id,
            "name": self.name,
            "era": self.era.value,
            "government": self.government.value,
            "population": round(self.population, 2),
            "territory_size": round(self.territory_size, 2),
            "tech_level": round(self.tech_level, 3),
            "military_strength": round(self.military_strength, 2),
            "economic_power": round(self.economic_power, 2),
            "cultural_influence": round(self.cultural_influence, 2),
            "stability": round(self.stability, 4),
            "resources": {k: round(v, 2) for k, v in self.resources.items()},
            "culture_id": self.culture_id,
            "tick": self.tick,
            "founded_tick": self.founded_tick,
            "unlocked_tech_count": sum(1 for n in self.tech_tree.values() if n.unlocked),
        }


@dataclass
class DiplomaticEvent:
    """Recorded diplomatic relation change between two civilizations."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_civ: str = ""
    target_civ: str = ""
    event_type: str = ""
    description: str = ""
    relation_before: Optional[RelationStatus] = None
    relation_after: Optional[RelationStatus] = None
    tick: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source_civ": self.source_civ,
            "target_civ": self.target_civ,
            "event_type": self.event_type,
            "description": self.description,
            "relation_before": self.relation_before.value if self.relation_before else None,
            "relation_after": self.relation_after.value if self.relation_after else None,
            "tick": self.tick,
            "timestamp": self.timestamp,
        }


@dataclass
class CivilizationSnapshot:
    """Compact historical record of a civilization's state at one tick."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    civ_id: str = ""
    tick: int = 0
    population: float = 0.0
    era: TechEra = TechEra.STONE_AGE
    government: GovernmentType = GovernmentType.TRIBAL
    tech_level: float = 0.0
    stability: float = 0.0
    military_strength: float = 0.0
    economic_power: float = 0.0
    cultural_influence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "civ_id": self.civ_id,
            "tick": self.tick,
            "population": round(self.population, 2),
            "era": self.era.value,
            "government": self.government.value,
            "tech_level": round(self.tech_level, 3),
            "stability": round(self.stability, 4),
            "military_strength": round(self.military_strength, 2),
            "economic_power": round(self.economic_power, 2),
            "cultural_influence": round(self.cultural_influence, 2),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _era_index(era: TechEra) -> int:
    """Return the ordinal position of an era within the progression order."""
    try:
        return _ERA_ORDER.index(era)
    except ValueError:
        return 0


def _next_era(era: TechEra) -> Optional[TechEra]:
    """Return the era immediately following the given one, or None."""
    idx = _era_index(era)
    if idx + 1 < len(_ERA_ORDER):
        return _ERA_ORDER[idx + 1]
    return None


def _build_default_tech_tree() -> Dict[str, TechnologyNode]:
    """Construct a fresh copy of the default technology tree."""
    tree: Dict[str, TechnologyNode] = {}
    for entry in _DEFAULT_TECH_TREE:
        node = TechnologyNode(
            tech_id=entry["tech_id"],
            name=entry["name"],
            era=entry["era"],
            description=entry["description"],
            prerequisites=list(entry.get("prerequisites", [])),
            effects=dict(entry.get("effects", {})),
            research_cost=float(entry.get("research_cost", 1.0)),
            unlocked=False,
            research_progress=0.0,
        )
        tree[node.tech_id] = node
    return tree


# Pool of cultural drift tokens used when evolving aspects organically.
_LANGUAGE_FRAGMENTS = [
    "Aurelian", "Vosk", "Kethric", "Solari", "Dravan", "Myrrish",
    "Tellen", "Quor", "Sylvan", "Halric",
]
_RELIGION_FRAGMENTS = [
    "Sun Cult", "Ancestor Veneration", "River Pantheon", "Sky Worship",
    "Mystic Order", "Sacred Flame", "Lunar Rites", "Earth Communion",
]
_ART_FRAGMENTS = [
    "Geometric Carvings", "Mosaic Tradition", "Fresco Schools",
    "Calligraphic Lineage", "Sculptural Realism", "Tapestry Weaving",
]
_ARCH_FRAGMENTS = [
    "Megalithic", "Columnar", "Vaulted Stone", "Timber Frame",
    "Domed Civic", "Modular Prefab", "Crystal Spire",
]
_CUISINE_FRAGMENTS = [
    "Roasted Grains", "Fermented Stews", "Spiced Flatbreads",
    "Coastal Boils", "Smoke-Cured Meats", "Garden Medleys",
]
_CUSTOM_POOL = [
    "seasonal_festivals", "coming_of_age_rites", "council_elders",
    "trade_caravans", "ancestral_pilgrimages", "craft_guilds",
    "civic_assemblies", "war_dances", "harvest_rituals", "storytelling_nights",
]
_VALUE_POOL = [
    "honor", "wisdom", "prosperity", "harmony", "courage", "innovation",
    "tradition", "equality", "discipline", "mercy", "ambition", "stewardship",
]


# ---------------------------------------------------------------------------
# Main Singleton Class
# ---------------------------------------------------------------------------

class CivilizationEvolutionEngine:
    """Long-term civilization evolution simulation engine.

    Manages the complete lifecycle of multiple civilizations including
    demographic growth, technology research, cultural drift, government
    transitions, and inter-civilization diplomatic relations. All state
    mutations are guarded by a reentrant lock for thread safety.

    Usage:
        engine = get_civilization_engine()
        civ = engine.create_civilization(
            name="Aurelia",
            starting_era=TechEra.STONE_AGE,
            government=GovernmentType.TRIBAL,
            population=150,
            territory_size=12.0,
            resources={"food": 250, "wood": 100},
        )
        engine.simulate_ticks(civ.civ_id, 100)
    """

    _instance: Optional["CivilizationEvolutionEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_HISTORY_PER_CIV: int = 500
    MAX_DIPLOMATIC_EVENTS: int = 1000
    DEFAULT_HISTORY_LIMIT: int = 50

    # Logistic growth tuning constants.
    GROWTH_RATE_BASE: float = 0.015
    CARRYING_CAPACITY_PER_TERRITORY: float = 50.0
    STABILITY_GROWTH_FLOOR: float = 0.20

    # Research throughput tuning constants.
    RESEARCH_BASE: float = 0.05
    RESEARCH_POPULATION_FACTOR: float = 0.0005

    # Diplomatic event probability per tick per neighbor.
    DIPLOMATIC_EVENT_CHANCE: float = 0.04

    def __new__(cls) -> "CivilizationEvolutionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CivilizationEvolutionEngine":
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # -- Civilization registry --
        self._civilizations: Dict[str, CivilizationState] = {}
        self._cultures: Dict[str, CulturalIdentity] = {}

        # -- History tracking --
        self._history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.MAX_HISTORY_PER_CIV)
        )
        self._diplomatic_events: deque = deque(maxlen=self.MAX_DIPLOMATIC_EVENTS)

        # -- Global counters --
        self._total_ticks_simulated: int = 0
        self._total_civilizations_created: int = 0
        self._total_techs_unlocked: int = 0
        self._total_government_changes: int = 0
        self._total_diplomatic_events: int = 0
        self._total_era_advancements: int = 0

    # ------------------------------------------------------------------
    # Civilization Lifecycle
    # ------------------------------------------------------------------

    def create_civilization(
        self,
        name: str,
        starting_era: TechEra,
        government: GovernmentType,
        population: float,
        territory_size: float,
        resources: Optional[Dict[str, float]] = None,
    ) -> CivilizationState:
        """Found a new civilization with the given starting parameters.

        Initializes a fresh tech tree, a default cultural identity, and
        registers the civilization in the engine. Starting era determines
        which initial technologies are pre-unlocked.

        Args:
            name: Human-readable name of the civilization.
            starting_era: The technology era the civilization begins in.
            government: The initial form of government.
            population: Starting population count.
            territory_size: Starting territory area in arbitrary units.
            resources: Starting resource stockpile keyed by resource name.

        Returns:
            The newly created CivilizationState.
        """
        with self._lock:
            civ = CivilizationState(
                name=name,
                era=starting_era,
                government=government,
                population=max(1.0, population),
                territory_size=max(1.0, territory_size),
                resources=dict(resources) if resources else {},
                tech_tree=_build_default_tech_tree(),
                founded_tick=self._total_ticks_simulated,
                tick=0,
            )

            # Pre-unlock technologies whose era is at or before the starting era.
            starting_idx = _era_index(starting_era)
            for node in civ.tech_tree.values():
                if _era_index(node.era) <= starting_idx:
                    node.unlocked = True
                    node.research_progress = node.research_cost
                    self._apply_tech_effects(civ, node)

            civ.tech_level = self._compute_tech_level(civ)

            # Create a default cultural identity.
            culture = CulturalIdentity(
                civilization_id=civ.civ_id,
                language=random.choice(_LANGUAGE_FRAGMENTS) + " Tongue",
                religion=random.choice(_RELIGION_FRAGMENTS),
                art_style=random.choice(_ART_FRAGMENTS),
                architecture_style=random.choice(_ARCH_FRAGMENTS),
                cuisine=random.choice(_CUISINE_FRAGMENTS),
                customs=random.sample(_CUSTOM_POOL, k=min(3, len(_CUSTOM_POOL))),
                core_values=random.sample(_VALUE_POOL, k=min(3, len(_VALUE_POOL))),
                drift_rate=0.02,
            )
            civ.culture_id = culture.culture_id

            self._civilizations[civ.civ_id] = civ
            self._cultures[culture.culture_id] = culture
            self._total_civilizations_created += 1

            # Record an initial snapshot.
            self._record_snapshot(civ)
            return civ

    def get_civilization(self, civ_id: str) -> Optional[CivilizationState]:
        """Retrieve a civilization by id.

        Returns:
            The CivilizationState, or None if not found.
        """
        with self._lock:
            return self._civilizations.get(civ_id)

    # ------------------------------------------------------------------
    # Technology Research
    # ------------------------------------------------------------------

    def research_technology(
        self,
        civ_id: str,
        tech_id: str,
    ) -> TechnologyNode:
        """Attempt to unlock a technology for a civilization.

        Validates that the technology exists, all prerequisites are met,
        and instantly completes its research. Applies the technology's
        effects to the civilization and recomputes the tech level.

        Args:
            civ_id: The civilization attempting the research.
            tech_id: The technology node identifier to unlock.

        Returns:
            The unlocked TechnologyNode.

        Raises:
            KeyError: If the civilization or technology does not exist.
            ValueError: If prerequisites are not satisfied.
        """
        with self._lock:
            civ = self._require_civilization(civ_id)
            node = civ.tech_tree.get(tech_id)
            if node is None:
                raise KeyError(
                    f"Technology '{tech_id}' not found in civilization '{civ_id}'"
                )

            if node.unlocked:
                return node

            missing = [
                p for p in node.prerequisites
                if p not in civ.tech_tree or not civ.tech_tree[p].unlocked
            ]
            if missing:
                raise ValueError(
                    f"Prerequisites not satisfied for '{tech_id}': {missing}"
                )

            node.unlocked = True
            node.research_progress = node.research_cost
            self._apply_tech_effects(civ, node)
            civ.tech_level = self._compute_tech_level(civ)
            self._total_techs_unlocked += 1

            # Era advancement check.
            self._check_era_advancement(civ)

            return node

    def get_tech_tree(self, civ_id: str) -> List[TechnologyNode]:
        """Retrieve the full technology tree for a civilization.

        Returns:
            List of all TechnologyNode objects in the civilization's tree.

        Raises:
            KeyError: If the civilization does not exist.
        """
        with self._lock:
            civ = self._require_civilization(civ_id)
            return list(civ.tech_tree.values())

    def _apply_tech_effects(
        self,
        civ: CivilizationState,
        node: TechnologyNode,
    ) -> None:
        """Accumulate a technology's effect modifiers onto the civilization."""
        for key, value in node.effects.items():
            current = civ.tech_effects.get(key, 0.0)
            civ.tech_effects[key] = current + value

    def _compute_tech_level(self, civ: CivilizationState) -> float:
        """Compute the aggregate tech level from unlocked technologies."""
        level = 0.0
        for node in civ.tech_tree.values():
            if node.unlocked:
                # Weight each technology by its era progression.
                era_weight = 1.0 + _era_index(node.era) * 0.5
                level += era_weight
        return round(level, 3)

    def _check_era_advancement(self, civ: CivilizationState) -> bool:
        """Advance the civilization's era if the tech threshold is met.

        Returns:
            True if the era was advanced, False otherwise.
        """
        next_era = _next_era(civ.era)
        if next_era is None:
            return False
        threshold = _ERA_TECH_THRESHOLDS.get(next_era, float("inf"))
        if civ.tech_level >= threshold:
            civ.era = next_era
            self._total_era_advancements += 1
            return True
        return False

    # ------------------------------------------------------------------
    # Government Transitions
    # ------------------------------------------------------------------

    def change_government(
        self,
        civ_id: str,
        new_government: GovernmentType,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Transition a civilization to a new form of government.

        Records the transition, applies a temporary stability penalty
        proportional to the disruption, and returns a summary dict.

        Args:
            civ_id: The civilization changing government.
            new_government: The target government type.
            reason: Optional human-readable reason for the transition.

        Returns:
            Dictionary describing the transition and its effects.

        Raises:
            KeyError: If the civilization does not exist.
        """
        with self._lock:
            civ = self._require_civilization(civ_id)
            old_government = civ.government

            if old_government == new_government:
                return {
                    "civ_id": civ_id,
                    "changed": False,
                    "reason": "already_governed",
                    "old_government": old_government.value,
                    "new_government": new_government.value,
                }

            # Stability penalty for the transition disruption.
            penalty = random.uniform(0.05, 0.15)
            civ.stability = _clamp(civ.stability - penalty, 0.0, 1.0)
            civ.government = new_government
            self._total_government_changes += 1

            return {
                "civ_id": civ_id,
                "changed": True,
                "old_government": old_government.value,
                "new_government": new_government.value,
                "reason": reason,
                "stability_penalty": round(penalty, 4),
                "stability_after": round(civ.stability, 4),
            }

    # ------------------------------------------------------------------
    # Cultural Evolution
    # ------------------------------------------------------------------

    def evolve_culture(
        self,
        civ_id: str,
        aspect: CulturalAspect,
        new_value: str,
        drift_rate: float,
    ) -> CulturalIdentity:
        """Shift a specific cultural aspect of a civilization.

        Updates the requested aspect to the provided value and adjusts the
        overall drift rate. Used to model deliberate cultural shifts such
        as a religious conversion or an architectural renaissance.

        Args:
            civ_id: The civilization whose culture is evolving.
            aspect: The cultural aspect to modify.
            new_value: The new value for the aspect.
            drift_rate: The new drift rate governing organic drift.

        Returns:
            The updated CulturalIdentity.

        Raises:
            KeyError: If the civilization or its culture does not exist.
        """
        with self._lock:
            civ = self._require_civilization(civ_id)
            culture = self._cultures.get(civ.culture_id)
            if culture is None:
                raise KeyError(
                    f"Culture not found for civilization '{civ_id}'"
                )

            if aspect == CulturalAspect.LANGUAGE:
                culture.language = new_value
            elif aspect == CulturalAspect.RELIGION:
                culture.religion = new_value
            elif aspect == CulturalAspect.ART:
                culture.art_style = new_value
            elif aspect == CulturalAspect.ARCHITECTURE:
                culture.architecture_style = new_value
            elif aspect == CulturalAspect.CUISINE:
                culture.cuisine = new_value
            elif aspect == CulturalAspect.CUSTOMS:
                if new_value not in culture.customs:
                    culture.customs.append(new_value)
            elif aspect == CulturalAspect.VALUES:
                if new_value not in culture.core_values:
                    culture.core_values.append(new_value)

            culture.drift_rate = max(0.0, drift_rate)
            return culture

    def get_culture(self, civ_id: str) -> Optional[CulturalIdentity]:
        """Retrieve the cultural identity of a civilization.

        Returns:
            The CulturalIdentity, or None if the civilization or culture
            does not exist.
        """
        with self._lock:
            civ = self._civilizations.get(civ_id)
            if civ is None:
                return None
            return self._cultures.get(civ.culture_id)

    def _drift_culture(self, civ: CivilizationState) -> None:
        """Apply organic cultural drift for one simulation tick.

        Each aspect has a small chance of shifting toward a new token
        drawn from the fragment pools, scaled by the drift rate.
        """
        culture = self._cultures.get(civ.culture_id)
        if culture is None:
            return

        rate = culture.drift_rate
        if rate <= 0.0:
            return

        if random.random() < rate:
            culture.language = random.choice(_LANGUAGE_FRAGMENTS) + " Tongue"
        if random.random() < rate * 0.8:
            culture.religion = random.choice(_RELIGION_FRAGMENTS)
        if random.random() < rate * 0.7:
            culture.art_style = random.choice(_ART_FRAGMENTS)
        if random.random() < rate * 0.6:
            culture.architecture_style = random.choice(_ARCH_FRAGMENTS)
        if random.random() < rate * 0.5:
            culture.cuisine = random.choice(_CUISINE_FRAGMENTS)
        if random.random() < rate * 0.4:
            new_custom = random.choice(_CUSTOM_POOL)
            if new_custom not in culture.customs:
                if len(culture.customs) >= 6:
                    culture.customs[random.randint(0, len(culture.customs) - 1)] = new_custom
                else:
                    culture.customs.append(new_custom)
        if random.random() < rate * 0.4:
            new_value = random.choice(_VALUE_POOL)
            if new_value not in culture.core_values:
                if len(culture.core_values) >= 6:
                    culture.core_values[random.randint(0, len(culture.core_values) - 1)] = new_value
                else:
                    culture.core_values.append(new_value)

    # ------------------------------------------------------------------
    # Diplomatic Relations
    # ------------------------------------------------------------------

    def establish_relation(
        self,
        source_civ: str,
        target_civ: str,
        relation: RelationStatus,
    ) -> DiplomaticEvent:
        """Set the diplomatic relation between two civilizations.

        Records the previous relation (if any) and creates a DiplomaticEvent
        capturing the transition. Relations are symmetric: setting A->B
        also sets B->A.

        Args:
            source_civ: The civilization initiating the relation.
            target_civ: The civilization receiving the relation.
            relation: The new relation status.

        Returns:
            The recorded DiplomaticEvent.

        Raises:
            KeyError: If either civilization does not exist.
        """
        with self._lock:
            source = self._require_civilization(source_civ)
            target = self._require_civilization(target_civ)
            if source_civ == target_civ:
                raise ValueError("Cannot establish a relation with itself")

            before = source.relations.get(target_civ)
            source.relations[target_civ] = relation
            target.relations[source_civ] = relation

            event = DiplomaticEvent(
                source_civ=source_civ,
                target_civ=target_civ,
                event_type="relation_change",
                description=f"{source.name} set relation with {target.name} to {relation.value}",
                relation_before=before,
                relation_after=relation,
                tick=source.tick,
            )
            self._diplomatic_events.append(event)
            self._total_diplomatic_events += 1
            return event

    def get_relations(self, civ_id: str) -> Dict[str, Any]:
        """Retrieve all diplomatic relations for a civilization.

        Returns:
            Dictionary mapping target civilization ids to relation status
            value strings. Returns an empty dict if the civilization does
            not exist.
        """
        with self._lock:
            civ = self._civilizations.get(civ_id)
            if civ is None:
                return {}
            return {
                target: relation.value
                for target, relation in civ.relations.items()
            }

    def _trigger_random_diplomatic_event(self, civ: CivilizationState) -> None:
        """Probabilistically trigger a diplomatic event with a neighbor.

        Selects a random known civilization and may shift the relation
        one step toward alliance or war depending on relative power and
        a random factor.
        """
        if not civ.relations:
            return
        if random.random() > self.DIPLOMATIC_EVENT_CHANCE:
            return

        target_id = random.choice(list(civ.relations.keys()))
        target = self._civilizations.get(target_id)
        if target is None:
            return

        current = civ.relations.get(target_id, RelationStatus.NEUTRAL)

        # Determine shift direction based on power balance and stability.
        own_power = civ.military_strength + civ.economic_power
        target_power = target.military_strength + target.economic_power
        power_ratio = own_power / max(1.0, target_power)

        # Stronger civilizations tend toward rivalry; stable ones toward pacts.
        if power_ratio > 1.3 and civ.stability < 0.4:
            new_relation = self._escalate_relation(current)
        elif civ.stability > 0.6 and target.stability > 0.6:
            new_relation = self._deescalate_relation(current)
        else:
            # Random walk in either direction.
            if random.random() < 0.5:
                new_relation = self._escalate_relation(current)
            else:
                new_relation = self._deescalate_relation(current)

        if new_relation != current:
            before = civ.relations.get(target_id)
            civ.relations[target_id] = new_relation
            target.relations[civ.civ_id] = new_relation

            event = DiplomaticEvent(
                source_civ=civ.civ_id,
                target_civ=target_id,
                event_type="spontaneous_shift",
                description=(
                    f"Relation between {civ.name} and {target.name} shifted "
                    f"from {current.value} to {new_relation.value}"
                ),
                relation_before=before,
                relation_after=new_relation,
                tick=civ.tick,
            )
            self._diplomatic_events.append(event)
            self._total_diplomatic_events += 1

    @staticmethod
    def _escalate_relation(current: RelationStatus) -> RelationStatus:
        """Move a relation one step toward open conflict."""
        progression = [
            RelationStatus.ALLIANCE,
            RelationStatus.TRADE_PACT,
            RelationStatus.NEUTRAL,
            RelationStatus.RIVALRY,
            RelationStatus.COLD_WAR,
            RelationStatus.WAR,
        ]
        try:
            idx = progression.index(current)
        except ValueError:
            return RelationStatus.RIVALRY
        if idx + 1 < len(progression):
            return progression[idx + 1]
        return current

    @staticmethod
    def _deescalate_relation(current: RelationStatus) -> RelationStatus:
        """Move a relation one step toward alliance."""
        progression = [
            RelationStatus.ALLIANCE,
            RelationStatus.TRADE_PACT,
            RelationStatus.NEUTRAL,
            RelationStatus.RIVALRY,
            RelationStatus.COLD_WAR,
            RelationStatus.WAR,
        ]
        try:
            idx = progression.index(current)
        except ValueError:
            return RelationStatus.NEUTRAL
        if idx - 1 >= 0:
            return progression[idx - 1]
        return current

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate_tick(self, civ_id: str) -> CivilizationSnapshot:
        """Advance a civilization by one simulation tick.

        Performs logistic population growth, accumulates research progress,
        applies cultural drift, recomputes power attributes, may trigger
        diplomatic events, checks for era advancement, and adjusts
        stability based on internal and external factors.

        Args:
            civ_id: The civilization to advance.

        Returns:
            A CivilizationSnapshot capturing the state after the tick.

        Raises:
            KeyError: If the civilization does not exist.
        """
        with self._lock:
            civ = self._require_civilization(civ_id)
            civ.tick += 1
            self._total_ticks_simulated += 1

            self._simulate_population(civ)
            self._simulate_research(civ)
            self._drift_culture(civ)
            self._simulate_power(civ)
            self._trigger_random_diplomatic_event(civ)
            self._simulate_stability(civ)
            self._check_era_advancement(civ)

            snapshot = self._record_snapshot(civ)
            return snapshot

    def simulate_ticks(
        self,
        civ_id: str,
        num_ticks: int,
    ) -> List[CivilizationSnapshot]:
        """Advance a civilization by multiple simulation ticks.

        Args:
            civ_id: The civilization to advance.
            num_ticks: Number of ticks to simulate.

        Returns:
            List of CivilizationSnapshot objects, one per tick.

        Raises:
            KeyError: If the civilization does not exist.
        """
        if num_ticks <= 0:
            return []
        snapshots: List[CivilizationSnapshot] = []
        with self._lock:
            for _ in range(num_ticks):
                snapshots.append(self.simulate_tick(civ_id))
        return snapshots

    def _simulate_population(self, civ: CivilizationState) -> None:
        """Apply logistic population growth constrained by carrying capacity.

        The carrying capacity is derived from territory size and the food
        resource stockpile. Growth rate is modulated by stability and
        population-growth tech effects. Low stability can cause decline.
        """
        gov = _GOVERNMENT_MODIFIERS.get(civ.government, {})
        food = civ.resources.get("food", 0.0)
        resource_factor = 1.0 + (food / 500.0)
        carrying_capacity = (
            civ.territory_size * self.CARRYING_CAPACITY_PER_TERRITORY * resource_factor
        )
        carrying_capacity = max(10.0, carrying_capacity)

        growth_modifier = civ.tech_effects.get("population_growth", 0.0)
        stability_factor = max(
            self.STABILITY_GROWTH_FLOOR,
            civ.stability,
        )
        growth_rate = (
            self.GROWTH_RATE_BASE
            * (1.0 + growth_modifier)
            * stability_factor
            * gov.get("economy", 1.0)
        )

        # Logistic growth: dP = r * P * (1 - P/K)
        population = max(0.0, civ.population)
        if population <= 0:
            civ.population = 0.0
            return

        growth = growth_rate * population * (1.0 - population / carrying_capacity)

        # Famine and instability cause decline when carrying capacity is exceeded.
        if population > carrying_capacity:
            decline = (population - carrying_capacity) * 0.02
            growth -= decline

        # Consume food proportional to population.
        food_consumption = population * 0.05
        if food > 0:
            civ.resources["food"] = max(0.0, food - food_consumption)
            if civ.resources["food"] <= 0.0:
                # Starvation sharply reduces population.
                growth -= population * 0.05

        civ.population = max(0.0, population + growth)

    def _simulate_research(self, civ: CivilizationState) -> None:
        """Accumulate research progress and unlock completed technologies.

        Research throughput scales with population, stability, government
        research modifier, and accumulated research tech effects.
        """
        gov = _GOVERNMENT_MODIFIERS.get(civ.government, {})
        research_modifier = civ.tech_effects.get("research", 0.0)
        stability_factor = max(0.1, civ.stability)

        throughput = (
            self.RESEARCH_BASE
            + civ.population * self.RESEARCH_POPULATION_FACTOR
        ) * (1.0 + research_modifier) * stability_factor * gov.get("research", 1.0)

        civ.research_output = throughput

        # Distribute throughput across the cheapest unlocked-eligible tech.
        candidates = [
            node for node in civ.tech_tree.values()
            if not node.unlocked and self._prerequisites_met(civ, node)
        ]
        if not candidates:
            return

        candidates.sort(key=lambda n: n.research_cost)
        target = candidates[0]
        target.research_progress += throughput

        if target.research_progress >= target.research_cost:
            target.unlocked = True
            target.research_progress = target.research_cost
            self._apply_tech_effects(civ, target)
            civ.tech_level = self._compute_tech_level(civ)
            self._total_techs_unlocked += 1

    @staticmethod
    def _prerequisites_met(civ: CivilizationState, node: TechnologyNode) -> bool:
        """Check whether all prerequisites for a technology are unlocked."""
        for prereq in node.prerequisites:
            prereq_node = civ.tech_tree.get(prereq)
            if prereq_node is None or not prereq_node.unlocked:
                return False
        return True

    def _simulate_power(self, civ: CivilizationState) -> None:
        """Recompute military, economic, and cultural power attributes.

        Each attribute is a function of population, tech level, resources,
        government modifiers, and accumulated tech effects. Values drift
        gradually toward their target to avoid sudden jumps.
        """
        gov = _GOVERNMENT_MODIFIERS.get(civ.government, {})
        pop_factor = math.log1p(max(1.0, civ.population)) / math.log(10.0)
        tech_factor = 1.0 + civ.tech_level * 0.1
        resource_total = sum(civ.resources.values())

        # Military strength.
        military_target = (
            pop_factor * 8.0
            * tech_factor
            * (1.0 + civ.tech_effects.get("military", 0.0))
            * gov.get("military", 1.0)
        )
        civ.military_strength = self._drift_toward(
            civ.military_strength, military_target, 0.10
        )

        # Economic power.
        economy_target = (
            pop_factor * 6.0
            * tech_factor
            * (1.0 + civ.tech_effects.get("economy", 0.0))
            * (1.0 + resource_total / 1000.0)
            * gov.get("economy", 1.0)
        )
        civ.economic_power = self._drift_toward(
            civ.economic_power, economy_target, 0.10
        )

        # Cultural influence.
        culture_target = (
            pop_factor * 4.0
            * tech_factor
            * (1.0 + civ.tech_effects.get("culture", 0.0))
            * gov.get("culture", 1.0)
            * (0.5 + civ.stability * 0.5)
        )
        civ.cultural_influence = self._drift_toward(
            civ.cultural_influence, culture_target, 0.08
        )

    @staticmethod
    def _drift_toward(current: float, target: float, rate: float) -> float:
        """Move current toward target by a fraction determined by rate."""
        return current + (target - current) * rate

    def _simulate_stability(self, civ: CivilizationState) -> None:
        """Adjust stability based on internal and external factors.

        Factors include government type, population pressure relative to
        carrying capacity, active diplomatic relations, and random events.
        """
        gov = _GOVERNMENT_MODIFIERS.get(civ.government, {})
        gov_stability = gov.get("stability", 1.0)

        # Population pressure: penalty when near or above carrying capacity.
        food = civ.resources.get("food", 0.0)
        carrying_capacity = (
            civ.territory_size * self.CARRYING_CAPACITY_PER_TERRITORY
            * (1.0 + food / 500.0)
        )
        pressure_ratio = civ.population / max(1.0, carrying_capacity)
        pressure_penalty = 0.0
        if pressure_ratio > 1.0:
            pressure_penalty = (pressure_ratio - 1.0) * 0.10
        elif pressure_ratio < 0.5:
            pressure_penalty = -0.02  # Low pressure slightly boosts stability.

        # Diplomatic relation impact.
        diplomatic_delta = 0.0
        for relation in civ.relations.values():
            diplomatic_delta += _RELATION_STABILITY_IMPACT.get(relation, 0.0)

        # Tech stability bonus.
        tech_bonus = civ.tech_effects.get("stability", 0.0) * 0.05

        # Random event shock.
        shock = random.gauss(0.0, 0.01)

        # Government stability baseline centered on 0.7 * gov modifier.
        baseline = 0.70 * gov_stability

        target = (
            baseline
            - pressure_penalty
            + diplomatic_delta
            + tech_bonus
            + shock
        )
        target = _clamp(target, 0.0, 1.0)

        # Drift stability toward the computed target.
        civ.stability = _clamp(
            civ.stability + (target - civ.stability) * 0.15, 0.0, 1.0
        )

    # ------------------------------------------------------------------
    # Stability Assessment
    # ------------------------------------------------------------------

    def assess_stability(self, civ_id: str) -> Dict[str, Any]:
        """Analyze the factors contributing to a civilization's stability.

        Returns a detailed breakdown of the baseline, population pressure,
        diplomatic impact, technology bonuses, and random shocks that
        feed into the stability calculation.

        Args:
            civ_id: The civilization to assess.

        Returns:
            Dictionary with the stability breakdown.

        Raises:
            KeyError: If the civilization does not exist.
        """
        with self._lock:
            civ = self._require_civilization(civ_id)
            gov = _GOVERNMENT_MODIFIERS.get(civ.government, {})
            gov_stability = gov.get("stability", 1.0)
            baseline = 0.70 * gov_stability

            food = civ.resources.get("food", 0.0)
            carrying_capacity = (
                civ.territory_size * self.CARRYING_CAPACITY_PER_TERRITORY
                * (1.0 + food / 500.0)
            )
            pressure_ratio = civ.population / max(1.0, carrying_capacity)
            pressure_penalty = 0.0
            if pressure_ratio > 1.0:
                pressure_penalty = (pressure_ratio - 1.0) * 0.10
            elif pressure_ratio < 0.5:
                pressure_penalty = -0.02

            diplomatic_delta = 0.0
            relation_breakdown: Dict[str, int] = defaultdict(int)
            for relation in civ.relations.values():
                diplomatic_delta += _RELATION_STABILITY_IMPACT.get(relation, 0.0)
                relation_breakdown[relation.value] += 1

            tech_bonus = civ.tech_effects.get("stability", 0.0) * 0.05

            return {
                "civ_id": civ_id,
                "current_stability": round(civ.stability, 4),
                "baseline": round(baseline, 4),
                "government_modifier": round(gov_stability, 4),
                "population_pressure_ratio": round(pressure_ratio, 4),
                "pressure_penalty": round(pressure_penalty, 4),
                "diplomatic_impact": round(diplomatic_delta, 4),
                "relation_counts": dict(relation_breakdown),
                "tech_stability_bonus": round(tech_bonus, 4),
                "carrying_capacity": round(carrying_capacity, 2),
                "population": round(civ.population, 2),
                "assessment": self._stability_verdict(civ.stability),
            }

    @staticmethod
    def _stability_verdict(stability: float) -> str:
        """Return a qualitative verdict for a stability value."""
        if stability >= 0.80:
            return "flourishing"
        if stability >= 0.60:
            return "stable"
        if stability >= 0.40:
            return "strained"
        if stability >= 0.20:
            return "unstable"
        return "critical"

    # ------------------------------------------------------------------
    # History and Queries
    # ------------------------------------------------------------------

    def get_history(
        self,
        civ_id: str,
        limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> List[CivilizationSnapshot]:
        """Retrieve recent historical snapshots for a civilization.

        Args:
            civ_id: The civilization to query.
            limit: Maximum number of snapshots to return (most recent first).

        Returns:
            List of CivilizationSnapshot objects in reverse-chronological
            order. Returns an empty list if the civilization does not exist.
        """
        with self._lock:
            history = self._history.get(civ_id)
            if history is None:
                return []
            items = list(history)
            items.reverse()
            return items[:max(0, limit)]

    def _record_snapshot(self, civ: CivilizationState) -> CivilizationSnapshot:
        """Capture and store a snapshot of the civilization's current state."""
        snapshot = CivilizationSnapshot(
            civ_id=civ.civ_id,
            tick=civ.tick,
            population=civ.population,
            era=civ.era,
            government=civ.government,
            tech_level=civ.tech_level,
            stability=civ.stability,
            military_strength=civ.military_strength,
            economic_power=civ.economic_power,
            cultural_influence=civ.cultural_influence,
        )
        self._history[civ.civ_id].append(snapshot)
        return snapshot

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _require_civilization(self, civ_id: str) -> CivilizationState:
        """Return the civilization or raise KeyError if not found."""
        civ = self._civilizations.get(civ_id)
        if civ is None:
            raise KeyError(f"Civilization '{civ_id}' not found")
        return civ

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return global engine statistics and health summary.

        Returns:
            Dictionary with aggregate counts, era distribution, government
            distribution, and diplomatic event totals.
        """
        with self._lock:
            era_counts: Dict[str, int] = defaultdict(int)
            gov_counts: Dict[str, int] = defaultdict(int)
            total_population = 0.0
            total_military = 0.0
            total_economy = 0.0
            total_culture = 0.0
            total_techs_unlocked = 0

            for civ in self._civilizations.values():
                era_counts[civ.era.value] += 1
                gov_counts[civ.government.value] += 1
                total_population += civ.population
                total_military += civ.military_strength
                total_economy += civ.economic_power
                total_culture += civ.cultural_influence
                total_techs_unlocked += sum(
                    1 for n in civ.tech_tree.values() if n.unlocked
                )

            return {
                "total_civilizations": len(self._civilizations),
                "total_civilizations_created": self._total_civilizations_created,
                "total_ticks_simulated": self._total_ticks_simulated,
                "total_techs_unlocked": self._total_techs_unlocked,
                "total_government_changes": self._total_government_changes,
                "total_diplomatic_events": self._total_diplomatic_events,
                "total_era_advancements": self._total_era_advancements,
                "diplomatic_event_history_size": len(self._diplomatic_events),
                "aggregate_population": round(total_population, 2),
                "aggregate_military_strength": round(total_military, 2),
                "aggregate_economic_power": round(total_economy, 2),
                "aggregate_cultural_influence": round(total_culture, 2),
                "active_techs_unlocked": total_techs_unlocked,
                "by_era": dict(era_counts),
                "by_government": dict(gov_counts),
            }


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

def get_civilization_engine() -> CivilizationEvolutionEngine:
    """Return the singleton CivilizationEvolutionEngine instance."""
    return CivilizationEvolutionEngine.get_instance()
