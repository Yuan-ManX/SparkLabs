"""
SparkLabs Agent - World Builder

AI-driven world building system for the AI-native game engine.
Generates game worlds with biomes, terrain, points of interest,
population distribution, and environmental storytelling.

The WorldBuilderEngine creates diverse, interconnected worlds
with logical biome placement, appropriate terrain features,
population distribution based on habitability, and danger level
progression across regions.

Architecture:
  WorldBuilderEngine (Singleton)
    |-- BiomeType (16 distinct biome categories)
    |-- TerrainFeature (15 terrain feature types)
    |-- PointOfInterestType (16 POI categories)
    |-- WorldRegion (individual region data model)
    |-- PointOfInterest (location data model)
    |-- WorldMap (complete world data model)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class BiomeType(Enum):
    """Distinct biome categories for world regions."""

    FOREST = "forest"
    DESERT = "desert"
    TUNDRA = "tundra"
    SWAMP = "swamp"
    MOUNTAIN = "mountain"
    VOLCANIC = "volcanic"
    OCEAN = "ocean"
    PLAINS = "plains"
    JUNGLE = "jungle"
    TAIGA = "taiga"
    SAVANNA = "savanna"
    CAVE = "cave"
    URBAN = "urban"
    RUINS = "ruins"
    CORRUPTED = "corrupted"
    CELESTIAL = "celestial"


class TerrainFeature(Enum):
    """Natural terrain features that can appear within regions."""

    RIVER = "river"
    LAKE = "lake"
    WATERFALL = "waterfall"
    CLIFF = "cliff"
    CANYON = "canyon"
    VALLEY = "valley"
    PLATEAU = "plateau"
    HILL = "hill"
    DUNE = "dune"
    GLACIER = "glacier"
    HOT_SPRING = "hot_spring"
    GEYSER = "geyser"
    CRATER = "crater"
    ARCH = "arch"
    PILLAR = "pillar"


class PointOfInterestType(Enum):
    """Categories of points of interest placed within regions."""

    VILLAGE = "village"
    TOWN = "town"
    CITY = "city"
    DUNGEON = "dungeon"
    TEMPLE = "temple"
    RUINS = "ruins"
    TOWER = "tower"
    CAMP = "camp"
    OASIS = "oasis"
    PORTAL = "portal"
    SHRINE = "shrine"
    BRIDGE = "bridge"
    GRAVEYARD = "graveyard"
    MINE = "mine"
    LIGHTHOUSE = "lighthouse"
    OUTPOST = "outpost"


# ------------------------------------------------------------------
# Lookup Tables
# ------------------------------------------------------------------


# Adjacency rules: which biomes can naturally border each other.
# Each biome maps to a list of compatible neighboring biomes.
BIOME_ADJACENCY_RULES: Dict[BiomeType, List[BiomeType]] = {
    BiomeType.FOREST: [
        BiomeType.FOREST, BiomeType.PLAINS, BiomeType.MOUNTAIN,
        BiomeType.SWAMP, BiomeType.JUNGLE, BiomeType.TAIGA,
        BiomeType.RUINS, BiomeType.RIVER if hasattr(BiomeType, "RIVER") else BiomeType.PLAINS,
    ],
    BiomeType.DESERT: [
        BiomeType.DESERT, BiomeType.PLAINS, BiomeType.MOUNTAIN,
        BiomeType.SAVANNA, BiomeType.RUINS, BiomeType.VOLCANIC,
    ],
    BiomeType.TUNDRA: [
        BiomeType.TUNDRA, BiomeType.TAIGA, BiomeType.MOUNTAIN,
        BiomeType.PLAINS, BiomeType.GLACIER if hasattr(BiomeType, "GLACIER") else BiomeType.TUNDRA,
    ],
    BiomeType.SWAMP: [
        BiomeType.SWAMP, BiomeType.FOREST, BiomeType.PLAINS,
        BiomeType.JUNGLE, BiomeType.RUINS,
    ],
    BiomeType.MOUNTAIN: [
        BiomeType.MOUNTAIN, BiomeType.FOREST, BiomeType.TUNDRA,
        BiomeType.DESERT, BiomeType.VOLCANIC, BiomeType.CAVE,
        BiomeType.TAIGA, BiomeType.PLAINS,
    ],
    BiomeType.VOLCANIC: [
        BiomeType.VOLCANIC, BiomeType.MOUNTAIN, BiomeType.DESERT,
        BiomeType.CORRUPTED, BiomeType.CAVE,
    ],
    BiomeType.OCEAN: [
        BiomeType.OCEAN, BiomeType.PLAINS, BiomeType.DESERT,
        BiomeType.SWAMP, BiomeType.TUNDRA, BiomeType.FOREST,
    ],
    BiomeType.PLAINS: [
        BiomeType.PLAINS, BiomeType.FOREST, BiomeType.DESERT,
        BiomeType.MOUNTAIN, BiomeType.SWAMP, BiomeType.SAVANNA,
        BiomeType.TUNDRA, BiomeType.URBAN, BiomeType.RUINS,
        BiomeType.OCEAN,
    ],
    BiomeType.JUNGLE: [
        BiomeType.JUNGLE, BiomeType.FOREST, BiomeType.SWAMP,
        BiomeType.PLAINS, BiomeType.RUINS, BiomeType.MOUNTAIN,
    ],
    BiomeType.TAIGA: [
        BiomeType.TAIGA, BiomeType.FOREST, BiomeType.TUNDRA,
        BiomeType.MOUNTAIN, BiomeType.PLAINS,
    ],
    BiomeType.SAVANNA: [
        BiomeType.SAVANNA, BiomeType.PLAINS, BiomeType.DESERT,
        BiomeType.MOUNTAIN, BiomeType.FOREST,
    ],
    BiomeType.CAVE: [
        BiomeType.CAVE, BiomeType.MOUNTAIN, BiomeType.VOLCANIC,
        BiomeType.RUINS, BiomeType.CORRUPTED,
    ],
    BiomeType.URBAN: [
        BiomeType.URBAN, BiomeType.PLAINS, BiomeType.FOREST,
        BiomeType.RUINS, BiomeType.OCEAN,
    ],
    BiomeType.RUINS: [
        BiomeType.RUINS, BiomeType.DESERT, BiomeType.PLAINS,
        BiomeType.FOREST, BiomeType.SWAMP, BiomeType.URBAN,
        BiomeType.CORRUPTED, BiomeType.CAVE, BiomeType.JUNGLE,
    ],
    BiomeType.CORRUPTED: [
        BiomeType.CORRUPTED, BiomeType.RUINS, BiomeType.VOLCANIC,
        BiomeType.CAVE, BiomeType.SWAMP, BiomeType.DESERT,
    ],
    BiomeType.CELESTIAL: [
        BiomeType.CELESTIAL, BiomeType.MOUNTAIN, BiomeType.PLAINS,
        BiomeType.CAVE, BiomeType.RUINS,
    ],
}


# Terrain features that naturally occur in each biome.
BIOME_TERRAIN_FEATURES: Dict[BiomeType, List[TerrainFeature]] = {
    BiomeType.FOREST: [
        TerrainFeature.RIVER, TerrainFeature.LAKE, TerrainFeature.HILL,
        TerrainFeature.VALLEY, TerrainFeature.WATERFALL, TerrainFeature.CLIFF,
    ],
    BiomeType.DESERT: [
        TerrainFeature.DUNE, TerrainFeature.CANYON, TerrainFeature.PLATEAU,
        TerrainFeature.CRATER, TerrainFeature.ARCH, TerrainFeature.PILLAR,
    ],
    BiomeType.TUNDRA: [
        TerrainFeature.GLACIER, TerrainFeature.PLATEAU, TerrainFeature.LAKE,
        TerrainFeature.HILL, TerrainFeature.CLIFF,
    ],
    BiomeType.SWAMP: [
        TerrainFeature.LAKE, TerrainFeature.RIVER, TerrainFeature.HOT_SPRING,
        TerrainFeature.VALLEY, TerrainFeature.PILLAR,
    ],
    BiomeType.MOUNTAIN: [
        TerrainFeature.CLIFF, TerrainFeature.WATERFALL, TerrainFeature.CANYON,
        TerrainFeature.CRATER, TerrainFeature.ARCH, TerrainFeature.PLATEAU,
        TerrainFeature.GEYSER, TerrainFeature.HOT_SPRING,
    ],
    BiomeType.VOLCANIC: [
        TerrainFeature.GEYSER, TerrainFeature.CRATER, TerrainFeature.CLIFF,
        TerrainFeature.HOT_SPRING, TerrainFeature.PLATEAU,
    ],
    BiomeType.OCEAN: [
        TerrainFeature.CLIFF, TerrainFeature.ARCH, TerrainFeature.PILLAR,
        TerrainFeature.CRATER, TerrainFeature.LAKE,
    ],
    BiomeType.PLAINS: [
        TerrainFeature.RIVER, TerrainFeature.LAKE, TerrainFeature.HILL,
        TerrainFeature.VALLEY, TerrainFeature.PLATEAU,
    ],
    BiomeType.JUNGLE: [
        TerrainFeature.RIVER, TerrainFeature.WATERFALL, TerrainFeature.VALLEY,
        TerrainFeature.LAKE, TerrainFeature.HILL,
    ],
    BiomeType.TAIGA: [
        TerrainFeature.LAKE, TerrainFeature.RIVER, TerrainFeature.HILL,
        TerrainFeature.GLACIER, TerrainFeature.VALLEY,
    ],
    BiomeType.SAVANNA: [
        TerrainFeature.PLATEAU, TerrainFeature.HILL, TerrainFeature.VALLEY,
        TerrainFeature.RIVER, TerrainFeature.ARCH,
    ],
    BiomeType.CAVE: [
        TerrainFeature.LAKE, TerrainFeature.PILLAR, TerrainFeature.CLIFF,
        TerrainFeature.HOT_SPRING, TerrainFeature.CRATER,
    ],
    BiomeType.URBAN: [
        TerrainFeature.RIVER, TerrainFeature.LAKE, TerrainFeature.HILL,
        TerrainFeature.PLATEAU,
    ],
    BiomeType.RUINS: [
        TerrainFeature.CRATER, TerrainFeature.ARCH, TerrainFeature.PILLAR,
        TerrainFeature.CANYON, TerrainFeature.CLIFF,
    ],
    BiomeType.CORRUPTED: [
        TerrainFeature.CRATER, TerrainFeature.GEYSER, TerrainFeature.CLIFF,
        TerrainFeature.HOT_SPRING, TerrainFeature.PILLAR,
    ],
    BiomeType.CELESTIAL: [
        TerrainFeature.ARCH, TerrainFeature.PILLAR, TerrainFeature.PLATEAU,
        TerrainFeature.CRATER, TerrainFeature.WATERFALL,
    ],
}


# Points of interest that can appear in each biome.
BIOME_POI_AFFINITY: Dict[BiomeType, List[PointOfInterestType]] = {
    BiomeType.FOREST: [
        PointOfInterestType.VILLAGE, PointOfInterestType.TEMPLE,
        PointOfInterestType.CAMP, PointOfInterestType.SHRINE,
        PointOfInterestType.OUTPOST, PointOfInterestType.TOWER,
        PointOfInterestType.RUINS,
    ],
    BiomeType.DESERT: [
        PointOfInterestType.OASIS, PointOfInterestType.RUINS,
        PointOfInterestType.CAMP, PointOfInterestType.TEMPLE,
        PointOfInterestType.MINE, PointOfInterestType.GRAVEYARD,
    ],
    BiomeType.TUNDRA: [
        PointOfInterestType.OUTPOST, PointOfInterestType.CAMP,
        PointOfInterestType.RUINS, PointOfInterestType.MINE,
        PointOfInterestType.SHRINE,
    ],
    BiomeType.SWAMP: [
        PointOfInterestType.RUINS, PointOfInterestType.SHRINE,
        PointOfInterestType.CAMP, PointOfInterestType.TEMPLE,
        PointOfInterestType.GRAVEYARD,
    ],
    BiomeType.MOUNTAIN: [
        PointOfInterestType.MINE, PointOfInterestType.TOWER,
        PointOfInterestType.TEMPLE, PointOfInterestType.DUNGEON,
        PointOfInterestType.BRIDGE, PointOfInterestType.OUTPOST,
        PointOfInterestType.SHRINE,
    ],
    BiomeType.VOLCANIC: [
        PointOfInterestType.DUNGEON, PointOfInterestType.MINE,
        PointOfInterestType.PORTAL, PointOfInterestType.TEMPLE,
        PointOfInterestType.RUINS,
    ],
    BiomeType.OCEAN: [
        PointOfInterestType.LIGHTHOUSE, PointOfInterestType.PORTAL,
        PointOfInterestType.OUTPOST, PointOfInterestType.RUINS,
        PointOfInterestType.SHRINE,
    ],
    BiomeType.PLAINS: [
        PointOfInterestType.VILLAGE, PointOfInterestType.TOWN,
        PointOfInterestType.CITY, PointOfInterestType.CAMP,
        PointOfInterestType.BRIDGE, PointOfInterestType.OUTPOST,
        PointOfInterestType.TOWER, PointOfInterestType.GRAVEYARD,
    ],
    BiomeType.JUNGLE: [
        PointOfInterestType.TEMPLE, PointOfInterestType.RUINS,
        PointOfInterestType.CAMP, PointOfInterestType.SHRINE,
        PointOfInterestType.DUNGEON,
    ],
    BiomeType.TAIGA: [
        PointOfInterestType.OUTPOST, PointOfInterestType.CAMP,
        PointOfInterestType.VILLAGE, PointOfInterestType.SHRINE,
        PointOfInterestType.TOWER,
    ],
    BiomeType.SAVANNA: [
        PointOfInterestType.VILLAGE, PointOfInterestType.CAMP,
        PointOfInterestType.OASIS, PointOfInterestType.OUTPOST,
        PointOfInterestType.RUINS,
    ],
    BiomeType.CAVE: [
        PointOfInterestType.DUNGEON, PointOfInterestType.MINE,
        PointOfInterestType.SHRINE, PointOfInterestType.RUINS,
        PointOfInterestType.GRAVEYARD, PointOfInterestType.PORTAL,
    ],
    BiomeType.URBAN: [
        PointOfInterestType.CITY, PointOfInterestType.TOWN,
        PointOfInterestType.TEMPLE, PointOfInterestType.BRIDGE,
        PointOfInterestType.TOWER, PointOfInterestType.GRAVEYARD,
    ],
    BiomeType.RUINS: [
        PointOfInterestType.RUINS, PointOfInterestType.DUNGEON,
        PointOfInterestType.TEMPLE, PointOfInterestType.GRAVEYARD,
        PointOfInterestType.PORTAL, PointOfInterestType.SHRINE,
    ],
    BiomeType.CORRUPTED: [
        PointOfInterestType.DUNGEON, PointOfInterestType.PORTAL,
        PointOfInterestType.RUINS, PointOfInterestType.GRAVEYARD,
        PointOfInterestType.TEMPLE,
    ],
    BiomeType.CELESTIAL: [
        PointOfInterestType.SHRINE, PointOfInterestType.TEMPLE,
        PointOfInterestType.PORTAL, PointOfInterestType.TOWER,
        PointOfInterestType.RUINS,
    ],
}


# Population ranges per biome based on habitability.
# (min, max) population per square kilometer.
BIOME_POPULATION_DENSITY: Dict[BiomeType, Tuple[float, float]] = {
    BiomeType.FOREST: (5.0, 40.0),
    BiomeType.DESERT: (0.1, 5.0),
    BiomeType.TUNDRA: (0.5, 8.0),
    BiomeType.SWAMP: (1.0, 15.0),
    BiomeType.MOUNTAIN: (0.2, 8.0),
    BiomeType.VOLCANIC: (0.0, 2.0),
    BiomeType.OCEAN: (0.0, 0.5),
    BiomeType.PLAINS: (10.0, 80.0),
    BiomeType.JUNGLE: (2.0, 25.0),
    BiomeType.TAIGA: (1.0, 12.0),
    BiomeType.SAVANNA: (3.0, 30.0),
    BiomeType.CAVE: (0.0, 3.0),
    BiomeType.URBAN: (50.0, 500.0),
    BiomeType.RUINS: (0.5, 10.0),
    BiomeType.CORRUPTED: (0.0, 1.0),
    BiomeType.CELESTIAL: (0.1, 5.0),
}


# Base danger level range per biome.
BIOME_DANGER_LEVELS: Dict[BiomeType, Tuple[float, float]] = {
    BiomeType.FOREST: (0.1, 0.5),
    BiomeType.DESERT: (0.2, 0.6),
    BiomeType.TUNDRA: (0.2, 0.5),
    BiomeType.SWAMP: (0.3, 0.7),
    BiomeType.MOUNTAIN: (0.3, 0.7),
    BiomeType.VOLCANIC: (0.5, 0.95),
    BiomeType.OCEAN: (0.2, 0.7),
    BiomeType.PLAINS: (0.05, 0.3),
    BiomeType.JUNGLE: (0.3, 0.8),
    BiomeType.TAIGA: (0.2, 0.5),
    BiomeType.SAVANNA: (0.15, 0.5),
    BiomeType.CAVE: (0.4, 0.8),
    BiomeType.URBAN: (0.1, 0.4),
    BiomeType.RUINS: (0.3, 0.7),
    BiomeType.CORRUPTED: (0.6, 1.0),
    BiomeType.CELESTIAL: (0.3, 0.8),
}


# Region name generation pools.
REGION_NAME_PREFIXES: List[str] = [
    "Aether", "Blight", "Crystal", "Dragon", "Elder",
    "Frost", "Gloom", "Hallow", "Iron", "Jade",
    "Kings", "Lunar", "Mist", "Noble", "Opal",
    "Raven", "Silver", "Storm", "Thorn", "Verdant",
]

REGION_NAME_SUFFIXES: List[str] = [
    "Wilds", "Expanse", "Reach", "Frontier", "Blight",
    "Highlands", "Lowlands", "Badlands", "Heartlands", "Marches",
    "Shield", "Falls", "Cradle", "Fringe", "Enclave",
    "Hollow", "Depths", "Vale", "Steppe", "Moor",
]

# Descriptive phrases for environmental storytelling.
REGION_DESCRIPTION_SEGMENTS: Dict[str, List[str]] = {
    "forest": [
        "Ancient trees tower overhead, their canopies forming a dense ceiling that filters sunlight into scattered beams.",
        "The forest floor is carpeted with moss and ferns, muffling footsteps and hiding small creatures.",
        "Tangled undergrowth and twisting vines create natural corridors between the towering trunks.",
        "A constant chorus of birdsong and rustling leaves fills the air, broken occasionally by the distant call of something larger.",
    ],
    "desert": [
        "Endless dunes stretch toward the horizon, their ridges sculpted by relentless winds into flowing patterns.",
        "The sun beats down mercilessly on cracked earth, where only the hardiest life clings to existence.",
        "Heat shimmers rise from the sand, distorting distant landmarks and playing tricks on weary travelers.",
        "Scattered rock formations jut from the barren landscape, offering brief respite from the scorching sun.",
    ],
    "tundra": [
        "A frozen expanse stretches in all directions, the permafrost locking the land in an eternal winter grip.",
        "Sparse vegetation clings to the rocky soil, surviving in the brief window between frosts.",
        "The wind howls across the open plain, carrying the scent of ice and distant snow.",
        "Low clouds hang perpetually overhead, casting the landscape in shades of grey and white.",
    ],
    "swamp": [
        "Stagnant water pools among the gnarled roots of ancient trees, the surface occasionally broken by rising bubbles.",
        "A thick mist hangs over the murky waters, muffling sounds and obscuring vision.",
        "Twisted mangroves rise from the black water, their roots forming a labyrinthine network.",
        "The air is heavy with the scent of decay and damp earth, a reminder of the cycle of life and death.",
    ],
    "mountain": [
        "Jagged peaks pierce the sky, their snow-capped summits visible from leagues away.",
        "Sheer cliff faces and narrow passes make travel treacherous, rewarding only the most determined.",
        "The thin air carries the sound of distant avalanches and the cry of mountain birds.",
        "Ancient rock formations tell stories of geological upheaval spanning millennia.",
    ],
    "volcanic": [
        "Rivers of molten rock carve glowing paths down the mountainside, illuminating the ash-choked sky.",
        "The ground trembles periodically, a reminder of the immense forces churning beneath the surface.",
        "Sulfur-scented steam vents hiss from cracks in the blackened earth, painting the rocks in yellow and orange.",
        "Obsidian formations jut from the landscape, their glassy surfaces reflecting the orange glow of distant lava flows.",
    ],
    "ocean": [
        "Waves crash against rocky shores, their rhythm a constant heartbeat of the deep.",
        "The vast expanse of water stretches beyond sight, its depths hiding secrets older than civilization.",
        "Salt spray hangs in the air, carried inland by the persistent coastal winds.",
        "Coral reefs teem with life beneath the surface, a hidden world of color and movement.",
    ],
    "plains": [
        "Rolling grasslands stretch as far as the eye can see, a sea of green swaying in the breeze.",
        "Scattered groves of trees dot the landscape, providing shade and shelter for travelers and wildlife alike.",
        "The open sky dominates the horizon, making the world feel vast and full of possibility.",
        "Wildflowers bloom in season, painting the fields in bursts of color before the cycle begins anew.",
    ],
    "jungle": [
        "Dense vegetation forms a living wall of green, the canopy so thick that the forest floor exists in perpetual twilight.",
        "The air is thick with humidity and the sounds of countless creatures, from buzzing insects to calling birds.",
        "Massive buttress roots support trees that have stood for centuries, their trunks disappearing into the canopy above.",
        "Vibrant flowers and fruit hang from every branch, their colors a stark contrast to the deep greens of the foliage.",
    ],
    "taiga": [
        "Endless rows of conifers march across the landscape, their dark needles softening the harsh northern light.",
        "The ground is a patchwork of moss, lichen, and fallen needles, absorbing sound into a muffled quiet.",
        "Clear lakes reflect the sky like mirrors, their waters cold and deep, fed by melting snow.",
        "The scent of pine permeates the air, sharp and clean, carried by the steady northern breeze.",
    ],
    "savanna": [
        "Scattered trees stand like sentinels over the golden grasslands, their broad canopies casting pools of shade.",
        "The dry season paints the landscape in amber and gold, while the rains transform it into a verdant paradise.",
        "Dust devils spin across the open plain, marking the passage of wind across the sun-baked earth.",
        "Herds of grazing animals dot the horizon, their movements synchronized with the rhythm of the seasons.",
    ],
    "cave": [
        "Darkness presses in from all sides, broken only by the glow of bioluminescent fungi clinging to the walls.",
        "The sound of dripping water echoes through vast chambers, marking the slow passage of geological time.",
        "Stalactites and stalagmites form natural pillars, their surfaces glistening with mineral deposits.",
        "Narrow passages open into grand cathedrals of stone, their ceilings lost in shadow.",
    ],
    "urban": [
        "Towering spires and crowded streets form the heart of civilization, where thousands live and work in close quarters.",
        "The architecture tells the story of centuries of development, from ancient foundations to modern heights.",
        "Markets and squares buzz with activity, the constant hum of commerce and conversation filling the air.",
        "Stone walls and paved roads crisscross the district, connecting neighborhoods and landmarks.",
    ],
    "ruins": [
        "Crumbling walls and toppled columns mark where a great civilization once stood, now reclaimed by nature.",
        "The silence is heavy with history, broken only by the wind whistling through empty windows.",
        "Weathered stone bears the faint marks of inscriptions, their meanings lost to time.",
        "Vines and moss creep over ancient masonry, slowly erasing the boundary between architecture and earth.",
    ],
    "corrupted": [
        "The land itself seems to writhe, twisted into unnatural shapes by forces beyond comprehension.",
        "A palpable sense of wrongness permeates the air, making skin crawl and hearts race.",
        "The colors here are muted and sickly, as if the very light has been drained from the world.",
        "Strange growths and crystalline formations pulse with a dim, malevolent light.",
    ],
    "celestial": [
        "The ground seems to float above the clouds, bathed in an eternal twilight of shifting colors.",
        "Crystalline structures hum with energy, resonating with frequencies beyond mortal hearing.",
        "Stars are visible even in the brightest hours, their light seemingly drawn toward this sacred place.",
        "The air itself feels charged with possibility, as if the boundary between worlds grows thin here.",
    ],
}


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class WorldRegion:
    """A single region within a world, defined by its biome, terrain, and population."""

    region_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    biome: BiomeType = BiomeType.PLAINS
    size: float = 1000.0
    terrain_features: List[TerrainFeature] = field(default_factory=list)
    points_of_interest: List[str] = field(default_factory=list)
    population: int = 0
    danger_level: float = 0.3
    resources: List[str] = field(default_factory=list)
    description: str = ""
    connected_regions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "name": self.name,
            "biome": self.biome.value,
            "size": self.size,
            "terrain_features": [tf.value for tf in self.terrain_features],
            "points_of_interest": list(self.points_of_interest),
            "population": self.population,
            "danger_level": round(self.danger_level, 3),
            "resources": list(self.resources),
            "description": self.description,
            "connected_regions": list(self.connected_regions),
        }


@dataclass
class WorldMap:
    """A complete world map composed of interconnected regions."""

    map_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    regions: List[str] = field(default_factory=list)
    total_biomes: int = 0
    world_size: float = 10000.0
    seed: int = 42
    description: str = ""
    lore: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "map_id": self.map_id,
            "name": self.name,
            "regions": list(self.regions),
            "total_biomes": self.total_biomes,
            "world_size": self.world_size,
            "seed": self.seed,
            "description": self.description,
            "lore": self.lore,
            "created_at": self.created_at,
        }


@dataclass
class PointOfInterest:
    """A point of interest within a world region."""

    poi_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    poi_type: PointOfInterestType = PointOfInterestType.VILLAGE
    region_id: str = ""
    description: str = ""
    significance: str = "minor"
    npc_count: int = 0
    quest_hooks: List[str] = field(default_factory=list)
    loot_tier: int = 1
    danger_level: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "poi_id": self.poi_id,
            "name": self.name,
            "poi_type": self.poi_type.value,
            "region_id": self.region_id,
            "description": self.description,
            "significance": self.significance,
            "npc_count": self.npc_count,
            "quest_hooks": list(self.quest_hooks),
            "loot_tier": self.loot_tier,
            "danger_level": round(self.danger_level, 3),
        }


# ------------------------------------------------------------------
# WorldBuilderEngine (Singleton)
# ------------------------------------------------------------------


POI_NAME_PREFIXES: List[str] = [
    "Crimson", "Shattered", "Eternal", "Frozen", "Gilded",
    "Howling", "Jade", "Lost", "Obsidian", "Radiant",
    "Silent", "Thundering", "Twilight", "Veiled", "Whispering",
    "Iron", "Silver", "Golden", "Shadow", "Storm",
]

POI_NAME_SUFFIXES: List[str] = [
    "Keep", "Hollow", "Spire", "Cradle", "Gate",
    "Expanse", "Grove", "Canyon", "Falls", "Reach",
    "Maw", "Citadel", "Vale", "Throne", "Abyss",
    "Sanctuary", "Crossing", "Haven", "Refuge", "Watch",
]

QUEST_HOOK_TEMPLATES: List[str] = [
    "A mysterious disappearance has the locals on edge.",
    "Ancient treasure is rumored to be hidden nearby.",
    "Travelers have been attacked by unknown creatures in the area.",
    "A long-lost artifact was recently unearthed by a storm.",
    "Strange lights have been seen in the night sky.",
    "The local leader seeks aid with a growing threat.",
    "A reclusive scholar needs rare materials for research.",
    "Bandits have been raiding supply caravans along the road.",
    "A ghostly figure has been spotted near the old ruins.",
    "The water supply has been tainted by an unknown source.",
    "A messenger carrying urgent news has gone missing.",
    "Rival factions are on the brink of open conflict.",
    "An ancient seal has been weakening, causing strange phenomena.",
    "A festival is approaching, but key preparations are disrupted.",
    "Survivors of a shipwreck need escort to safety.",
    "A rare creature has been spotted, drawing hunters and scholars.",
    "The crops have been failing for three seasons straight.",
    "A forgotten shrine has been discovered deep in the wilderness.",
    "Whispers of a secret society reach the ears of the curious.",
    "A lone tower stands abandoned, yet lights flicker in its windows.",
]


class WorldBuilderEngine:
    """AI-driven world building system for the game engine.

    Generates complete game worlds with diverse biomes, terrain features,
    points of interest, population distribution, and environmental
    storytelling. Worlds are interconnected, validated for coherence,
    and designed to support narrative gameplay.

    Usage:
        engine = get_world_builder_engine()
        world = engine.generate_random_world("Eldoria", num_regions=12)
        print(world.to_dict())
    """

    _instance: Optional["WorldBuilderEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_REGIONS_PER_WORLD: int = 64
    MAX_POI_PER_REGION: int = 8
    MAX_FEATURES_PER_REGION: int = 6
    DEFAULT_WORLD_SIZE: float = 50000.0

    def __new__(cls) -> "WorldBuilderEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "WorldBuilderEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._worlds: Dict[str, WorldMap] = {}
            self._regions: Dict[str, WorldRegion] = {}
            self._pois: Dict[str, PointOfInterest] = {}
            self._region_to_world: Dict[str, str] = {}
            self._total_worlds_generated: int = 0
            self._total_regions_created: int = 0
            self._total_pois_placed: int = 0
            self._initialized = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_world(
        self,
        name: str,
        seed: int = 42,
        world_size: float = 50000.0,
        description: str = "",
    ) -> WorldMap:
        """Create an empty world map ready for region population.

        Args:
            name: Display name for the world.
            seed: Random seed for deterministic generation.
            world_size: Total area of the world in square kilometers.
            description: A brief description of the world's theme.

        Returns:
            A new WorldMap instance.
        """
        time.sleep(0.001)
        map_id = uuid.uuid4().hex

        world = WorldMap(
            map_id=map_id,
            name=name,
            regions=[],
            total_biomes=0,
            world_size=world_size,
            seed=seed,
            description=description,
            lore="",
            created_at=time.time(),
        )
        self._worlds[map_id] = world
        self._total_worlds_generated += 1
        return world

    def generate_region(
        self,
        map_id: str,
        biome: BiomeType,
        size: float = 1000.0,
        danger_level: float = 0.3,
    ) -> WorldRegion:
        """Generate a single region within an existing world map.

        Args:
            map_id: The world map to add the region to.
            biome: The biome type for this region.
            size: The region's area in square kilometers.
            danger_level: Overall danger rating (0.0 to 1.0).

        Returns:
            A new WorldRegion instance.
        """
        time.sleep(0.001)
        world = self._worlds.get(map_id)
        if world is None:
            raise ValueError(f"World map '{map_id}' not found.")

        rng = random.Random(world.seed + len(world.regions))

        region = WorldRegion(
            region_id=uuid.uuid4().hex,
            name=self._generate_region_name(rng, biome),
            biome=biome,
            size=size,
            terrain_features=[],
            points_of_interest=[],
            population=self._compute_population(biome, size, danger_level),
            danger_level=danger_level,
            resources=self._derive_resources(biome, rng),
            description=self._generate_region_description(biome, rng),
            connected_regions=[],
        )

        # Assign terrain features based on biome.
        feature_count = rng.randint(1, min(self.MAX_FEATURES_PER_REGION, len(BIOME_TERRAIN_FEATURES.get(biome, []))))
        available_features = list(BIOME_TERRAIN_FEATURES.get(biome, []))
        if available_features:
            region.terrain_features = rng.sample(
                available_features,
                min(feature_count, len(available_features)),
            )

        self._regions[region.region_id] = region
        self._region_to_world[region.region_id] = map_id
        world.regions.append(region.region_id)
        self._total_regions_created += 1

        # Update total biomes count.
        biome_set: Set[str] = set()
        for rid in world.regions:
            r = self._regions.get(rid)
            if r is not None:
                biome_set.add(r.biome.value)
        world.total_biomes = len(biome_set)

        return region

    def add_terrain_feature(
        self,
        region_id: str,
        feature: TerrainFeature,
    ) -> WorldRegion:
        """Add a terrain feature to an existing region.

        Args:
            region_id: The region to modify.
            feature: The terrain feature to add.

        Returns:
            The updated WorldRegion.
        """
        time.sleep(0.001)
        region = self._regions.get(region_id)
        if region is None:
            raise ValueError(f"Region '{region_id}' not found.")

        if feature not in region.terrain_features:
            region.terrain_features.append(feature)

        return region

    def add_point_of_interest(
        self,
        region_id: str,
        name: str,
        poi_type: PointOfInterestType,
        description: str = "",
        significance: str = "minor",
        npc_count: int = 0,
        quest_hooks: Optional[List[str]] = None,
        loot_tier: int = 1,
        danger_level: float = 0.1,
    ) -> PointOfInterest:
        """Add a point of interest to a region.

        Args:
            region_id: The region to place the POI in.
            name: Display name for the POI.
            poi_type: The type of point of interest.
            description: Narrative description of the location.
            significance: Importance level (minor, major, legendary).
            npc_count: Number of NPCs at this location.
            quest_hooks: List of quest hook descriptions.
            loot_tier: Quality tier of loot (1-5).
            danger_level: Danger rating (0.0 to 1.0).

        Returns:
            A new PointOfInterest instance.
        """
        time.sleep(0.001)
        region = self._regions.get(region_id)
        if region is None:
            raise ValueError(f"Region '{region_id}' not found.")

        poi = PointOfInterest(
            poi_id=uuid.uuid4().hex,
            name=name,
            poi_type=poi_type,
            region_id=region_id,
            description=description,
            significance=significance,
            npc_count=npc_count,
            quest_hooks=quest_hooks or [],
            loot_tier=loot_tier,
            danger_level=danger_level,
        )

        self._pois[poi.poi_id] = poi
        region.points_of_interest.append(poi.poi_id)
        self._total_pois_placed += 1

        return poi

    def connect_regions(
        self,
        region_a_id: str,
        region_b_id: str,
    ) -> WorldMap:
        """Create a bidirectional connection between two regions.

        Args:
            region_a_id: First region to connect.
            region_b_id: Second region to connect.

        Returns:
            The WorldMap containing both regions.
        """
        time.sleep(0.001)
        region_a = self._regions.get(region_a_id)
        region_b = self._regions.get(region_b_id)
        if region_a is None:
            raise ValueError(f"Region '{region_a_id}' not found.")
        if region_b is None:
            raise ValueError(f"Region '{region_b_id}' not found.")

        map_id_a = self._region_to_world.get(region_a_id)
        map_id_b = self._region_to_world.get(region_b_id)
        if map_id_a != map_id_b or map_id_a is None:
            raise ValueError("Regions must belong to the same world map.")

        if region_b_id not in region_a.connected_regions:
            region_a.connected_regions.append(region_b_id)
        if region_a_id not in region_b.connected_regions:
            region_b.connected_regions.append(region_a_id)

        world = self._worlds.get(map_id_a)
        if world is None:
            raise ValueError("World map not found.")
        return world

    def generate_random_world(
        self,
        name: str,
        num_regions: int = 10,
    ) -> WorldMap:
        """Generate a complete, diverse, interconnected world procedurally.

        This method creates a world with:
        - Varied biome distribution based on adjacency rules.
        - Appropriate terrain features per biome.
        - Points of interest with logical placement.
        - Population distribution based on biome habitability.
        - Danger level progression across regions.
        - Environmental storytelling through region descriptions.

        Args:
            name: Display name for the world.
            num_regions: Number of regions to generate (2-64).

        Returns:
            A fully generated WorldMap.
        """
        time.sleep(0.001)
        num_regions = max(2, min(num_regions, self.MAX_REGIONS_PER_WORLD))
        seed = random.randint(0, 2**31 - 1)
        rng = random.Random(seed)

        world = self.create_world(
            name=name,
            seed=seed,
            world_size=self.DEFAULT_WORLD_SIZE,
            description=f"A procedurally generated world of {num_regions} regions.",
        )

        # Phase 1: Select biomes with diversity and adjacency awareness.
        biomes = self._select_diverse_biomes(rng, num_regions)

        # Phase 2: Create regions with progressive danger levels.
        for i in range(num_regions):
            biome = biomes[i]
            size = rng.uniform(500.0, 3000.0)

            # Danger level progression: outer regions are more dangerous.
            # Center regions are safer, edges are more hostile.
            progress = i / max(num_regions - 1, 1)
            base_danger = BIOME_DANGER_LEVELS.get(biome, (0.1, 0.5))
            # Mix biome base with position-based progression.
            danger = base_danger[0] + (base_danger[1] - base_danger[0]) * (0.3 + 0.7 * progress)
            danger = round(min(1.0, max(0.0, danger)), 3)

            region = self.generate_region(
                map_id=world.map_id,
                biome=biome,
                size=size,
                danger_level=danger,
            )

            # Phase 3: Add points of interest with logical placement.
            self._populate_pois_for_region(rng, region, world.seed)

        # Phase 4: Connect regions using adjacency rules.
        self._build_region_connections(rng, world)

        # Phase 5: Generate world lore.
        world.lore = self._generate_world_lore(rng, world)

        self._total_worlds_generated += 1
        return world

    def validate_world(self, map_id: str) -> Dict[str, Any]:
        """Validate a world map for structural and logical coherence.

        Checks:
        - Region connectivity (no isolated regions).
        - Biome adjacency rules.
        - Point of interest distribution.
        - Population balance.

        Args:
            map_id: The world map to validate.

        Returns:
            A dictionary with validation results, issues, and a valid flag.
        """
        time.sleep(0.001)
        world = self._worlds.get(map_id)
        if world is None:
            return {"valid": False, "error": f"World map '{map_id}' not found.", "issues": []}

        issues: List[str] = []
        warnings: List[str] = []

        region_ids = world.regions

        # Check 1: Region connectivity (no isolated regions).
        if len(region_ids) > 1:
            visited = self._bfs_connected_regions(region_ids)
            isolated = [rid for rid in region_ids if rid not in visited]
            if isolated:
                region_names = []
                for rid in isolated:
                    r = self._regions.get(rid)
                    if r is not None:
                        region_names.append(r.name)
                issues.append(
                    f"Found {len(isolated)} isolated region(s) with no connections: "
                    f"{', '.join(region_names[:5])}"
                )

        # Check 2: Biome adjacency rules.
        for rid in region_ids:
            region = self._regions.get(rid)
            if region is None:
                continue
            compatible = BIOME_ADJACENCY_RULES.get(region.biome, [])
            for neighbor_id in region.connected_regions:
                neighbor = self._regions.get(neighbor_id)
                if neighbor is None:
                    continue
                if neighbor.biome not in compatible:
                    warnings.append(
                        f"Biome adjacency violation: '{region.name}' ({region.biome.value}) "
                        f"borders '{neighbor.name}' ({neighbor.biome.value})"
                    )

        # Check 3: Point of interest distribution.
        total_pois = 0
        empty_regions: List[str] = []
        for rid in region_ids:
            region = self._regions.get(rid)
            if region is None:
                continue
            total_pois += len(region.points_of_interest)
            if len(region.points_of_interest) == 0:
                empty_regions.append(region.name)

        if empty_regions:
            warnings.append(
                f"{len(empty_regions)} region(s) have no points of interest: "
                f"{', '.join(empty_regions[:5])}"
            )

        if total_pois == 0 and region_ids:
            issues.append("World has no points of interest at all.")

        # Check 4: Population balance.
        total_pop = 0
        zero_pop_regions: List[str] = []
        for rid in region_ids:
            region = self._regions.get(rid)
            if region is None:
                continue
            total_pop += region.population
            if region.population <= 0 and region.biome not in (
                BiomeType.VOLCANIC, BiomeType.CORRUPTED, BiomeType.CAVE,
            ):
                zero_pop_regions.append(region.name)

        if zero_pop_regions:
            warnings.append(
                f"{len(zero_pop_regions)} unexpectedly unpopulated region(s): "
                f"{', '.join(zero_pop_regions[:5])}"
            )

        if total_pop == 0 and region_ids:
            issues.append("World has zero total population.")

        # Check 5: POI type diversity per world.
        poi_types_seen: Set[str] = set()
        for rid in region_ids:
            region = self._regions.get(rid)
            if region is None:
                continue
            for poi_id in region.points_of_interest:
                poi = self._pois.get(poi_id)
                if poi is not None:
                    poi_types_seen.add(poi.poi_type.value)
        if len(poi_types_seen) < 3 and region_ids:
            warnings.append(
                f"Low POI type diversity: only {len(poi_types_seen)} distinct type(s) in world."
            )

        valid = len(issues) == 0

        return {
            "valid": valid,
            "map_id": map_id,
            "world_name": world.name,
            "region_count": len(region_ids),
            "total_pois": total_pois,
            "total_population": total_pop,
            "issues": issues,
            "warnings": warnings,
        }

    def get_region(self, region_id: str) -> Optional[WorldRegion]:
        """Retrieve a region by its ID.

        Args:
            region_id: The region identifier.

        Returns:
            The WorldRegion if found, or None.
        """
        time.sleep(0.001)
        return self._regions.get(region_id)

    def get_world(self, map_id: str) -> Optional[WorldMap]:
        """Retrieve a world map by its ID.

        Args:
            map_id: The world map identifier.

        Returns:
            The WorldMap if found, or None.
        """
        time.sleep(0.001)
        return self._worlds.get(map_id)

    def list_worlds(self) -> List[WorldMap]:
        """List all generated world maps.

        Returns:
            A list of all WorldMap instances.
        """
        time.sleep(0.001)
        return list(self._worlds.values())

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the world builder's activity.

        Returns:
            A dictionary of usage statistics and world composition data.
        """
        time.sleep(0.001)
        total_worlds = len(self._worlds)
        total_regions = len(self._regions)
        total_pois = len(self._pois)

        biome_counts: Dict[str, int] = {}
        total_population = 0
        for region in self._regions.values():
            biome_counts[region.biome.value] = biome_counts.get(region.biome.value, 0) + 1
            total_population += region.population

        poi_type_counts: Dict[str, int] = {}
        for poi in self._pois.values():
            poi_type_counts[poi.poi_type.value] = poi_type_counts.get(poi.poi_type.value, 0) + 1

        avg_danger = 0.0
        if total_regions > 0:
            avg_danger = round(
                sum(r.danger_level for r in self._regions.values()) / total_regions, 3
            )

        avg_region_size = 0.0
        if total_regions > 0:
            avg_region_size = round(
                sum(r.size for r in self._regions.values()) / total_regions, 2
            )

        return {
            "total_worlds": total_worlds,
            "total_regions": total_regions,
            "total_points_of_interest": total_pois,
            "total_population": total_population,
            "average_danger_level": avg_danger,
            "average_region_size_km2": avg_region_size,
            "biome_distribution": biome_counts,
            "poi_type_distribution": poi_type_counts,
            "worlds_generated_lifetime": self._total_worlds_generated,
            "regions_created_lifetime": self._total_regions_created,
            "pois_placed_lifetime": self._total_pois_placed,
        }

    # ------------------------------------------------------------------
    # Internal: Region Generation Helpers
    # ------------------------------------------------------------------

    def _select_diverse_biomes(
        self,
        rng: random.Random,
        count: int,
    ) -> List[BiomeType]:
        """Select a diverse set of biomes with adjacency-aware ordering.

        Ensures that adjacent biomes in the sequence are compatible
        according to BIOME_ADJACENCY_RULES.

        Args:
            rng: Random number generator.
            count: Number of biomes to select.

        Returns:
            A list of BiomeType values in generation order.
        """
        all_biomes = list(BiomeType)
        # Start with a habitable biome.
        starter_pool = [
            BiomeType.PLAINS, BiomeType.FOREST, BiomeType.SAVANNA,
            BiomeType.URBAN, BiomeType.TAIGA,
        ]
        biomes: List[BiomeType] = [rng.choice(starter_pool)]

        # Ensure minimum diversity: include at least one of several biome groups.
        mandatory_groups: List[List[BiomeType]] = [
            [BiomeType.DESERT, BiomeType.SAVANNA],
            [BiomeType.MOUNTAIN, BiomeType.VOLCANIC],
            [BiomeType.SWAMP, BiomeType.JUNGLE],
            [BiomeType.TUNDRA, BiomeType.TAIGA],
            [BiomeType.RUINS, BiomeType.CORRUPTED, BiomeType.CAVE],
        ]

        for _ in range(count - 1):
            if len(biomes) < len(mandatory_groups) and len(biomes) < count:
                # Pick from mandatory groups not yet represented.
                group_idx = len(biomes) % len(mandatory_groups)
                candidates = list(mandatory_groups[group_idx])
                current = biomes[-1]
                compatible = [
                    b for b in candidates
                    if b in BIOME_ADJACENCY_RULES.get(current, [])
                ]
                if compatible:
                    biomes.append(rng.choice(compatible))
                    continue

            # Fallback: pick from biomes compatible with the last one.
            current = biomes[-1]
            compatible = BIOME_ADJACENCY_RULES.get(current, all_biomes)
            # Exclude recently used biomes to promote diversity.
            recent = set(biomes[-3:]) if len(biomes) >= 3 else set(biomes)
            candidates = [b for b in compatible if b not in recent or len(biomes) > count - 3]
            if not candidates:
                candidates = list(compatible)
            biomes.append(rng.choice(candidates))

        return biomes

    def _populate_pois_for_region(
        self,
        rng: random.Random,
        region: WorldRegion,
        world_seed: int,
    ) -> None:
        """Generate points of interest for a region based on its biome.

        Args:
            rng: Random number generator.
            region: The region to populate.
            world_seed: The world's seed for deterministic generation.
        """
        available_types = BIOME_POI_AFFINITY.get(region.biome, [PointOfInterestType.VILLAGE])
        if not available_types:
            return

        # More POIs in safer, habitable regions; fewer in dangerous ones.
        habitable_biomes = {
            BiomeType.PLAINS, BiomeType.FOREST, BiomeType.URBAN,
            BiomeType.SAVANNA, BiomeType.JUNGLE,
        }
        if region.biome in habitable_biomes:
            poi_count = rng.randint(2, min(self.MAX_POI_PER_REGION, 5))
        else:
            poi_count = rng.randint(1, min(self.MAX_POI_PER_REGION, 3))

        # Adjust for size: larger regions get more POIs.
        if region.size > 2000.0:
            poi_count += 1
        poi_count = min(poi_count, self.MAX_POI_PER_REGION)

        for _ in range(poi_count):
            poi_type = rng.choice(available_types)
            name = self._generate_poi_name(rng, poi_type)
            significance = rng.choice(["minor", "minor", "major", "major", "legendary"])
            npc_count = self._derive_npc_count(poi_type, significance, rng)
            loot_tier = rng.randint(1, 5)
            if significance == "legendary":
                loot_tier = max(loot_tier, 4)
            poi_danger = round(region.danger_level * rng.uniform(0.5, 1.2), 3)
            poi_danger = min(1.0, max(0.0, poi_danger))

            quest_hooks = rng.sample(
                QUEST_HOOK_TEMPLATES,
                min(rng.randint(1, 3), len(QUEST_HOOK_TEMPLATES)),
            )

            description = self._generate_poi_description(poi_type, region.biome, significance, rng)

            self.add_point_of_interest(
                region_id=region.region_id,
                name=name,
                poi_type=poi_type,
                description=description,
                significance=significance,
                npc_count=npc_count,
                quest_hooks=quest_hooks,
                loot_tier=loot_tier,
                danger_level=poi_danger,
            )

    def _build_region_connections(
        self,
        rng: random.Random,
        world: WorldMap,
    ) -> None:
        """Build connections between regions ensuring no isolation.

        Uses a minimum spanning tree approach to connect all regions,
        then adds extra edges for a more natural topology.

        Args:
            rng: Random number generator.
            world: The world map to connect.
        """
        region_ids = list(world.regions)
        if len(region_ids) < 2:
            return

        # Minimum spanning tree to ensure connectivity.
        connected: List[str] = [region_ids[0]]
        remaining: Set[str] = set(region_ids[1:])

        while remaining:
            best_src: Optional[str] = None
            best_tgt: Optional[str] = None
            best_score = float("inf")

            for src_id in connected:
                src = self._regions.get(src_id)
                if src is None:
                    continue
                for tgt_id in remaining:
                    tgt = self._regions.get(tgt_id)
                    if tgt is None:
                        continue
                    # Prefer connecting compatible biomes with lower cost.
                    compatible = BIOME_ADJACENCY_RULES.get(src.biome, [])
                    compat_score = 0.0 if tgt.biome in compatible else 10.0
                    danger_diff = abs(src.danger_level - tgt.danger_level)
                    score = compat_score + danger_diff * 5.0
                    if score < best_score:
                        best_score = score
                        best_src = src_id
                        best_tgt = tgt_id

            if best_src is not None and best_tgt is not None:
                self.connect_regions(best_src, best_tgt)
                connected.append(best_tgt)
                remaining.discard(best_tgt)
            else:
                break

        # Add extra edges for a richer topology (up to 2 extra per region).
        for rid in region_ids:
            region = self._regions.get(rid)
            if region is None:
                continue
            if len(region.connected_regions) >= 3:
                continue
            candidates = [
                r for r in region_ids
                if r != rid and r not in region.connected_regions
            ]
            extra_count = rng.randint(0, min(2, len(candidates)))
            if extra_count > 0 and candidates:
                for neighbor in rng.sample(candidates, extra_count):
                    self.connect_regions(rid, neighbor)

    def _bfs_connected_regions(self, region_ids: List[str]) -> Set[str]:
        """Perform BFS from the first region to find all connected regions.

        Args:
            region_ids: All region IDs in the world.

        Returns:
            Set of region IDs reachable from the first region.
        """
        if not region_ids:
            return set()
        visited: Set[str] = set()
        queue: deque[str] = deque([region_ids[0]])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            region = self._regions.get(current)
            if region is not None:
                for neighbor in region.connected_regions:
                    if neighbor not in visited:
                        queue.append(neighbor)
        return visited

    # ------------------------------------------------------------------
    # Internal: Name and Description Generation
    # ------------------------------------------------------------------

    def _generate_region_name(
        self,
        rng: random.Random,
        biome: BiomeType,
    ) -> str:
        """Generate a unique region name combining prefix and suffix.

        Args:
            rng: Random number generator.
            biome: The region's biome for themed naming.

        Returns:
            A unique region name string.
        """
        prefix = rng.choice(REGION_NAME_PREFIXES)
        suffix = rng.choice(REGION_NAME_SUFFIXES)
        name = f"{prefix} {suffix}"
        # Ensure uniqueness.
        attempts = 0
        while any(r.name == name for r in self._regions.values()) and attempts < 20:
            prefix = rng.choice(REGION_NAME_PREFIXES)
            suffix = rng.choice(REGION_NAME_SUFFIXES)
            name = f"{prefix} {suffix}"
            attempts += 1
        return name

    def _generate_poi_name(
        self,
        rng: random.Random,
        poi_type: PointOfInterestType,
    ) -> str:
        """Generate a unique point of interest name.

        Args:
            rng: Random number generator.
            poi_type: The POI type for themed naming.

        Returns:
            A unique POI name string.
        """
        prefix = rng.choice(POI_NAME_PREFIXES)
        suffix = rng.choice(POI_NAME_SUFFIXES)
        name = f"The {prefix} {suffix}"
        attempts = 0
        while any(p.name == name for p in self._pois.values()) and attempts < 20:
            prefix = rng.choice(POI_NAME_PREFIXES)
            suffix = rng.choice(POI_NAME_SUFFIXES)
            name = f"The {prefix} {suffix}"
            attempts += 1
        return name

    def _generate_region_description(
        self,
        biome: BiomeType,
        rng: random.Random,
    ) -> str:
        """Generate environmental storytelling text for a region.

        Combines segments from the biome's description pool to create
        a unique, evocative description of the region.

        Args:
            biome: The region's biome.
            rng: Random number generator.

        Returns:
            A narrative description string.
        """
        biome_key = biome.value
        segments = REGION_DESCRIPTION_SEGMENTS.get(biome_key, REGION_DESCRIPTION_SEGMENTS.get("plains", []))
        if not segments:
            segments = ["A vast, uncharted territory stretching toward the horizon."]

        chosen = rng.sample(segments, min(2, len(segments)))
        return " ".join(chosen)

    def _generate_poi_description(
        self,
        poi_type: PointOfInterestType,
        biome: BiomeType,
        significance: str,
        rng: random.Random,
    ) -> str:
        """Generate a description for a point of interest.

        Args:
            poi_type: The type of POI.
            biome: The surrounding biome.
            significance: Importance level.
            rng: Random number generator.

        Returns:
            A narrative description string.
        """
        significance_prefix = {
            "minor": "A modest",
            "major": "An impressive",
            "legendary": "A legendary",
        }.get(significance, "A")

        description_templates: Dict[PointOfInterestType, List[str]] = {
            PointOfInterestType.VILLAGE: [
                f"{significance_prefix} settlement nestled within the {biome.value} landscape, where locals go about their daily routines.",
                f"A small {biome.value} community built from local materials, its residents welcoming to travelers.",
            ],
            PointOfInterestType.TOWN: [
                f"{significance_prefix} trade hub where merchants from surrounding regions gather to exchange goods.",
                f"A bustling market town that serves as the economic heart of the surrounding {biome.value} territory.",
            ],
            PointOfInterestType.CITY: [
                f"{significance_prefix} metropolis rising from the {biome.value}, its spires visible for miles.",
                f"A grand city of stone and ambition, where thousands of souls pursue their fortunes in the {biome.value}.",
            ],
            PointOfInterestType.DUNGEON: [
                f"{significance_prefix} underground complex carved into the {biome.value}, its depths unexplored for generations.",
                f"A dark labyrinth beneath the {biome.value} surface, where treasures and dangers lie in equal measure.",
            ],
            PointOfInterestType.TEMPLE: [
                f"{significance_prefix} sacred structure dedicated to ancient powers, its halls echoing with whispered prayers.",
                f"A place of worship built where the veil between worlds grows thin, attracting pilgrims and scholars.",
            ],
            PointOfInterestType.RUINS: [
                f"{significance_prefix} remnant of a forgotten age, its crumbling walls telling stories of glory and downfall.",
                f"Weathered stones and broken arches mark where civilization once flourished in the {biome.value}.",
            ],
            PointOfInterestType.TOWER: [
                f"{significance_prefix} spire reaching toward the sky, its purpose known only to those who dwell within.",
                f"A solitary tower standing against the {biome.value} elements, its windows flickering with mysterious light.",
            ],
            PointOfInterestType.CAMP: [
                f"{significance_prefix} encampment providing shelter for travelers braving the {biome.value}.",
                f"A temporary settlement of tents and campfires, its occupants wary but not unfriendly.",
            ],
            PointOfInterestType.OASIS: [
                f"{significance_prefix} haven of water and greenery in the {biome.value}, a lifeline for weary travelers.",
                f"A spring-fed pool surrounded by vegetation, a rare sanctuary in the harsh {biome.value}.",
            ],
            PointOfInterestType.PORTAL: [
                f"{significance_prefix} gateway shimmering with arcane energy, a threshold between worlds.",
                f"A rift in reality where the {biome.value} landscape gives way to something beyond mortal understanding.",
            ],
            PointOfInterestType.SHRINE: [
                f"{significance_prefix} sacred site marked by offerings and tokens left by those seeking favor.",
                f"A quiet place of contemplation where the {biome.value} seems to hold its breath.",
            ],
            PointOfInterestType.BRIDGE: [
                f"{significance_prefix} span crossing a natural divide, connecting two parts of the {biome.value}.",
                f"A marvel of engineering or magic, this bridge has stood against the {biome.value} elements for ages.",
            ],
            PointOfInterestType.GRAVEYARD: [
                f"{significance_prefix} burial ground where the {biome.value} slowly reclaims the markers of the dead.",
                f"Rows of weathered tombstones stand in silent testimony to those who came before.",
            ],
            PointOfInterestType.MINE: [
                f"{significance_prefix} excavation site where workers extract valuable resources from the {biome.value} earth.",
                f"Dark tunnels plunge into the {biome.value} ground, their depths promising wealth and danger.",
            ],
            PointOfInterestType.LIGHTHOUSE: [
                f"{significance_prefix} beacon standing at the edge of the {biome.value}, guiding ships safely to shore.",
                f"A tower of light that pierces through the {biome.value} darkness, a symbol of hope and warning.",
            ],
            PointOfInterestType.OUTPOST: [
                f"{significance_prefix} fortified position on the frontier of the {biome.value}, manned by vigilant guards.",
                f"A small garrison built to watch over the {biome.value} and protect against its dangers.",
            ],
        }

        templates = description_templates.get(poi_type, [
            f"A notable location within the {biome.value}, its story waiting to be discovered.",
        ])
        return rng.choice(templates)

    def _generate_world_lore(
        self,
        rng: random.Random,
        world: WorldMap,
    ) -> str:
        """Generate world lore text summarizing the world's composition.

        Args:
            rng: Random number generator.
            world: The world map to generate lore for.

        Returns:
            A narrative lore string.
        """
        region_count = len(world.regions)
        poi_count = sum(
            len(self._regions.get(rid, WorldRegion()).points_of_interest)
            for rid in world.regions
        )
        total_pop = sum(
            self._regions.get(rid, WorldRegion()).population
            for rid in world.regions
        )

        biome_names: Set[str] = set()
        for rid in world.regions:
            r = self._regions.get(rid)
            if r is not None:
                biome_names.add(r.biome.value)

        biome_list = ", ".join(sorted(biome_names)[:8])

        ages = [
            "the Age of Exploration",
            "the Era of Founding",
            "the Dawn of a New Cycle",
            "the Time of Convergence",
            "the Epoch of Strife",
            "the Century of Rebuilding",
            "the Age of Whispers",
            "the Era of Shifting Sands",
        ]

        lore_lines: List[str] = [
            f"During {rng.choice(ages)}, the world of {world.name} emerged as a land of {region_count} regions.",
            f"",
            f"Across {world.world_size:.0f} square kilometers, {len(biome_names)} distinct biomes shape the landscape: {biome_list}.",
            f"",
            f"A population of {total_pop:,} souls inhabits this world, scattered across {poi_count} points of interest.",
            f"Each region tells its own story, from the safest heartlands to the most dangerous frontiers.",
            f"",
            f"Travelers who brave the connected regions will find adventure, danger, and discovery.",
            f"Maps show intricate networks of paths linking settlements, ruins, and natural wonders.",
            f"",
            f"The balance of power shifts with every season, as factions rise and fall.",
            f"Legends speak of secrets hidden in the oldest places, waiting for those bold enough to seek them.",
        ]

        # Add region-specific lore for the first few regions.
        for rid in world.regions[:4]:
            region = self._regions.get(rid)
            if region is None:
                continue
            lore_lines.append("")
            lore_lines.append(
                f"The {region.name} is a {region.biome.value} region spanning {region.size:.0f} square kilometers. "
                f"Home to {region.population:,} inhabitants, its danger level of {region.danger_level:.1%} "
                f"makes it {'a treacherous frontier' if region.danger_level > 0.5 else 'a relatively safe domain'}."
            )

        return "\n".join(lore_lines)

    # ------------------------------------------------------------------
    # Internal: Computation Helpers
    # ------------------------------------------------------------------

    def _compute_population(
        self,
        biome: BiomeType,
        size: float,
        danger_level: float,
    ) -> int:
        """Compute population for a region based on biome habitability and size.

        Args:
            biome: The region's biome.
            size: Region area in square kilometers.
            danger_level: Danger rating affecting population.

        Returns:
            Estimated population count.
        """
        density_range = BIOME_POPULATION_DENSITY.get(biome, (1.0, 20.0))
        base_density = density_range[0] + (density_range[1] - density_range[0]) * 0.5
        # Higher danger reduces population.
        danger_penalty = 1.0 - danger_level * 0.8
        effective_density = base_density * danger_penalty
        return max(0, int(effective_density * size))

    def _derive_resources(
        self,
        biome: BiomeType,
        rng: random.Random,
    ) -> List[str]:
        """Derive natural resources available in a biome.

        Args:
            biome: The region's biome.
            rng: Random number generator.

        Returns:
            A list of resource name strings.
        """
        resource_pools: Dict[BiomeType, List[str]] = {
            BiomeType.FOREST: ["timber", "herbs", "game", "mushrooms", "berries", "honey"],
            BiomeType.DESERT: ["salt", "glass_sand", "oil", "gems", "cactus_fruit"],
            BiomeType.TUNDRA: ["fur", "oil", "iron", "ice", "peat"],
            BiomeType.SWAMP: ["peat", "herbs", "venom", "reeds", "fish", "clay"],
            BiomeType.MOUNTAIN: ["iron", "coal", "gold", "stone", "gems", "marble"],
            BiomeType.VOLCANIC: ["obsidian", "sulfur", "gems", "iron", "basalt"],
            BiomeType.OCEAN: ["fish", "pearls", "coral", "salt", "oil"],
            BiomeType.PLAINS: ["grain", "livestock", "clay", "freshwater", "wool"],
            BiomeType.JUNGLE: ["rare_herbs", "exotic_fruit", "venom", "timber", "dyes"],
            BiomeType.TAIGA: ["timber", "fur", "iron", "amber", "honey"],
            BiomeType.SAVANNA: ["livestock", "grain", "clay", "salt", "ivory"],
            BiomeType.CAVE: ["gems", "crystals", "mushrooms", "iron", "coal"],
            BiomeType.URBAN: ["crafted_goods", "coin", "textiles", "spices", "tools"],
            BiomeType.RUINS: ["ancient_relics", "salvage", "stone", "scrolls", "artifacts"],
            BiomeType.CORRUPTED: ["void_crystals", "shadow_essence", "corrupted_iron", "dark_matter"],
            BiomeType.CELESTIAL: ["starlight_shards", "aether_essence", "moonstone", "celestial_dust"],
        }

        pool = resource_pools.get(biome, ["stone", "wood", "water"])
        count = rng.randint(2, min(4, len(pool)))
        return rng.sample(pool, count)

    def _derive_npc_count(
        self,
        poi_type: PointOfInterestType,
        significance: str,
        rng: random.Random,
    ) -> int:
        """Derive NPC count for a point of interest.

        Args:
            poi_type: The type of POI.
            significance: Importance level.
            rng: Random number generator.

        Returns:
            Number of NPCs present.
        """
        base_ranges: Dict[PointOfInterestType, Tuple[int, int]] = {
            PointOfInterestType.VILLAGE: (5, 30),
            PointOfInterestType.TOWN: (20, 80),
            PointOfInterestType.CITY: (50, 200),
            PointOfInterestType.DUNGEON: (2, 15),
            PointOfInterestType.TEMPLE: (3, 20),
            PointOfInterestType.RUINS: (0, 10),
            PointOfInterestType.TOWER: (1, 10),
            PointOfInterestType.CAMP: (3, 25),
            PointOfInterestType.OASIS: (2, 15),
            PointOfInterestType.PORTAL: (0, 5),
            PointOfInterestType.SHRINE: (1, 8),
            PointOfInterestType.BRIDGE: (1, 5),
            PointOfInterestType.GRAVEYARD: (0, 3),
            PointOfInterestType.MINE: (5, 30),
            PointOfInterestType.LIGHTHOUSE: (1, 5),
            PointOfInterestType.OUTPOST: (5, 25),
        }

        lo, hi = base_ranges.get(poi_type, (1, 10))
        # Significance amplifies NPC count.
        sig_mult = {"minor": 1.0, "major": 1.8, "legendary": 3.0}.get(significance, 1.0)
        return max(0, int(rng.randint(lo, hi) * sig_mult))


# ------------------------------------------------------------------
# Module-Level Accessor
# ------------------------------------------------------------------


def get_world_builder_engine() -> WorldBuilderEngine:
    """Get the singleton WorldBuilderEngine instance."""
    return WorldBuilderEngine.get_instance()