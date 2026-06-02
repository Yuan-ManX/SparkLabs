"""
SparkLabs Agent - World Builder

AI-driven world building system for terrain, biome, and environmental design.
Generates procedurally coherent worlds with region definitions, climate
distribution, biome profiles, settlement placement, trade routes, landmarks,
and world lore.

Architecture:
  AgentWorldBuilder (Singleton)
    |-- Region Generator (terrain types, climate zones, fertility)
    |-- Biome Engine (flora, fauna, soil, threat, resource profiles)
    |-- Settlement Placer (strategic village/town/city placement)
    |-- Trade Network (route generation and adjacency graph)
    |-- Landmark System (natural wonders, ruins, monuments, dungeons, portals)
    |-- Lore Generator (world history and narrative context)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TerrainType(Enum):
    PLAINS = "plains"
    MOUNTAINS = "mountains"
    HILLS = "hills"
    VALLEY = "valley"
    PLATEAU = "plateau"
    CANYON = "canyon"
    MARSH = "marsh"
    DESERT = "desert"
    TUNDRA = "tundra"
    VOLCANIC = "volcanic"
    FOREST = "forest"
    OCEAN = "ocean"
    SWAMP = "swamp"
    CAVE = "cave"
    FLOATING_ISLANDS = "floating_islands"
    CRYSTAL = "crystal"
    MUSHROOM = "mushroom"


class ClimateZone(Enum):
    TROPICAL = "tropical"
    SUBTROPICAL = "subtropical"
    TEMPERATE = "temperate"
    BOREAL = "boreal"
    POLAR = "polar"
    ARID = "arid"
    MEDITERRANEAN = "mediterranean"
    SUBPOLAR = "subpolar"
    CONTINENTAL = "continental"


class PopulationDensity(Enum):
    SPARSE = "sparse"
    RURAL = "rural"
    SUBURBAN = "suburban"
    URBAN = "urban"
    METROPOLITAN = "metropolitan"


class SettlementType(Enum):
    VILLAGE = "village"
    TOWN = "town"
    CITY = "city"
    CAPITAL = "capital"
    FORTRESS = "fortress"


class LandmarkFeatureType(Enum):
    NATURAL_WONDER = "natural_wonder"
    RUIN = "ruin"
    MONUMENT = "monument"
    DUNGEON = "dungeon"
    PORTAL = "portal"


TERRAIN_TEMPLATES: Dict[TerrainType, Dict[str, Any]] = {
    TerrainType.PLAINS: {
        "base_elevation": (0, 200),
        "fertility_range": (0.55, 0.95),
        "resource_types": ["grain", "livestock", "clay", "freshwater"],
        "travel_modifier": 1.0,
        "defense_modifier": 0.3,
    },
    TerrainType.MOUNTAINS: {
        "base_elevation": (1500, 5000),
        "fertility_range": (0.05, 0.25),
        "resource_types": ["iron", "coal", "gold", "stone", "gems"],
        "travel_modifier": 3.5,
        "defense_modifier": 0.9,
    },
    TerrainType.HILLS: {
        "base_elevation": (200, 800),
        "fertility_range": (0.30, 0.65),
        "resource_types": ["copper", "stone", "timber", "herbs"],
        "travel_modifier": 1.6,
        "defense_modifier": 0.6,
    },
    TerrainType.VALLEY: {
        "base_elevation": (50, 400),
        "fertility_range": (0.60, 0.90),
        "resource_types": ["grain", "freshwater", "fruit", "clay"],
        "travel_modifier": 1.1,
        "defense_modifier": 0.4,
    },
    TerrainType.PLATEAU: {
        "base_elevation": (600, 2000),
        "fertility_range": (0.20, 0.50),
        "resource_types": ["stone", "copper", "herbs", "obsidian"],
        "travel_modifier": 1.4,
        "defense_modifier": 0.7,
    },
    TerrainType.CANYON: {
        "base_elevation": (100, 800),
        "fertility_range": (0.10, 0.40),
        "resource_types": ["stone", "gems", "clay", "freshwater"],
        "travel_modifier": 2.2,
        "defense_modifier": 0.8,
    },
    TerrainType.MARSH: {
        "base_elevation": (0, 50),
        "fertility_range": (0.40, 0.75),
        "resource_types": ["peat", "herbs", "fish", "reeds"],
        "travel_modifier": 2.8,
        "defense_modifier": 0.5,
    },
    TerrainType.DESERT: {
        "base_elevation": (0, 500),
        "fertility_range": (0.01, 0.15),
        "resource_types": ["salt", "glass_sand", "oil", "gems"],
        "travel_modifier": 2.0,
        "defense_modifier": 0.2,
    },
    TerrainType.TUNDRA: {
        "base_elevation": (0, 300),
        "fertility_range": (0.02, 0.20),
        "resource_types": ["fur", "oil", "iron", "ice"],
        "travel_modifier": 2.5,
        "defense_modifier": 0.4,
    },
    TerrainType.VOLCANIC: {
        "base_elevation": (300, 3000),
        "fertility_range": (0.15, 0.55),
        "resource_types": ["obsidian", "sulfur", "gems", "iron"],
        "travel_modifier": 2.3,
        "defense_modifier": 0.6,
    },
    TerrainType.FOREST: {
        "base_elevation": (50, 600),
        "fertility_range": (0.50, 0.85),
        "resource_types": ["timber", "herbs", "berries", "game", "mushrooms"],
        "travel_modifier": 1.5,
        "defense_modifier": 0.5,
    },
    TerrainType.OCEAN: {
        "base_elevation": (-5000, -100),
        "fertility_range": (0.0, 0.0),
        "resource_types": ["fish", "pearls", "coral", "salt", "oil"],
        "travel_modifier": 4.0,
        "defense_modifier": 0.1,
    },
    TerrainType.SWAMP: {
        "base_elevation": (0, 30),
        "fertility_range": (0.35, 0.70),
        "resource_types": ["peat", "herbs", "venom", "reeds", "fish"],
        "travel_modifier": 3.0,
        "defense_modifier": 0.4,
    },
    TerrainType.CAVE: {
        "base_elevation": (-200, 200),
        "fertility_range": (0.0, 0.15),
        "resource_types": ["gems", "crystals", "mushrooms", "iron", "coal"],
        "travel_modifier": 2.5,
        "defense_modifier": 0.9,
    },
    TerrainType.FLOATING_ISLANDS: {
        "base_elevation": (500, 3000),
        "fertility_range": (0.30, 0.70),
        "resource_types": ["aether_crystals", "cloud_essence", "wind_stone", "rare_herbs"],
        "travel_modifier": 3.5,
        "defense_modifier": 0.8,
    },
    TerrainType.CRYSTAL: {
        "base_elevation": (100, 1500),
        "fertility_range": (0.05, 0.25),
        "resource_types": ["crystals", "gems", "arcane_dust", "mana_stone"],
        "travel_modifier": 2.0,
        "defense_modifier": 0.6,
    },
    TerrainType.MUSHROOM: {
        "base_elevation": (0, 400),
        "fertility_range": (0.60, 0.95),
        "resource_types": ["giant_mushrooms", "spores", "mycelium", "bioluminescent_dust"],
        "travel_modifier": 1.8,
        "defense_modifier": 0.3,
    },
}

CLIMATE_PROFILES: Dict[ClimateZone, Dict[str, Any]] = {
    ClimateZone.TROPICAL: {
        "temperature_range": (24.0, 35.0),
        "precipitation_range": (1500, 4000),
        "flora_types": ["rainforest_canopy", "tropical_hardwoods", "bamboo", "vines"],
        "fauna_types": ["tropical_birds", "primates", "large_felines", "amphibians"],
        "soil_types": ["laterite", "tropical_loam"],
        "threat_base": 0.6,
    },
    ClimateZone.SUBTROPICAL: {
        "temperature_range": (18.0, 30.0),
        "precipitation_range": (800, 2000),
        "flora_types": ["broadleaf_evergreens", "citrus_groves", "ferns", "cycads"],
        "fauna_types": ["reptiles", "songbirds", "small_mammals", "insects"],
        "soil_types": ["red_earth", "subtropical_clay"],
        "threat_base": 0.4,
    },
    ClimateZone.TEMPERATE: {
        "temperature_range": (0.0, 25.0),
        "precipitation_range": (500, 1500),
        "flora_types": ["deciduous_forests", "grasslands", "oak_groves", "meadow_wildflowers"],
        "fauna_types": ["deer", "wolves", "raptors", "rodents"],
        "soil_types": ["brown_earth", "chernozem"],
        "threat_base": 0.35,
    },
    ClimateZone.BOREAL: {
        "temperature_range": (-15.0, 10.0),
        "precipitation_range": (300, 800),
        "flora_types": ["coniferous_forests", "taiga_scrub", "mosses", "lichens"],
        "fauna_types": ["bears", "moose", "lynx", "winter_birds"],
        "soil_types": ["podzol", "permafrost_margin"],
        "threat_base": 0.45,
    },
    ClimateZone.POLAR: {
        "temperature_range": (-40.0, 0.0),
        "precipitation_range": (50, 300),
        "flora_types": ["tundra_scrub", "mosses", "lichens", "hardy_grasses"],
        "fauna_types": ["polar_bears", "seals", "arctic_foxes", "migratory_birds"],
        "soil_types": ["permafrost", "glacial_till"],
        "threat_base": 0.7,
    },
    ClimateZone.ARID: {
        "temperature_range": (10.0, 45.0),
        "precipitation_range": (10, 250),
        "flora_types": ["cacti", "succulents", "desert_scrub", "drought_grasses"],
        "fauna_types": ["scorpions", "snakes", "camels", "desert_foxes"],
        "soil_types": ["aridisol", "sand_dunes"],
        "threat_base": 0.55,
    },
    ClimateZone.MEDITERRANEAN: {
        "temperature_range": (8.0, 30.0),
        "precipitation_range": (400, 900),
        "flora_types": ["olive_groves", "vineyards", "evergreen_oaks", "aromatic_herbs"],
        "fauna_types": ["goats", "wild_boar", "eagles", "lizards"],
        "soil_types": ["terra_rossa", "calcareous_loam"],
        "threat_base": 0.25,
    },
    ClimateZone.SUBPOLAR: {
        "temperature_range": (-10.0, 10.0),
        "precipitation_range": (200, 700),
        "flora_types": ["conifers", "mosses", "lichens", "hardy_shrubs"],
        "fauna_types": ["wolves", "moose", "bears", "arctic_foxes"],
        "soil_types": ["podzol", "permafrost_loam"],
        "threat_base": 0.45,
    },
    ClimateZone.CONTINENTAL: {
        "temperature_range": (-5.0, 25.0),
        "precipitation_range": (500, 1200),
        "flora_types": ["deciduous_trees", "prairie_grasses", "wildflowers", "shrubs"],
        "fauna_types": ["deer", "bison", "wolves", "eagles"],
        "soil_types": ["chernozem", "loess"],
        "threat_base": 0.30,
    },
}

SETTLEMENT_TYPE_TEMPLATES: Dict[SettlementType, Dict[str, Any]] = {
    SettlementType.VILLAGE: {
        "min_population": 50,
        "max_population": 500,
        "economy_types": ["subsistence_farming", "fishing", "hunting", "herding"],
        "defense_rating": 0.15,
        "trade_route_capacity": 1,
    },
    SettlementType.TOWN: {
        "min_population": 500,
        "max_population": 5000,
        "economy_types": ["crafting", "market_trade", "mining", "lumber"],
        "defense_rating": 0.35,
        "trade_route_capacity": 3,
    },
    SettlementType.CITY: {
        "min_population": 5000,
        "max_population": 50000,
        "economy_types": ["manufacturing", "commerce", "education", "governance"],
        "defense_rating": 0.60,
        "trade_route_capacity": 6,
    },
    SettlementType.CAPITAL: {
        "min_population": 20000,
        "max_population": 200000,
        "economy_types": ["governance", "high_commerce", "culture", "military_command"],
        "defense_rating": 0.85,
        "trade_route_capacity": 10,
    },
    SettlementType.FORTRESS: {
        "min_population": 200,
        "max_population": 3000,
        "economy_types": ["military", "armory", "garrison", "prison"],
        "defense_rating": 0.95,
        "trade_route_capacity": 1,
    },
}

FACTION_POOL: List[str] = [
    "Iron Dominion",
    "Azure Concord",
    "Shadow Syndicate",
    "Emerald Enclave",
    "Frostborn Covenant",
    "Sunstone Coalition",
    "Verdant Collective",
    "Obsidian Pact",
    "Celestial Order",
    "Thornwood Alliance",
]

LANDMARK_NAME_PREFIXES: List[str] = [
    "Crimson", "Shattered", "Eternal", "Frozen", "Gilded",
    "Howling", "Jade", "Lost", "Obsidian", "Radiant",
    "Silent", "Thundering", "Twilight", "Veiled", "Whispering",
]

LANDMARK_NAME_SUFFIXES: List[str] = [
    "Peak", "Depths", "Spire", "Cradle", "Gate",
    "Expanse", "Grove", "Canyon", "Falls", "Reach",
    "Maw", "Citadel", "Vale", "Throne", "Abyss",
]

SETTLEMENT_NAME_PREFIXES: List[str] = [
    "North", "South", "East", "West", "Old",
    "New", "Upper", "Lower", "Fort", "Port",
    "Kings", "Queens", "Grand", "High", "Deep",
]

SETTLEMENT_NAME_SUFFIXES: List[str] = [
    "haven", "shire", "ford", "bridge", "field",
    "vale", "crest", "watch", "gate", "moor",
    "wood", "stone", "mere", "holm", "stead",
]

REGION_NAME_PREFIXES: List[str] = [
    "Aether", "Blight", "Crystal", "Dragon", "Elder",
    "Frost", "Gloom", "Hallow", "Iron", "Jade",
    "Kings", "Lunar", "Mist", "Noble", "Opal",
]

REGION_NAME_SUFFIXES: List[str] = [
    "Wilds", "Expanse", "Reach", "Frontier", "Blight",
    "Highlands", "Lowlands", "Badlands", "Heartlands", "Marches",
    "Shield", "Falls", "Cradle", "Fringe", "Enclave",
]

BIOME_NAME_PREFIXES: List[str] = [
    "Ancient", "Burning", "Crystal", "Dense", "Emerald",
    "Frozen", "Golden", "Hidden", "Ivory", "Lush",
    "Misty", "Shadow", "Silent", "Verdant", "Wild",
]

BIOME_NAME_SUFFIXES: List[str] = [
    "Woodlands", "Fen", "Thicket", "Grove", "Marsh",
    "Steppe", "Savanna", "Tundra", "Jungle", "Heath",
    "Coppice", "Glade", "Bog", "Weald", "Chaparral",
]


@dataclass
class WorldRegion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    terrain_type: TerrainType = TerrainType.PLAINS
    climate: ClimateZone = ClimateZone.TEMPERATE
    size_km2: float = 1000.0
    elevation: float = 0.0
    fertility: float = 0.5
    resources: List[str] = field(default_factory=list)
    population_density: PopulationDensity = PopulationDensity.SPARSE
    biome_signature: str = ""
    borders: List[str] = field(default_factory=list)
    landmarks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "terrain_type": self.terrain_type.value,
            "climate": self.climate.value,
            "size_km2": self.size_km2,
            "elevation": round(self.elevation, 2),
            "fertility": round(self.fertility, 3),
            "resources": self.resources,
            "population_density": self.population_density.value,
            "biome_signature": self.biome_signature,
            "borders": self.borders,
            "landmarks": self.landmarks,
        }


@dataclass
class BiomeProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    temperature_range: Tuple[float, float] = (0.0, 25.0)
    precipitation_range: Tuple[int, int] = (500, 1500)
    flora_species: List[str] = field(default_factory=list)
    fauna_species: List[str] = field(default_factory=list)
    soil_type: str = "loam"
    threat_level: float = 0.3
    resource_richness: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "temperature_range": list(self.temperature_range),
            "precipitation_range": list(self.precipitation_range),
            "flora_species": self.flora_species,
            "fauna_species": self.fauna_species,
            "soil_type": self.soil_type,
            "threat_level": round(self.threat_level, 3),
            "resource_richness": round(self.resource_richness, 3),
        }


@dataclass
class SettlementNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    region_id: str = ""
    population: int = 100
    settlement_type: SettlementType = SettlementType.VILLAGE
    economy_type: str = "subsistence_farming"
    defenses: float = 0.15
    trade_routes: List[str] = field(default_factory=list)
    faction_control: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "region_id": self.region_id,
            "population": self.population,
            "settlement_type": self.settlement_type.value,
            "economy_type": self.economy_type,
            "defenses": round(self.defenses, 3),
            "trade_routes": self.trade_routes,
            "faction_control": self.faction_control,
        }


@dataclass
class LandmarkFeature:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    feature_type: LandmarkFeatureType = LandmarkFeatureType.NATURAL_WONDER
    region_id: str = ""
    coordinates: Tuple[float, float] = (0.0, 0.0)
    discovery_status: str = "undiscovered"
    lore_description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "feature_type": self.feature_type.value,
            "region_id": self.region_id,
            "coordinates": list(self.coordinates),
            "discovery_status": self.discovery_status,
            "lore_description": self.lore_description,
        }


@dataclass
class TradeRoute:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    target_id: str = ""
    distance: float = 0.0
    hazard_level: float = 0.0
    goods_flow: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "distance": round(self.distance, 2),
            "hazard_level": round(self.hazard_level, 2),
            "goods_flow": self.goods_flow,
        }


@dataclass
class WorldMap:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    seed: int = 42
    width: int = 1000
    height: int = 1000
    regions: List[str] = field(default_factory=list)
    biomes: List[str] = field(default_factory=list)
    settlements: List[str] = field(default_factory=list)
    adjacency_graph: Dict[str, List[str]] = field(default_factory=dict)
    total_area: float = 1000000.0
    climate_zones: List[str] = field(default_factory=list)
    population_centers: List[str] = field(default_factory=list)
    trade_routes: List[str] = field(default_factory=list)
    landmarks: List[str] = field(default_factory=list)
    lore: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "seed": self.seed,
            "width": self.width,
            "height": self.height,
            "region_count": len(self.regions),
            "regions": self.regions,
            "biome_count": len(self.biomes),
            "biomes": self.biomes,
            "settlement_count": len(self.settlements),
            "settlements": self.settlements,
            "adjacency_graph": self.adjacency_graph,
            "total_area": self.total_area,
            "climate_zones": self.climate_zones,
            "population_centers": self.population_centers,
            "trade_routes": self.trade_routes,
            "landmark_count": len(self.landmarks),
            "landmarks": self.landmarks,
            "lore": self.lore,
        }


class AgentWorldBuilder:
    """AI-driven world building system for terrain, biome, and environmental design.

    Generates complete worlds with coherent region definitions, climate
    distribution, biome profiles, settlement networks, trade routes,
    landmark placement, and world lore.
    """

    _instance: Optional["AgentWorldBuilder"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_REGIONS_PER_WORLD: int = 64
    MAX_BIOMES_PER_REGION: int = 8
    MAX_SETTLEMENTS_PER_WORLD: int = 200
    MAX_TRADE_ROUTES_PER_WORLD: int = 500
    MAX_LANDMARKS_PER_WORLD: int = 50
    DEFAULT_WORLD_SIZE: int = 1000

    WORLD_PRESETS: Dict[str, Dict[str, Any]] = {
        "fantasy_kingdom": {
            "description": "Classic medieval fantasy realm with diverse biomes",
            "terrain_distribution": {
                TerrainType.PLAINS: 0.30,
                TerrainType.MOUNTAINS: 0.15,
                TerrainType.HILLS: 0.15,
                TerrainType.VALLEY: 0.10,
                TerrainType.PLATEAU: 0.05,
                TerrainType.CANYON: 0.05,
                TerrainType.MARSH: 0.05,
                TerrainType.DESERT: 0.05,
                TerrainType.TUNDRA: 0.05,
                TerrainType.VOLCANIC: 0.05,
            },
            "climate_distribution": {
                ClimateZone.TEMPERATE: 0.35,
                ClimateZone.SUBTROPICAL: 0.15,
                ClimateZone.BOREAL: 0.15,
                ClimateZone.MEDITERRANEAN: 0.15,
                ClimateZone.ARID: 0.10,
                ClimateZone.TROPICAL: 0.05,
                ClimateZone.POLAR: 0.05,
            },
        },
        "desert_wasteland": {
            "description": "Harsh desert-dominated world with scattered oases",
            "terrain_distribution": {
                TerrainType.DESERT: 0.45,
                TerrainType.CANYON: 0.20,
                TerrainType.PLATEAU: 0.15,
                TerrainType.MOUNTAINS: 0.10,
                TerrainType.PLAINS: 0.05,
                TerrainType.VOLCANIC: 0.05,
            },
            "climate_distribution": {
                ClimateZone.ARID: 0.60,
                ClimateZone.SUBTROPICAL: 0.20,
                ClimateZone.MEDITERRANEAN: 0.15,
                ClimateZone.TEMPERATE: 0.05,
            },
        },
        "frozen_north": {
            "description": "Frigid northern realm of tundra, boreal forests, and glaciers",
            "terrain_distribution": {
                TerrainType.TUNDRA: 0.40,
                TerrainType.MOUNTAINS: 0.20,
                TerrainType.HILLS: 0.15,
                TerrainType.PLAINS: 0.10,
                TerrainType.VALLEY: 0.10,
                TerrainType.VOLCANIC: 0.05,
            },
            "climate_distribution": {
                ClimateZone.POLAR: 0.40,
                ClimateZone.BOREAL: 0.35,
                ClimateZone.TEMPERATE: 0.20,
                ClimateZone.ARID: 0.05,
            },
        },
        "lush_tropics": {
            "description": "Vibrant tropical world with dense jungles and archipelagos",
            "terrain_distribution": {
                TerrainType.PLAINS: 0.20,
                TerrainType.HILLS: 0.15,
                TerrainType.VALLEY: 0.15,
                TerrainType.MARSH: 0.15,
                TerrainType.PLATEAU: 0.10,
                TerrainType.MOUNTAINS: 0.10,
                TerrainType.VOLCANIC: 0.10,
                TerrainType.CANYON: 0.05,
            },
            "climate_distribution": {
                ClimateZone.TROPICAL: 0.55,
                ClimateZone.SUBTROPICAL: 0.30,
                ClimateZone.TEMPERATE: 0.10,
                ClimateZone.MEDITERRANEAN: 0.05,
            },
        },
    }

    def __new__(cls) -> "AgentWorldBuilder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentWorldBuilder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        _time_module.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._worlds: Dict[str, WorldMap] = {}
            self._regions: Dict[str, WorldRegion] = {}
            self._biomes: Dict[str, BiomeProfile] = {}
            self._settlements: Dict[str, SettlementNode] = {}
            self._landmarks: Dict[str, LandmarkFeature] = {}
            self._trade_routes: Dict[str, TradeRoute] = {}
            self._region_lookup: Dict[str, str] = {}
            self._total_worlds_generated: int = 0
            self._total_regions_defined: int = 0
            self._total_settlements_placed: int = 0
            self._initialized = True

    def generate_world_map(
        self,
        name: str = "Untitled World",
        width: int = 1000,
        height: int = 1000,
        seed: int = 42,
        preset: Optional[str] = None,
    ) -> WorldMap:
        _time_module.sleep(0.001)
        rng = random.Random(seed)
        world_id = uuid.uuid4().hex

        if preset is not None and preset in self.WORLD_PRESETS:
            preset_config = self.WORLD_PRESETS[preset]
            terrain_dist = preset_config.get("terrain_distribution", {})
            climate_dist = preset_config.get("climate_distribution", {})
        else:
            terrain_dist = self.WORLD_PRESETS["fantasy_kingdom"]["terrain_distribution"]
            climate_dist = self.WORLD_PRESETS["fantasy_kingdom"]["climate_distribution"]

        total_area = float(width * height)
        region_count = rng.randint(6, min(self.MAX_REGIONS_PER_WORLD, 24))
        region_ids: List[str] = []
        region_objects: List[WorldRegion] = []

        for _ in range(region_count):
            terrain = self._weighted_choice(rng, terrain_dist)
            climate = self._weighted_choice(rng, climate_dist)

            base_elev = TERRAIN_TEMPLATES[terrain]["base_elevation"]
            elevation = rng.randint(base_elev[0], base_elev[1])
            fert_min, fert_max = TERRAIN_TEMPLATES[terrain]["fertility_range"]
            fertility = rng.uniform(fert_min, fert_max)
            resources = list(TERRAIN_TEMPLATES[terrain]["resource_types"])

            size_km2 = (total_area / region_count) * rng.uniform(0.5, 1.5)
            size_km2 = round(size_km2, 2)

            region_name = (
                rng.choice(REGION_NAME_PREFIXES)
                + " "
                + rng.choice(REGION_NAME_SUFFIXES)
            )
            while any(r.name == region_name for r in region_objects):
                region_name = (
                    rng.choice(REGION_NAME_PREFIXES)
                    + " "
                    + rng.choice(REGION_NAME_SUFFIXES)
                )

            pop_density = self._derive_population_density(fertility, terrain)

            region = WorldRegion(
                id=uuid.uuid4().hex,
                name=region_name,
                terrain_type=terrain,
                climate=climate,
                size_km2=size_km2,
                elevation=float(elevation),
                fertility=fertility,
                resources=resources,
                population_density=pop_density,
                biome_signature="",
            )
            region_ids.append(region.id)
            region_objects.append(region)
            self._regions[region.id] = region
            self._region_lookup[region.id] = world_id
            self._total_regions_defined += 1

        adjacency = self._build_adjacency_graph(rng, region_ids, region_objects)

        world = WorldMap(
            id=world_id,
            name=name,
            seed=seed,
            width=width,
            height=height,
            regions=region_ids,
            biomes=[],
            settlements=[],
            adjacency_graph=adjacency,
            total_area=total_area,
            climate_zones=[],
            population_centers=[],
            trade_routes=[],
            landmarks=[],
        )
        self._worlds[world_id] = world

        self.compute_climate_distribution(region_objects)
        for region in region_objects:
            self.generate_biomes_for_region(region.id)

        world.climate_zones = [
            self._regions[rid].climate.value
            for rid in region_ids
            if rid in self._regions
        ]
        world.biomes = [
            b.id
            for b in self._biomes.values()
            if any(
                b.id in self._regions[rid].biome_signature.split(",")
                for rid in region_ids
                if rid in self._regions
            )
        ]
        self._total_worlds_generated += 1
        return world

    def define_region(
        self, name: str, terrain: TerrainType, climate: ClimateZone, size: float
    ) -> WorldRegion:
        _time_module.sleep(0.001)
        template = TERRAIN_TEMPLATES.get(terrain, TERRAIN_TEMPLATES[TerrainType.PLAINS])
        base_elev = template["base_elevation"]
        fert_min, fert_max = template["fertility_range"]

        elevation = float(random.randint(base_elev[0], base_elev[1]))
        fertility = random.uniform(fert_min, fert_max)
        resources = list(template["resource_types"])
        pop_density = self._derive_population_density(fertility, terrain)

        region = WorldRegion(
            id=uuid.uuid4().hex,
            name=name,
            terrain_type=terrain,
            climate=climate,
            size_km2=size,
            elevation=elevation,
            fertility=fertility,
            resources=resources,
            population_density=pop_density,
        )
        self._regions[region.id] = region
        self._total_regions_defined += 1
        return region

    def compute_climate_distribution(
        self, regions: List[WorldRegion]
    ) -> Dict[str, ClimateZone]:
        _time_module.sleep(0.001)
        result: Dict[str, ClimateZone] = {}
        rng = random.Random()

        for region in regions:
            if not region.climate:
                elevation_factor = region.elevation / 5000.0
                if elevation_factor > 0.6:
                    region.climate = ClimateZone.BOREAL
                elif elevation_factor > 0.3:
                    region.climate = ClimateZone.TEMPERATE
                else:
                    region.climate = rng.choice(list(ClimateZone))
            result[region.id] = region.climate
        return result

    def generate_biomes_for_region(self, region_id: str) -> List[BiomeProfile]:
        _time_module.sleep(0.001)
        region = self._regions.get(region_id)
        if region is None:
            return []

        climate_profile = CLIMATE_PROFILES.get(
            region.climate, CLIMATE_PROFILES[ClimateZone.TEMPERATE]
        )
        rng = random.Random()
        biome_count = rng.randint(1, self.MAX_BIOMES_PER_REGION)
        biomes: List[BiomeProfile] = []
        biome_ids: List[str] = []

        for _ in range(biome_count):
            temp_low, temp_high = climate_profile["temperature_range"]
            adjusted_temp = (
                temp_low + rng.uniform(0, 5),
                temp_high - rng.uniform(0, 5),
            )

            precip_low, precip_high = climate_profile["precipitation_range"]
            adjusted_precip = (
                int(precip_low * rng.uniform(0.7, 1.0)),
                int(precip_high * rng.uniform(0.7, 1.3)),
            )

            flora = list(climate_profile.get("flora_types", []))
            fauna = list(climate_profile.get("fauna_types", []))
            soil = rng.choice(climate_profile.get("soil_types", ["loam"]))
            threat = climate_profile.get("threat_base", 0.3) * rng.uniform(0.5, 1.5)
            threat = min(threat, 1.0)

            richness = region.fertility * rng.uniform(0.6, 1.4)
            richness = min(richness, 1.0)

            biome_name = (
                rng.choice(BIOME_NAME_PREFIXES)
                + " "
                + rng.choice(BIOME_NAME_SUFFIXES)
            )
            while any(b.name == biome_name for b in biomes):
                biome_name = (
                    rng.choice(BIOME_NAME_PREFIXES)
                    + " "
                    + rng.choice(BIOME_NAME_SUFFIXES)
                )

            rng.shuffle(flora)
            rng.shuffle(fauna)

            biome = BiomeProfile(
                id=uuid.uuid4().hex,
                name=biome_name,
                temperature_range=adjusted_temp,
                precipitation_range=adjusted_precip,
                flora_species=flora[: rng.randint(2, min(6, len(flora)))],
                fauna_species=fauna[: rng.randint(2, min(6, len(fauna)))],
                soil_type=soil,
                threat_level=round(threat, 3),
                resource_richness=round(richness, 3),
            )
            biomes.append(biome)
            biome_ids.append(biome.id)
            self._biomes[biome.id] = biome

        region.biome_signature = ",".join(biome_ids)
        return biomes

    def place_settlements(
        self, world_id: str, density: PopulationDensity = PopulationDensity.RURAL
    ) -> List[SettlementNode]:
        _time_module.sleep(0.001)
        world = self._worlds.get(world_id)
        if world is None:
            return []

        rng = random.Random(world.seed)
        settlements: List[SettlementNode] = []

        density_multipliers = {
            PopulationDensity.SPARSE: 0.3,
            PopulationDensity.RURAL: 0.6,
            PopulationDensity.SUBURBAN: 1.0,
            PopulationDensity.URBAN: 2.0,
            PopulationDensity.METROPOLITAN: 4.0,
        }
        multiplier = density_multipliers.get(density, 0.6)

        for region_id in world.regions:
            region = self._regions.get(region_id)
            if region is None:
                continue

            base_count = max(1, int(region.size_km2 / 200 * multiplier))
            count = min(base_count, 10)

            faction = rng.choice(FACTION_POOL)

            for _ in range(count):
                pop_density = region.population_density
                settlement_type = self._derive_settlement_type(
                    rng, region.size_km2, pop_density
                )
                template = SETTLEMENT_TYPE_TEMPLATES.get(
                    settlement_type,
                    SETTLEMENT_TYPE_TEMPLATES[SettlementType.VILLAGE],
                )
                population = rng.randint(
                    template["min_population"], template["max_population"]
                )
                economy = rng.choice(template["economy_types"])
                defense = template["defense_rating"] * rng.uniform(0.7, 1.3)

                name = self._generate_settlement_name(rng, settlements)

                settlement = SettlementNode(
                    id=uuid.uuid4().hex,
                    name=name,
                    region_id=region_id,
                    population=population,
                    settlement_type=settlement_type,
                    economy_type=economy,
                    defenses=min(defense, 1.0),
                    trade_routes=[],
                    faction_control=faction,
                )
                settlements.append(settlement)
                self._settlements[settlement.id] = settlement
                self._total_settlements_placed += 1

        world.settlements = [s.id for s in settlements]
        world.population_centers = [
            s.id
            for s in settlements
            if s.settlement_type
            in (SettlementType.CITY, SettlementType.CAPITAL)
        ]
        return settlements

    def generate_trade_routes(self, world_id: str) -> List[TradeRoute]:
        _time_module.sleep(0.001)
        world = self._worlds.get(world_id)
        if world is None:
            return []

        rng = random.Random(world.seed)
        routes: List[TradeRoute] = []
        settlement_ids = list(world.settlements)

        if len(settlement_ids) < 2:
            return []

        trade_graph: Dict[str, List[str]] = {}

        for i in range(len(settlement_ids)):
            for j in range(i + 1, len(settlement_ids)):
                sid_a = settlement_ids[i]
                sid_b = settlement_ids[j]
                settlement_a = self._settlements.get(sid_a)
                settlement_b = self._settlements.get(sid_b)
                if settlement_a is None or settlement_b is None:
                    continue

                region_a = self._regions.get(settlement_a.region_id)
                region_b = self._regions.get(settlement_b.region_id)
                if region_a is None or region_b is None:
                    continue

                distance = (
                    abs(region_a.elevation - region_b.elevation) * 0.1
                    + rng.uniform(10, 100)
                )

                hazard = (
                    rng.uniform(0.0, 0.3)
                    + TERRAIN_TEMPLATES.get(
                        region_a.terrain_type,
                        TERRAIN_TEMPLATES[TerrainType.PLAINS],
                    )["travel_modifier"]
                    * 0.1
                    + TERRAIN_TEMPLATES.get(
                        region_b.terrain_type,
                        TERRAIN_TEMPLATES[TerrainType.PLAINS],
                    )["travel_modifier"]
                    * 0.1
                )
                hazard = min(hazard, 1.0)

                goods = self._derive_trade_goods(region_a, region_b, rng)

                route = TradeRoute(
                    id=uuid.uuid4().hex,
                    source_id=sid_a,
                    target_id=sid_b,
                    distance=round(distance, 2),
                    hazard_level=round(hazard, 2),
                    goods_flow=goods,
                )
                routes.append(route)
                self._trade_routes[route.id] = route

                trade_graph.setdefault(sid_a, []).append(sid_b)
                trade_graph.setdefault(sid_b, []).append(sid_a)

                settlement_a.trade_routes.append(route.id)
                settlement_b.trade_routes.append(route.id)

                if len(routes) >= self.MAX_TRADE_ROUTES_PER_WORLD:
                    break
            if len(routes) >= self.MAX_TRADE_ROUTES_PER_WORLD:
                break

        world.trade_routes = [r.id for r in routes]
        return routes

    def calculate_region_fertility(self, region: WorldRegion) -> float:
        _time_module.sleep(0.001)
        template = TERRAIN_TEMPLATES.get(
            region.terrain_type, TERRAIN_TEMPLATES[TerrainType.PLAINS]
        )
        base_fertility_min, base_fertility_max = template["fertility_range"]

        climate = CLIMATE_PROFILES.get(region.climate, CLIMATE_PROFILES[ClimateZone.TEMPERATE])
        precip_min, precip_max = climate["precipitation_range"]
        temp_min, temp_max = climate["temperature_range"]

        precipitation_score = min(precip_max / 4000.0, 1.0) if precip_max > 0 else 0.1
        temperature_score = (
            max(0.0, min(1.0, (temp_max - 5.0) / 30.0)) if temp_max > 5 else 0.05
        )

        elevation_penalty = max(0.0, 1.0 - (region.elevation / 4000.0))

        computed = (
            base_fertility_max * 0.4
            + precipitation_score * 0.25
            + temperature_score * 0.20
            + elevation_penalty * 0.15
        )
        computed = max(base_fertility_min, min(base_fertility_max, computed))
        region.fertility = round(computed, 3)
        return region.fertility

    def place_landmarks(
        self, world_id: str, count: int
    ) -> List[LandmarkFeature]:
        _time_module.sleep(0.001)
        world = self._worlds.get(world_id)
        if world is None:
            return []

        rng = random.Random(world.seed)
        placed = min(count, self.MAX_LANDMARKS_PER_WORLD)
        landmarks: List[LandmarkFeature] = []
        region_ids = world.regions

        feature_types = list(LandmarkFeatureType)
        lore_templates = [
            "An ancient structure left by a forgotten civilization, its purpose shrouded in mystery.",
            "A natural formation said to hold immense magical energy, attracting scholars and adventurers alike.",
            "The site of a legendary battle where the earth itself was scarred by forces beyond comprehension.",
            "A sacred grove where the veil between worlds grows thin during certain celestial alignments.",
            "Remnants of a colossal beast, its bones now serving as a landmark for travelers crossing the region.",
            "A towering monument erected by the first settlers, marking the founding of civilization in this land.",
            "An underground labyrinth rumored to contain treasures guarded by ancient automatons.",
            "A crystalline cavern whose walls glow with an ethereal light, never touched by the sun.",
            "The petrified remains of an elder forest, its trees now standing as silent stone sentinels.",
        ]

        for _ in range(placed):
            region_id = rng.choice(region_ids)
            feature_type = rng.choice(feature_types)

            prefix = rng.choice(LANDMARK_NAME_PREFIXES)
            suffix = rng.choice(LANDMARK_NAME_SUFFIXES)
            name = f"The {prefix} {suffix}"
            while any(l.name == name for l in landmarks):
                prefix = rng.choice(LANDMARK_NAME_PREFIXES)
                suffix = rng.choice(LANDMARK_NAME_SUFFIXES)
                name = f"The {prefix} {suffix}"

            coordinates = (
                round(rng.uniform(0, world.width), 2),
                round(rng.uniform(0, world.height), 2),
            )

            lore = rng.choice(lore_templates)

            landmark = LandmarkFeature(
                id=uuid.uuid4().hex,
                name=name,
                feature_type=feature_type,
                region_id=region_id,
                coordinates=coordinates,
                discovery_status="undiscovered",
                lore_description=lore,
            )
            landmarks.append(landmark)
            self._landmarks[landmark.id] = landmark

            region = self._regions.get(region_id)
            if region is not None:
                region.landmarks.append(landmark.id)

        world.landmarks = [l.id for l in landmarks]
        return landmarks

    def generate_world_lore(self, world_id: str) -> str:
        _time_module.sleep(0.001)
        world = self._worlds.get(world_id)
        if world is None:
            return ""

        rng = random.Random(world.seed)
        region_count = len(world.regions)
        settlement_count = len(world.settlements)
        landmark_count = len(world.landmarks)

        age_eras = [
            "Dawn Era",
            "Age of Foundations",
            "Era of Strife",
            "Golden Age",
            "Age of Discovery",
            "Era of Discord",
            "Age of Renewal",
            "Silver Century",
        ]
        era = rng.choice(age_eras)

        faction = rng.choice(FACTION_POOL)
        region_name = "unknown lands"
        if world.regions:
            first_region = self._regions.get(world.regions[0])
            if first_region is not None:
                region_name = first_region.name

        lore_lines: List[str] = [
            f"In the {era}, the world of {world.name} spans {region_count} regions "
            f"across {world.width}x{world.height} kilometers of varied terrain.",
            "",
            f"The {faction} rose to prominence from the {region_name}, "
            f"establishing dominion through diplomacy and conquest.",
            f"With {settlement_count} settlements scattered across the realm, "
            f"trade flourishes along carefully guarded routes.",
            "",
            f"Legends speak of {landmark_count} landmarks hidden throughout the world, "
            f"each holding secrets of the ancient past.",
            f"Scholars debate the origins of these sites, but adventurers "
            f"continue to seek their treasures regardless of the dangers.",
            "",
            f"The climate ranges from frozen polar wastes to scorching desert expanses, "
            f"with temperate heartlands serving as the cradle of civilization.",
            f"Each region's unique biome supports distinct flora and fauna, "
            f"shaping the cultures that have grown within them.",
        ]

        # Add region-specific lore snippets
        for region_id in world.regions[:3]:
            region = self._regions.get(region_id)
            if region is None:
                continue
            region_faction = rng.choice(FACTION_POOL)
            lore_lines.append("")
            lore_lines.append(
                f"The {region.name} is a {region.terrain_type.value} region "
                f"under the influence of the {region_faction}. "
                f"Its {region.climate.value} climate and "
                f"{'fertile' if region.fertility > 0.5 else 'harsh'} lands "
                f"support a {region.population_density.value} population."
            )

        world.lore = "\n".join(lore_lines)
        return world.lore

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        total_regions = len(self._regions)
        total_biomes = len(self._biomes)
        total_settlements = len(self._settlements)
        total_landmarks = len(self._landmarks)
        total_trade_routes = len(self._trade_routes)
        total_worlds = len(self._worlds)

        terrain_counts: Dict[str, int] = {}
        climate_counts: Dict[str, int] = {}
        for region in self._regions.values():
            t_key = region.terrain_type.value
            terrain_counts[t_key] = terrain_counts.get(t_key, 0) + 1
            c_key = region.climate.value
            climate_counts[c_key] = climate_counts.get(c_key, 0) + 1

        avg_fertility = 0.0
        if total_regions > 0:
            avg_fertility = round(
                sum(r.fertility for r in self._regions.values()) / total_regions, 3
            )

        total_population = sum(s.population for s in self._settlements.values())

        return {
            "total_worlds": total_worlds,
            "total_regions": total_regions,
            "total_biomes": total_biomes,
            "total_settlements": total_settlements,
            "total_landmarks": total_landmarks,
            "total_trade_routes": total_trade_routes,
            "total_population": total_population,
            "average_fertility": avg_fertility,
            "terrain_distribution": terrain_counts,
            "climate_distribution": climate_counts,
            "worlds_generated_lifetime": self._total_worlds_generated,
            "regions_defined_lifetime": self._total_regions_defined,
            "settlements_placed_lifetime": self._total_settlements_placed,
        }

    def _weighted_choice(
        self, rng: random.Random, distribution: Dict[Any, float]
    ) -> Any:
        _time_module.sleep(0.001)
        items = list(distribution.items())
        if not items:
            return TerrainType.PLAINS
        total = sum(weight for _, weight in items)
        if total <= 0:
            return items[0][0]
        roll = rng.uniform(0, total)
        cumulative = 0.0
        for key, weight in items:
            cumulative += weight
            if roll <= cumulative:
                return key
        return items[-1][0]

    def _derive_population_density(
        self, fertility: float, terrain: TerrainType
    ) -> PopulationDensity:
        _time_module.sleep(0.001)
        if terrain in (TerrainType.DESERT, TerrainType.TUNDRA, TerrainType.VOLCANIC):
            if fertility > 0.35:
                return PopulationDensity.RURAL
            return PopulationDensity.SPARSE

        if fertility > 0.75:
            return PopulationDensity.URBAN
        elif fertility > 0.50:
            return PopulationDensity.SUBURBAN
        elif fertility > 0.25:
            return PopulationDensity.RURAL
        return PopulationDensity.SPARSE

    def _derive_settlement_type(
        self,
        rng: random.Random,
        region_size: float,
        density: PopulationDensity,
    ) -> SettlementType:
        _time_module.sleep(0.001)
        if density == PopulationDensity.METROPOLITAN:
            return rng.choice(
                [SettlementType.CITY, SettlementType.CAPITAL, SettlementType.CITY]
            )
        if density == PopulationDensity.URBAN:
            return rng.choice(
                [
                    SettlementType.TOWN,
                    SettlementType.CITY,
                    SettlementType.CAPITAL,
                    SettlementType.TOWN,
                ]
            )
        if density == PopulationDensity.SUBURBAN:
            return rng.choice(
                [
                    SettlementType.VILLAGE,
                    SettlementType.TOWN,
                    SettlementType.CITY,
                    SettlementType.VILLAGE,
                    SettlementType.TOWN,
                ]
            )
        if density == PopulationDensity.RURAL:
            if region_size > 800 and rng.random() < 0.15:
                return SettlementType.FORTRESS
            return rng.choice(
                [
                    SettlementType.VILLAGE,
                    SettlementType.VILLAGE,
                    SettlementType.TOWN,
                    SettlementType.FORTRESS,
                ]
            )
        return rng.choice(
            [
                SettlementType.VILLAGE,
                SettlementType.VILLAGE,
                SettlementType.FORTRESS,
            ]
        )

    def _build_adjacency_graph(
        self,
        rng: random.Random,
        region_ids: List[str],
        regions: List[WorldRegion],
    ) -> Dict[str, List[str]]:
        _time_module.sleep(0.001)
        graph: Dict[str, List[str]] = {rid: [] for rid in region_ids}
        if len(region_ids) < 2:
            return graph

        remaining = list(region_ids)
        rng.shuffle(remaining)
        connected: List[str] = [remaining.pop()]

        while remaining:
            best_src: Optional[str] = None
            best_tgt: Optional[str] = None
            best_dist = float("inf")

            for src in connected:
                src_region = self._regions.get(src)
                if src_region is None:
                    continue
                for tgt in remaining:
                    tgt_region = self._regions.get(tgt)
                    if tgt_region is None:
                        continue
                    dist = abs(src_region.elevation - tgt_region.elevation)
                    if dist < best_dist:
                        best_dist = dist
                        best_src = src
                        best_tgt = tgt

            if best_src is not None and best_tgt is not None:
                graph[best_src].append(best_tgt)
                graph[best_tgt].append(best_src)
                connected.append(best_tgt)
                remaining.remove(best_tgt)
            else:
                break

        for rid in region_ids:
            if len(graph[rid]) < 2:
                candidates = [r for r in region_ids if r != rid and r not in graph[rid]]
                for _ in range(min(2 - len(graph[rid]), len(candidates))):
                    if not candidates:
                        break
                    neighbor = rng.choice(candidates)
                    graph[rid].append(neighbor)
                    graph[neighbor].append(rid)
                    candidates.remove(neighbor)

        return graph

    def _generate_settlement_name(
        self,
        rng: random.Random,
        existing: List[SettlementNode],
    ) -> str:
        _time_module.sleep(0.001)
        name = (
            rng.choice(SETTLEMENT_NAME_PREFIXES)
            + rng.choice(SETTLEMENT_NAME_SUFFIXES)
        )
        while any(s.name == name for s in existing):
            name = (
                rng.choice(SETTLEMENT_NAME_PREFIXES)
                + rng.choice(SETTLEMENT_NAME_SUFFIXES)
            )
        return name

    def _derive_trade_goods(
        self,
        region_a: WorldRegion,
        region_b: WorldRegion,
        rng: random.Random,
    ) -> List[str]:
        _time_module.sleep(0.001)
        goods: List[str] = []
        a_resources = set(region_a.resources)
        b_resources = set(region_b.resources)

        a_exclusive = a_resources - b_resources
        b_exclusive = b_resources - a_resources

        if a_exclusive:
            goods.append(f"{rng.choice(list(a_exclusive))}_export")
        if b_exclusive:
            goods.append(f"{rng.choice(list(b_exclusive))}_import")

        mutual = a_resources & b_resources
        if mutual:
            goods.append(f"{rng.choice(list(mutual))}_mutual_trade")
        if not goods:
            goods.append("basic_supplies")
        return goods


def get_agent_world_builder() -> AgentWorldBuilder:
    return AgentWorldBuilder.get_instance()