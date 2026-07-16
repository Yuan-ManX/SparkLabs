"""
SparkLabs Agent - World Synthesizer

AI-driven procedural world generation system that synthesizes complete game
worlds from high-level descriptions. Combines terrain generation, ecosystem
simulation, structure placement, and narrative seeding to create coherent,
playable game environments with integrated world simulation capabilities.

Architecture:
  AgentWorldSynthesizer (Singleton)
    |-- TerrainGenerator (heightmap, biome, erosion simulation)
    |-- EcosystemSimulator (flora, fauna, food chain dynamics)
    |-- StructurePlacer (settlements, dungeons, landmarks)
    |-- NarrativeSeeder (quest hooks, lore fragments, world history)
    |-- WorldValidator (playability checks, balance verification)
    |-- WorldExporter (engine-ready world data export)

Generation Layers:
  - TERRAIN: height, water, biomes, climate
  - ECOLOGY: vegetation, wildlife, resources
  - CIVILIZATION: settlements, roads, factions
  - DUNGEON: underground structures, loot distribution
  - NARRATIVE: story hooks, NPC backstories, world events

Usage:
    ws = AgentWorldSynthesizer.get_instance()
    ws.initialize()

    world_config = ws.generate_world_config("fantasy forest with ancient ruins", 2048, 2048)
    terrain = ws.generate_terrain(world_config)
    ecosystem = ws.place_ecosystem(terrain, world_config)
    structures = ws.place_structures(terrain, ecosystem, world_config)
    narrative = ws.seed_narrative(structures, world_config)

    world_data = ws.export_world(terrain, ecosystem, structures, narrative)
    ws.shutdown()
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


# =============================================================================
# Enums
# =============================================================================


class BiomeType(Enum):
    """World biome types."""
    TUNDRA = "tundra"
    TAIGA = "taiga"
    TEMPERATE_FOREST = "temperate_forest"
    GRASSLAND = "grassland"
    DESERT = "desert"
    SAVANNA = "savanna"
    TROPICAL_RAINFOREST = "tropical_rainforest"
    SWAMP = "swamp"
    MOUNTAIN = "mountain"
    COASTAL = "coastal"
    VOLCANIC = "volcanic"
    MYSTIC = "mystic"
    VOID = "void"


class StructureType(Enum):
    """Types of world structures."""
    SETTLEMENT = "settlement"
    DUNGEON = "dungeon"
    TEMPLE = "temple"
    RUIN = "ruin"
    FORTRESS = "fortress"
    CAVE = "cave"
    TOWER = "tower"
    CAMP = "camp"
    PORTAL = "portal"
    MONUMENT = "monument"
    BRIDGE = "bridge"
    MINE = "mine"


class TerrainLayer(Enum):
    """Terrain generation layers."""
    HEIGHTMAP = "heightmap"
    TEMPERATURE = "temperature"
    MOISTURE = "moisture"
    BIOME = "biome"
    RIVERS = "rivers"
    EROSION = "erosion"


class WorldTheme(Enum):
    """World thematic categories."""
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    POST_APOCALYPTIC = "post_apocalyptic"
    HISTORICAL = "historical"
    MYTHOLOGICAL = "mythological"
    STEAMPUNK = "steampunk"
    CYBERPUNK = "cyberpunk"
    LOVE_CRAFTIAN = "lovecraftian"
    FAIRY_TALE = "fairy_tale"
    CUSTOM = "custom"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WorldConfig:
    """Configuration for world generation."""
    config_id: str
    theme: WorldTheme = WorldTheme.FANTASY
    description: str = ""
    width: int = 1024
    height: int = 1024
    seed: int = 0
    sea_level: float = 0.3
    mountain_level: float = 0.7
    biome_count: int = 5
    settlement_count: int = 8
    dungeon_count: int = 5
    population_density: float = 0.5
    resource_richness: float = 0.6
    danger_level: float = 0.4
    magic_level: float = 0.3
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "theme": self.theme.value,
            "description": self.description,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "sea_level": self.sea_level,
            "mountain_level": self.mountain_level,
            "biome_count": self.biome_count,
            "settlement_count": self.settlement_count,
            "dungeon_count": self.dungeon_count,
            "population_density": self.population_density,
            "resource_richness": self.resource_richness,
            "danger_level": self.danger_level,
            "magic_level": self.magic_level,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class TerrainData:
    """Generated terrain data."""
    terrain_id: str
    heightmap: List[List[float]] = field(default_factory=list)
    biome_map: List[List[int]] = field(default_factory=list)
    river_paths: List[List[Tuple[int, int]]] = field(default_factory=list)
    biomes: List[BiomeType] = field(default_factory=list)
    width: int = 0
    height: int = 0
    seed: int = 0

    def get_height_at(self, x: int, y: int) -> float:
        if 0 <= x < self.width and 0 <= y < self.height and self.heightmap:
            return self.heightmap[y][x]
        return 0.0

    def get_biome_at(self, x: int, y: int) -> Optional[BiomeType]:
        if 0 <= x < self.width and 0 <= y < self.height and self.biome_map:
            idx = self.biome_map[y][x]
            if 0 <= idx < len(self.biomes):
                return self.biomes[idx]
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "terrain_id": self.terrain_id,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "biome_count": len(self.biomes),
            "biomes": [b.value for b in self.biomes],
            "river_count": len(self.river_paths),
        }


@dataclass
class EcosystemData:
    """Ecosystem placement data."""
    ecosystem_id: str
    vegetation_zones: List[Dict[str, Any]] = field(default_factory=list)
    wildlife_packs: List[Dict[str, Any]] = field(default_factory=list)
    resource_nodes: List[Dict[str, Any]] = field(default_factory=list)
    flora_count: int = 0
    fauna_count: int = 0
    resource_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "flora_count": self.flora_count,
            "fauna_count": self.fauna_count,
            "resource_count": self.resource_count,
            "vegetation_zones": len(self.vegetation_zones),
            "wildlife_packs": len(self.wildlife_packs),
        }


@dataclass
class StructureData:
    """Placed structure data."""
    structures: List[Dict[str, Any]] = field(default_factory=list)
    roads: List[Dict[str, Any]] = field(default_factory=list)
    regions: List[Dict[str, Any]] = field(default_factory=list)
    faction_count: int = 0
    total_structures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_structures": self.total_structures,
            "faction_count": self.faction_count,
            "road_count": len(self.roads),
            "region_count": len(self.regions),
            "structures": self.structures,
            "roads": self.roads,
            "regions": self.regions,
        }


@dataclass
class NarrativeData:
    """World narrative seeding data."""
    narrative_id: str
    world_history: List[Dict[str, Any]] = field(default_factory=list)
    quest_hooks: List[Dict[str, Any]] = field(default_factory=list)
    faction_lore: List[Dict[str, Any]] = field(default_factory=list)
    npc_archetypes: List[Dict[str, Any]] = field(default_factory=list)
    world_events: List[Dict[str, Any]] = field(default_factory=list)
    theme: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "narrative_id": self.narrative_id,
            "theme": self.theme,
            "history_events": len(self.world_history),
            "quest_hooks": len(self.quest_hooks),
            "faction_lore": len(self.faction_lore),
            "npc_archetypes": len(self.npc_archetypes),
            "world_events": len(self.world_events),
        }


# =============================================================================
# World Synthesizer
# =============================================================================


class AgentWorldSynthesizer:
    """
    AI-driven world synthesis engine for procedural game world generation.
    Generates complete worlds from high-level descriptions through layered
    terrain, ecosystem, structure, and narrative generation.
    """

    _instance: Optional["AgentWorldSynthesizer"] = None
    _instance_lock = threading.RLock()

    # Biome definitions by theme
    _THEME_BIOMES: Dict[WorldTheme, List[BiomeType]] = {
        WorldTheme.FANTASY: [BiomeType.TEMPERATE_FOREST, BiomeType.GRASSLAND,
                             BiomeType.MOUNTAIN, BiomeType.SWAMP, BiomeType.MYSTIC],
        WorldTheme.SCI_FI: [BiomeType.DESERT, BiomeType.VOLCANIC, BiomeType.TUNDRA,
                            BiomeType.MOUNTAIN, BiomeType.VOID],
        WorldTheme.POST_APOCALYPTIC: [BiomeType.DESERT, BiomeType.SWAMP,
                                       BiomeType.GRASSLAND, BiomeType.VOLCANIC, BiomeType.VOID],
        WorldTheme.STEAMPUNK: [BiomeType.TEMPERATE_FOREST, BiomeType.MOUNTAIN,
                                BiomeType.GRASSLAND, BiomeType.COASTAL, BiomeType.VOLCANIC],
        WorldTheme.CYBERPUNK: [BiomeType.DESERT, BiomeType.COASTAL, BiomeType.TUNDRA,
                                BiomeType.MOUNTAIN, BiomeType.VOID],
    }

    def __init__(self) -> None:
        if AgentWorldSynthesizer._instance is not None:
            raise RuntimeError("Use AgentWorldSynthesizer.get_instance()")
        self._initialized: bool = False
        self._worlds: Dict[str, Dict[str, Any]] = {}
        self._configs: Dict[str, WorldConfig] = {}
        self._terrains: Dict[str, TerrainData] = {}
        self._ecosystems: Dict[str, EcosystemData] = {}
        self._structures: Dict[str, StructureData] = {}
        self._narratives: Dict[str, NarrativeData] = {}
        self._stats: Dict[str, Any] = {
            "worlds_generated": 0,
            "total_structures_placed": 0,
            "total_quests_seeded": 0,
            "generation_time_ms": 0.0,
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "AgentWorldSynthesizer":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, default_seed: Optional[int] = None) -> None:
        """Initialize the world synthesizer."""
        with self._lock:
            if self._initialized:
                return
            self._default_seed = default_seed or int(time.time() * 1000)
            self._initialized = True

    # -------------------------------------------------------------------------
    # World Configuration
    # -------------------------------------------------------------------------

    def generate_world_config(self, description: str,
                              width: int = 1024, height: int = 1024,
                              theme: Optional[WorldTheme] = None,
                              seed: Optional[int] = None) -> WorldConfig:
        """Generate a world configuration from a description."""
        config_id = uuid.uuid4().hex[:12]
        if seed is None:
            seed = hash(description) % (2**31)

        # Auto-detect theme from description
        if theme is None:
            theme = self._detect_theme(description)

        config = WorldConfig(
            config_id=config_id,
            theme=theme,
            description=description,
            width=width,
            height=height,
            seed=seed,
            biome_count=min(5, len(self._THEME_BIOMES.get(theme, list(BiomeType)))),
            tags=self._extract_tags(description),
        )

        self._configs[config_id] = config
        return config

    def _detect_theme(self, description: str) -> WorldTheme:
        """Auto-detect world theme from description."""
        desc_lower = description.lower()
        theme_keywords = {
            WorldTheme.FANTASY: ["fantasy", "magic", "dragon", "elf", "wizard", "castle", "medieval"],
            WorldTheme.SCI_FI: ["sci-fi", "space", "robot", "alien", "futuristic", "laser", "planet"],
            WorldTheme.POST_APOCALYPTIC: ["apocalyptic", "wasteland", "zombie", "survival", "ruined"],
            WorldTheme.STEAMPUNK: ["steampunk", "steam", "clockwork", "victorian", "airship", "gear"],
            WorldTheme.CYBERPUNK: ["cyberpunk", "neon", "hacker", "megacorp", "dystopian", "cyborg"],
            WorldTheme.MYTHOLOGICAL: ["myth", "god", "olympus", "norse", "greek", "legend", "ancient"],
            WorldTheme.LOVE_CRAFTIAN: ["cosmic", "elder", "abyss", "madness", "tentacle", "forbidden"],
            WorldTheme.FAIRY_TALE: ["fairy", "enchanted", "tale", "whimsical", "storybook"],
        }
        for theme, keywords in theme_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                return theme
        return WorldTheme.FANTASY

    def _extract_tags(self, description: str) -> List[str]:
        """Extract meaningful tags from description."""
        common_tags = ["forest", "desert", "mountain", "ocean", "river", "snow",
                       "dungeon", "castle", "village", "city", "ruins", "cave",
                       "underground", "sky", "floating", "underwater", "volcanic"]
        desc_lower = description.lower()
        return [tag for tag in common_tags if tag in desc_lower]

    # -------------------------------------------------------------------------
    # Terrain Generation
    # -------------------------------------------------------------------------

    def generate_terrain(self, config: WorldConfig) -> TerrainData:
        """Generate layered terrain from world configuration."""
        terrain_id = uuid.uuid4().hex[:12]
        random.seed(config.seed)

        width, height = config.width, config.height
        terrain = TerrainData(
            terrain_id=terrain_id,
            width=width,
            height=height,
            seed=config.seed,
        )

        # Layer 1: Heightmap generation using simplex-like noise
        terrain.heightmap = self._generate_heightmap(width, height, config)

        # Layer 2: Biome assignment
        biomes = self._THEME_BIOMES.get(config.theme, [BiomeType.TEMPERATE_FOREST,
                                                         BiomeType.GRASSLAND,
                                                         BiomeType.MOUNTAIN])
        terrain.biomes = biomes[:config.biome_count]
        terrain.biome_map = self._assign_biomes(terrain.heightmap, terrain.biomes, width, height, config)

        # Layer 3: River generation
        terrain.river_paths = self._generate_rivers(terrain.heightmap, width, height, config)

        self._terrains[terrain_id] = terrain
        return terrain

    def _generate_heightmap(self, width: int, height: int,
                            config: WorldConfig) -> List[List[float]]:
        """Generate heightmap using multi-octave noise."""
        heightmap = [[0.0] * width for _ in range(height)]
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0

        for octave in range(octaves):
            frequency = 2 ** octave
            amplitude = persistence ** octave
            scale = max(width, height) / frequency

            for y in range(height):
                for x in range(width):
                    nx = x / scale * 2 * math.pi
                    ny = y / scale * 2 * math.pi
                    noise = (math.sin(nx * 1.3 + config.seed * 0.001) *
                             math.cos(ny * 0.7 + config.seed * 0.002) +
                             math.sin((nx + ny) * 0.9 + config.seed * 0.003) * 0.5)
                    heightmap[y][x] += noise * amplitude

        # Normalize to 0-1
        min_h = min(min(row) for row in heightmap)
        max_h = max(max(row) for row in heightmap)
        range_h = max(max_h - min_h, 0.001)
        for y in range(height):
            for x in range(width):
                heightmap[y][x] = (heightmap[y][x] - min_h) / range_h

        return heightmap

    def _assign_biomes(self, heightmap: List[List[float]], biomes: List[BiomeType],
                       width: int, height: int, config: WorldConfig) -> List[List[int]]:
        """Assign biomes based on height and moisture."""
        biome_map = [[0] * width for _ in range(height)]
        num_biomes = len(biomes)

        for y in range(height):
            for x in range(width):
                h = heightmap[y][x]
                moisture = (math.sin(x * 0.01 + y * 0.01 + config.seed) + 1) / 2

                if h < config.sea_level:
                    biome_map[y][x] = 0  # Water-adjacent biome
                elif h > config.mountain_level:
                    biome_map[y][x] = min(num_biomes - 1, num_biomes - 2)  # Mountain biome
                else:
                    zone = int((h - config.sea_level) / (config.mountain_level - config.sea_level) * (num_biomes - 2))
                    biome_map[y][x] = max(0, min(num_biomes - 1, zone + 1))

        return biome_map

    def _generate_rivers(self, heightmap: List[List[float]], width: int, height: int,
                         config: WorldConfig) -> List[List[Tuple[int, int]]]:
        """Generate river paths from mountains to sea."""
        rivers = []
        num_rivers = max(2, width // 256)

        for _ in range(num_rivers):
            # Start from a mountain point
            candidates = [(x, y) for y in range(height) for x in range(width)
                          if heightmap[y][x] > config.mountain_level]
            if not candidates:
                break
            start = random.choice(candidates)
            path = self._trace_river(start, heightmap, width, height, config.sea_level)
            if len(path) > 10:
                rivers.append(path)

        return rivers

    def _trace_river(self, start: Tuple[int, int], heightmap: List[List[float]],
                     width: int, height: int, sea_level: float) -> List[Tuple[int, int]]:
        """Trace a river path downhill."""
        path = [start]
        cx, cy = start
        max_steps = max(width, height) * 2
        visited = set()

        for _ in range(max_steps):
            visited.add((cx, cy))
            if heightmap[cy][cx] < sea_level:
                break

            # Find lowest neighbor
            best = (cx, cy)
            best_h = heightmap[cy][cx]
            for dx, dy in [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                    if heightmap[ny][nx] < best_h:
                        best_h = heightmap[ny][nx]
                        best = (nx, ny)

            if best == (cx, cy):
                break
            cx, cy = best
            path.append((cx, cy))

        return path

    # -------------------------------------------------------------------------
    # Ecosystem Placement
    # -------------------------------------------------------------------------

    def place_ecosystem(self, terrain: TerrainData, config: WorldConfig) -> EcosystemData:
        """Place ecosystem elements based on terrain."""
        eco_id = uuid.uuid4().hex[:12]
        ecosystem = EcosystemData(ecosystem_id=eco_id)

        # Vegetation zones
        for y in range(0, terrain.height, 32):
            for x in range(0, terrain.width, 32):
                biome = terrain.get_biome_at(x, y)
                if biome and terrain.get_height_at(x, y) > config.sea_level:
                    vegetation = self._generate_vegetation(x, y, biome, config)
                    ecosystem.vegetation_zones.append(vegetation)
                    ecosystem.flora_count += vegetation.get("density", 0)

        # Wildlife packs
        for _ in range(max(5, terrain.width // 128)):
            wx = random.randint(0, terrain.width - 1)
            wy = random.randint(0, terrain.height - 1)
            biome = terrain.get_biome_at(wx, wy)
            if biome:
                pack = self._generate_wildlife_pack(wx, wy, biome, config)
                ecosystem.wildlife_packs.append(pack)
                ecosystem.fauna_count += pack.get("count", 0)

        # Resource nodes
        for _ in range(max(10, terrain.width // 64)):
            rx = random.randint(0, terrain.width - 1)
            ry = random.randint(0, terrain.height - 1)
            biome = terrain.get_biome_at(rx, ry)
            if biome:
                resource = self._generate_resource_node(rx, ry, biome, config)
                ecosystem.resource_nodes.append(resource)
                ecosystem.resource_count += 1

        self._ecosystems[eco_id] = ecosystem
        return ecosystem

    def _generate_vegetation(self, x: int, y: int, biome: BiomeType,
                             config: WorldConfig) -> Dict[str, Any]:
        """Generate vegetation data for a zone."""
        flora_types = {
            BiomeType.TEMPERATE_FOREST: ["oak", "pine", "birch", "fern"],
            BiomeType.GRASSLAND: ["tall_grass", "wildflower", "shrub"],
            BiomeType.DESERT: ["cactus", "dry_bush", "tumbleweed"],
            BiomeType.TUNDRA: ["lichen", "moss", "dwarf_shrub"],
            BiomeType.SWAMP: ["mangrove", "cattail", "lily_pad"],
            BiomeType.TROPICAL_RAINFOREST: ["palm", "bamboo", "vine", "orchid"],
            BiomeType.MYSTIC: ["glowing_mushroom", "crystal_flower", "spirit_vine"],
        }
        types = flora_types.get(biome, ["generic_tree"])
        return {
            "position": [x, y],
            "biome": biome.value,
            "flora_types": types,
            "density": int(random.uniform(0.3, 1.0) * config.resource_richness * 10),
        }

    def _generate_wildlife_pack(self, x: int, y: int, biome: BiomeType,
                                config: WorldConfig) -> Dict[str, Any]:
        """Generate a wildlife pack."""
        fauna = {
            BiomeType.TEMPERATE_FOREST: ["deer", "wolf", "bear", "rabbit"],
            BiomeType.GRASSLAND: ["bison", "hawk", "fox", "snake"],
            BiomeType.DESERT: ["scorpion", "camel", "vulture", "lizard"],
            BiomeType.SWAMP: ["crocodile", "frog", "heron", "snake"],
            BiomeType.MYSTIC: ["will-o-wisp", "fey_dragon", "spirit_wolf"],
        }
        types = fauna.get(biome, ["creature"])
        return {
            "position": [x, y],
            "biome": biome.value,
            "species": random.choice(types),
            "count": max(1, int(config.population_density * 5)),
        }

    def _generate_resource_node(self, x: int, y: int, biome: BiomeType,
                                config: WorldConfig) -> Dict[str, Any]:
        """Generate a resource node."""
        resources = {
            BiomeType.TEMPERATE_FOREST: ["wood", "herbs", "stone"],
            BiomeType.MOUNTAIN: ["iron_ore", "gold_ore", "gems", "stone"],
            BiomeType.DESERT: ["sandstone", "oil", "salt"],
            BiomeType.SWAMP: ["peat", "clay", "medicinal_herbs"],
            BiomeType.MYSTIC: ["mana_crystal", "arcane_dust", "ethereal_essence"],
        }
        types = resources.get(biome, ["generic_resource"])
        return {
            "position": [x, y],
            "biome": biome.value,
            "resource_type": random.choice(types),
            "richness": round(random.uniform(0.1, 1.0) * config.resource_richness, 2),
        }

    # -------------------------------------------------------------------------
    # Structure Placement
    # -------------------------------------------------------------------------

    def place_structures(self, terrain: TerrainData, ecosystem: EcosystemData,
                         config: WorldConfig) -> StructureData:
        """Place structures across the world."""
        structures = StructureData()

        # Place settlements
        for i in range(config.settlement_count):
            pos = self._find_buildable_spot(terrain, config, structures.structures)
            if pos:
                settlement = {
                    "id": f"settlement_{i}",
                    "type": StructureType.SETTLEMENT.value,
                    "position": list(pos),
                    "name": self._generate_settlement_name(config.theme),
                    "size": random.choice(["village", "town", "city"]),
                    "faction": f"faction_{i % 3}",
                }
                structures.structures.append(settlement)
                structures.total_structures += 1

        # Place dungeons
        for i in range(config.dungeon_count):
            pos = self._find_buildable_spot(terrain, config, structures.structures, min_distance=100)
            if pos:
                dungeon = {
                    "id": f"dungeon_{i}",
                    "type": StructureType.DUNGEON.value,
                    "position": list(pos),
                    "name": f"Dark Depths of {self._generate_dungeon_name()}",
                    "floors": random.randint(1, 5),
                    "danger": round(config.danger_level * random.uniform(0.5, 1.5), 2),
                }
                structures.structures.append(dungeon)
                structures.total_structures += 1

        # Generate roads between settlements
        settlements = [s for s in structures.structures
                       if s["type"] == StructureType.SETTLEMENT.value]
        structures.roads = self._generate_road_network(settlements, terrain)

        # Faction regions
        structures.regions = self._generate_faction_regions(settlements, terrain.width, terrain.height)
        structures.faction_count = len(set(r.get("faction", "") for r in structures.regions))

        return structures

    def _find_buildable_spot(self, terrain: TerrainData, config: WorldConfig,
                             existing: List[Dict[str, Any]],
                             min_distance: float = 50) -> Optional[Tuple[float, float]]:
        """Find a suitable spot for building."""
        for _ in range(100):
            x = random.uniform(20, terrain.width - 20)
            y = random.uniform(20, terrain.height - 20)
            ix, iy = int(x), int(y)

            h = terrain.get_height_at(ix, iy)
            if h < config.sea_level or h > config.mountain_level:
                continue

            # Check distance from existing structures
            too_close = False
            for existing_structure in existing:
                ex, ey = existing_structure["position"]
                if math.sqrt((x - ex)**2 + (y - ey)**2) < min_distance:
                    too_close = True
                    break
            if too_close:
                continue

            return (x, y)
        return None

    def _generate_settlement_name(self, theme: WorldTheme) -> str:
        """Generate a settlement name."""
        prefixes = ["North", "South", "East", "West", "Old", "New", "Great", "Little", "High", "Deep"]
        suffixes = {
            WorldTheme.FANTASY: ["haven", "dale", "shire", "crest", "moor", "glen"],
            WorldTheme.SCI_FI: ["station", "colony", "outpost", "base", "hub"],
            WorldTheme.STEAMPUNK: ["forge", "works", "mill", "junction", "gears"],
        }
        theme_suffixes = suffixes.get(theme, ["town", "ville", "burg"])
        return f"{random.choice(prefixes)}{random.choice(theme_suffixes)}"

    def _generate_dungeon_name(self) -> str:
        """Generate a dungeon name."""
        parts = ["Shadow", "Crystal", "Obsidian", "Frozen", "Burning", "Whispering",
                 "Echoing", "Sunken", "Forgotten", "Cursed"]
        return random.choice(parts)

    def _generate_road_network(self, settlements: List[Dict[str, Any]],
                               terrain: TerrainData) -> List[Dict[str, Any]]:
        """Generate roads connecting settlements."""
        roads = []
        for i, s1 in enumerate(settlements):
            for j, s2 in enumerate(settlements):
                if i < j:
                    dist = math.sqrt(
                        (s1["position"][0] - s2["position"][0])**2 +
                        (s1["position"][1] - s2["position"][1])**2
                    )
                    if dist < 300:
                        roads.append({
                            "from": s1["id"],
                            "to": s2["id"],
                            "distance": round(dist, 1),
                        })
        return roads

    def _generate_faction_regions(self, settlements: List[Dict[str, Any]],
                                  width: int, height: int) -> List[Dict[str, Any]]:
        """Generate faction territories."""
        factions = {}
        for s in settlements:
            faction = s.get("faction", "neutral")
            if faction not in factions:
                factions[faction] = []
            factions[faction].append(s["position"])

        regions = []
        for faction, positions in factions.items():
            if positions:
                cx = sum(p[0] for p in positions) / len(positions)
                cy = sum(p[1] for p in positions) / len(positions)
                regions.append({
                    "faction": faction,
                    "center": [round(cx, 1), round(cy, 1)],
                    "settlement_count": len(positions),
                    "radius": random.uniform(100, 200),
                })
        return regions

    # -------------------------------------------------------------------------
    # Narrative Seeding
    # -------------------------------------------------------------------------

    def seed_narrative(self, structures: StructureData, config: WorldConfig) -> NarrativeData:
        """Seed narrative elements into the world."""
        narrative_id = uuid.uuid4().hex[:12]
        narrative = NarrativeData(
            narrative_id=narrative_id,
            theme=config.theme.value,
        )

        # World history events
        narrative.world_history = self._generate_world_history(config)

        # Quest hooks from structures
        for structure in structures.structures:
            quest = self._generate_quest_hook(structure, config)
            narrative.quest_hooks.append(quest)
            self._stats["total_quests_seeded"] += 1

        # Faction lore
        for region in structures.regions:
            lore = self._generate_faction_lore(region, config)
            narrative.faction_lore.append(lore)

        # NPC archetypes
        narrative.npc_archetypes = self._generate_npc_archetypes(structures, config)

        # World events
        narrative.world_events = self._generate_world_events(structures, config)

        self._narratives[narrative_id] = narrative
        return narrative

    def _generate_world_history(self, config: WorldConfig) -> List[Dict[str, Any]]:
        """Generate world history timeline."""
        events = [
            {"era": "Creation", "event": "The world was formed from primordial chaos", "age": 0},
            {"era": "Ancient", "event": "First civilizations rose and fell", "age": -5000},
            {"era": "Cataclysm", "event": "A great disaster reshaped the land", "age": -1000},
            {"era": "Rebuilding", "event": "Survivors began rebuilding civilization", "age": -500},
            {"era": "Current", "event": "Factions vie for power in the new world", "age": 0},
        ]
        return events

    def _generate_quest_hook(self, structure: Dict[str, Any],
                             config: WorldConfig) -> Dict[str, Any]:
        """Generate a quest hook from a structure."""
        quest_types = {
            StructureType.SETTLEMENT.value: ["defend", "deliver", "investigate", "recruit"],
            StructureType.DUNGEON.value: ["explore", "clear", "retrieve", "slay"],
            StructureType.RUIN.value: ["excavate", "study", "recover", "seal"],
            StructureType.TEMPLE.value: ["pilgrimage", "purify", "restore", "protect"],
        }
        types = quest_types.get(structure["type"], ["explore", "discover"])
        return {
            "structure_id": structure["id"],
            "quest_type": random.choice(types),
            "title": f"The {structure.get('name', 'Unknown')} {random.choice(['Mystery', 'Secret', 'Threat', 'Promise'])}",
            "danger_level": round(config.danger_level * random.uniform(0.3, 1.5), 2),
            "reward_tier": random.choice(["common", "uncommon", "rare", "epic"]),
        }

    def _generate_faction_lore(self, region: Dict[str, Any],
                               config: WorldConfig) -> Dict[str, Any]:
        """Generate lore for a faction."""
        faction_names = {
            "faction_0": "The Iron Council",
            "faction_1": "The Verdant Circle",
            "faction_2": "The Shadow Guild",
        }
        return {
            "faction": region["faction"],
            "name": faction_names.get(region["faction"], f"Faction {region['faction']}"),
            "territory_center": region["center"],
            "ideology": random.choice(["expansionist", "defensive", "mercantile", "spiritual", "technological"]),
            "symbol": random.choice(["eagle", "wolf", "dragon", "tree", "star", "moon", "sun", "crystal"]),
        }

    def _generate_npc_archetypes(self, structures: StructureData,
                                 config: WorldConfig) -> List[Dict[str, Any]]:
        """Generate NPC archetypes for the world."""
        archetypes = [
            {"role": "Quest Giver", "personality": "helpful", "location": "settlement"},
            {"role": "Merchant", "personality": "greedy", "location": "settlement"},
            {"role": "Blacksmith", "personality": "gruff", "location": "settlement"},
            {"role": "Sage", "personality": "wise", "location": "temple"},
            {"role": "Bandit Leader", "personality": "ruthless", "location": "camp"},
            {"role": "Hermit", "personality": "mysterious", "location": "cave"},
            {"role": "Guard Captain", "personality": "dutiful", "location": "fortress"},
        ]
        return archetypes

    def _generate_world_events(self, structures: StructureData,
                               config: WorldConfig) -> List[Dict[str, Any]]:
        """Generate ongoing world events."""
        events = [
            {"type": "festival", "description": "Annual harvest festival", "frequency": "yearly"},
            {"type": "invasion", "description": "Border skirmishes intensify", "frequency": "ongoing"},
            {"type": "discovery", "description": "Ancient ruins discovered", "frequency": "one-time"},
            {"type": "plague", "description": "Mysterious illness spreads", "frequency": "seasonal"},
        ]
        return events

    # -------------------------------------------------------------------------
    # World Export
    # -------------------------------------------------------------------------

    def export_world(self, terrain: TerrainData, ecosystem: EcosystemData,
                     structures: StructureData, narrative: NarrativeData) -> Dict[str, Any]:
        """Export complete world data for engine consumption."""
        world_id = uuid.uuid4().hex[:12]
        world_data = {
            "world_id": world_id,
            "terrain": terrain.to_dict(),
            "ecosystem": ecosystem.to_dict(),
            "structures": structures.to_dict(),
            "narrative": narrative.to_dict(),
            "metadata": {
                "generated_at": time.time(),
                "version": "1.0",
            },
        }
        self._worlds[world_id] = world_data
        self._stats["worlds_generated"] += 1
        return world_data

    def get_world(self, world_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a generated world by ID."""
        return self._worlds.get(world_id)

    def list_worlds(self) -> List[Dict[str, Any]]:
        """List all generated worlds."""
        return [{"world_id": wid, "theme": w.get("narrative", {}).get("theme", ""),
                 "generated_at": w.get("metadata", {}).get("generated_at", 0)}
                for wid, w in self._worlds.items()]

    def get_status(self) -> Dict[str, Any]:
        """Get synthesizer status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "worlds_generated": self._stats["worlds_generated"],
                "total_structures_placed": self._stats["total_structures_placed"],
                "total_quests_seeded": self._stats["total_quests_seeded"],
                "active_configs": len(self._configs),
                "active_terrains": len(self._terrains),
                "active_ecosystems": len(self._ecosystems),
                "active_narratives": len(self._narratives),
            }

    def shutdown(self) -> None:
        """Shutdown the synthesizer."""
        with self._lock:
            self._worlds.clear()
            self._configs.clear()
            self._terrains.clear()
            self._ecosystems.clear()
            self._structures.clear()
            self._narratives.clear()
            self._initialized = False


def get_world_synthesizer() -> AgentWorldSynthesizer:
    """Get the singleton world synthesizer instance."""
    return AgentWorldSynthesizer.get_instance()