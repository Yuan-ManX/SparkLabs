"""
SparkAI Agent - World Builder

Procedural world generation system that creates complete game worlds
from natural language descriptions. The WorldBuilder generates terrain,
environments, entity placements, biome distributions, and atmospheric
settings to produce rich, playable game worlds.

Architecture:
  WorldBuilder
    |-- TerrainGenerator (heightmaps, biomes, vegetation zones)
    |-- EnvironmentDesigner (sky, weather, lighting, atmosphere)
    |-- EntityPlacer (strategic entity placement with constraints)
    |-- StructureGenerator (buildings, dungeons, landmarks)
    |-- WorldComposer (assembles all layers into a coherent world)

World Generation Pipeline:
  Parse -> Terrain -> Environment -> Structures -> Populate -> Compose

The WorldBuilder integrates with GameContext to persist generated worlds
and with the AgentRuntime for LLM-powered creative decisions.
"""

from __future__ import annotations

import math
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class BiomeType(Enum):
    PLAINS = "plains"
    FOREST = "forest"
    DESERT = "desert"
    MOUNTAINS = "mountains"
    OCEAN = "ocean"
    SWAMP = "swamp"
    TUNDRA = "tundra"
    VOLCANIC = "volcanic"
    CAVE = "cave"
    FLOATING_ISLANDS = "floating_islands"
    CRYSTAL = "crystal"
    MUSHROOM = "mushroom"


class WorldPhase(Enum):
    IDLE = "idle"
    PARSING = "parsing"
    GENERATING_TERRAIN = "generating_terrain"
    GENERATING_ENVIRONMENT = "generating_environment"
    GENERATING_STRUCTURES = "generating_structures"
    POPULATING = "populating"
    COMPOSING = "composing"
    COMPLETED = "completed"
    FAILED = "failed"


class StructureType(Enum):
    VILLAGE = "village"
    DUNGEON = "dungeon"
    CASTLE = "castle"
    TEMPLE = "temple"
    TOWER = "tower"
    BRIDGE = "bridge"
    CAMP = "camp"
    RUINS = "ruins"
    MINE = "mine"
    PORTAL = "portal"
    SHRINE = "shrine"
    ARENA = "arena"


class WeatherType(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    SANDSTORM = "sandstorm"
    AURORA = "aurora"
    MAGICAL = "magical"


class TimeOfDay(Enum):
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"


@dataclass
class TerrainTile:
    """A single tile in the world terrain grid."""
    x: int = 0
    y: int = 0
    height: float = 0.0
    biome: BiomeType = BiomeType.PLAINS
    moisture: float = 0.5
    temperature: float = 0.5
    vegetation_density: float = 0.0
    walkable: bool = True
    resources: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "height": self.height,
            "biome": self.biome.value,
            "moisture": self.moisture,
            "temperature": self.temperature,
            "vegetation_density": self.vegetation_density,
            "walkable": self.walkable,
            "resources": self.resources,
            "tags": self.tags,
        }


@dataclass
class TerrainData:
    """Complete terrain data for a world."""
    width: int = 64
    height: int = 64
    tile_size: float = 1.0
    sea_level: float = 0.3
    tiles: List[TerrainTile] = field(default_factory=list)
    biome_distribution: Dict[str, float] = field(default_factory=dict)
    height_range: Tuple[float, float] = (0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "tile_size": self.tile_size,
            "sea_level": self.sea_level,
            "tile_count": len(self.tiles),
            "biome_distribution": self.biome_distribution,
            "height_range": list(self.height_range),
        }


@dataclass
class EnvironmentData:
    """Atmospheric and environmental settings."""
    sky_color: List[float] = field(default_factory=lambda: [0.4, 0.6, 0.9])
    fog_density: float = 0.0
    fog_color: List[float] = field(default_factory=lambda: [0.8, 0.8, 0.9])
    ambient_light: float = 0.4
    sun_direction: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.3])
    sun_intensity: float = 1.0
    weather: WeatherType = WeatherType.CLEAR
    time_of_day: TimeOfDay = TimeOfDay.NOON
    particle_effects: List[str] = field(default_factory=list)
    post_processing: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sky_color": self.sky_color,
            "fog_density": self.fog_density,
            "fog_color": self.fog_color,
            "ambient_light": self.ambient_light,
            "sun_direction": self.sun_direction,
            "sun_intensity": self.sun_intensity,
            "weather": self.weather.value,
            "time_of_day": self.time_of_day.value,
            "particle_effects": self.particle_effects,
            "post_processing": self.post_processing,
        }


@dataclass
class StructurePlacement:
    """A structure placed in the world."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    structure_type: StructureType = StructureType.VILLAGE
    name: str = ""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: float = 0.0
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    biome: BiomeType = BiomeType.PLAINS
    floors: int = 1
    rooms: int = 1
    npcs: int = 0
    loot_tier: int = 1
    connections: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "structure_type": self.structure_type.value,
            "name": self.name,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "biome": self.biome.value,
            "floors": self.floors,
            "rooms": self.rooms,
            "npcs": self.npcs,
            "loot_tier": self.loot_tier,
            "connections": self.connections,
            "tags": self.tags,
        }


@dataclass
class EntityPlacement:
    """An entity placed in the world."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str = "generic"
    name: str = ""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    spawn_rules: Dict[str, Any] = field(default_factory=dict)
    behavior: str = "idle"
    difficulty: int = 1
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "name": self.name,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "spawn_rules": self.spawn_rules,
            "behavior": self.behavior,
            "difficulty": self.difficulty,
            "tags": self.tags,
        }


@dataclass
class WorldData:
    """Complete generated world data."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    seed: int = 0
    terrain: Optional[TerrainData] = None
    environment: Optional[EnvironmentData] = None
    structures: List[StructurePlacement] = field(default_factory=list)
    entities: List[EntityPlacement] = field(default_factory=list)
    spawn_points: List[Dict[str, Any]] = field(default_factory=list)
    regions: List[Dict[str, Any]] = field(default_factory=list)
    phase: WorldPhase = WorldPhase.IDLE
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "seed": self.seed,
            "terrain": self.terrain.to_dict() if self.terrain else None,
            "environment": self.environment.to_dict() if self.environment else None,
            "structure_count": len(self.structures),
            "structures": [s.to_dict() for s in self.structures],
            "entity_count": len(self.entities),
            "entities": [e.to_dict() for e in self.entities],
            "spawn_points": self.spawn_points,
            "regions": self.regions,
            "phase": self.phase.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


_BIOME_COMPATIBILITY: Dict[BiomeType, Dict[str, Any]] = {
    BiomeType.PLAINS: {"height_range": (0.2, 0.5), "moisture": (0.3, 0.6), "temp": (0.4, 0.7), "vegetation": 0.3},
    BiomeType.FOREST: {"height_range": (0.2, 0.6), "moisture": (0.5, 0.9), "temp": (0.3, 0.7), "vegetation": 0.9},
    BiomeType.DESERT: {"height_range": (0.1, 0.5), "moisture": (0.0, 0.2), "temp": (0.7, 1.0), "vegetation": 0.05},
    BiomeType.MOUNTAINS: {"height_range": (0.6, 1.0), "moisture": (0.2, 0.5), "temp": (0.0, 0.4), "vegetation": 0.1},
    BiomeType.OCEAN: {"height_range": (0.0, 0.2), "moisture": (1.0, 1.0), "temp": (0.3, 0.8), "vegetation": 0.0},
    BiomeType.SWAMP: {"height_range": (0.15, 0.35), "moisture": (0.7, 1.0), "temp": (0.5, 0.8), "vegetation": 0.6},
    BiomeType.TUNDRA: {"height_range": (0.3, 0.7), "moisture": (0.1, 0.4), "temp": (0.0, 0.2), "vegetation": 0.1},
    BiomeType.VOLCANIC: {"height_range": (0.5, 0.9), "moisture": (0.0, 0.2), "temp": (0.8, 1.0), "vegetation": 0.0},
    BiomeType.CAVE: {"height_range": (0.0, 0.3), "moisture": (0.3, 0.6), "temp": (0.2, 0.5), "vegetation": 0.05},
    BiomeType.FLOATING_ISLANDS: {"height_range": (0.7, 1.0), "moisture": (0.4, 0.7), "temp": (0.3, 0.6), "vegetation": 0.5},
    BiomeType.CRYSTAL: {"height_range": (0.3, 0.8), "moisture": (0.1, 0.3), "temp": (0.1, 0.4), "vegetation": 0.0},
    BiomeType.MUSHROOM: {"height_range": (0.2, 0.5), "moisture": (0.6, 0.9), "temp": (0.4, 0.7), "vegetation": 0.8},
}

_STRUCTURE_BIOME_AFFINITY: Dict[StructureType, List[BiomeType]] = {
    StructureType.VILLAGE: [BiomeType.PLAINS, BiomeType.FOREST],
    StructureType.DUNGEON: [BiomeType.MOUNTAINS, BiomeType.CAVE, BiomeType.VOLCANIC],
    StructureType.CASTLE: [BiomeType.MOUNTAINS, BiomeType.PLAINS],
    StructureType.TEMPLE: [BiomeType.FOREST, BiomeType.MOUNTAINS, BiomeType.CRYSTAL],
    StructureType.TOWER: [BiomeType.PLAINS, BiomeType.MOUNTAINS, BiomeType.FLOATING_ISLANDS],
    StructureType.BRIDGE: [BiomeType.MOUNTAINS, BiomeType.SWAMP],
    StructureType.CAMP: [BiomeType.FOREST, BiomeType.PLAINS, BiomeType.DESERT],
    StructureType.RUINS: [BiomeType.DESERT, BiomeType.FOREST, BiomeType.SWAMP],
    StructureType.MINE: [BiomeType.MOUNTAINS, BiomeType.CAVE],
    StructureType.PORTAL: [BiomeType.CRYSTAL, BiomeType.FLOATING_ISLANDS, BiomeType.VOLCANIC],
    StructureType.SHRINE: [BiomeType.FOREST, BiomeType.CRYSTAL, BiomeType.MUSHROOM],
    StructureType.ARENA: [BiomeType.PLAINS, BiomeType.DESERT, BiomeType.VOLCANIC],
}

_WORLD_KEYWORDS: Dict[str, List[str]] = {
    "fantasy": ["fantasy", "magic", "wizard", "dragon", "enchant", "spell", "mythical"],
    "sci_fi": ["sci-fi", "space", "cyber", "futur", "tech", "robot", "neon", "hologram"],
    "medieval": ["medieval", "castle", "knight", "kingdom", "feudal", "sword"],
    "post_apocalyptic": ["apocalypse", "wasteland", "ruin", "survivor", "decay", "fallout"],
    "underwater": ["underwater", "ocean", "deep sea", "atlantis", "coral", "aqua"],
    "sky": ["sky", "floating", "cloud", "airship", "flying", "aerial"],
    "horror": ["dark", "haunted", "creepy", "nightmare", "undead", "cursed"],
    "prehistoric": ["dinosaur", "prehistoric", "ancient", "primitive", "jurassic", "tribe"],
}


class TerrainGenerator:
    """
    Generates terrain data including heightmaps, biome assignments,
    moisture levels, and vegetation density using procedural noise.
    """

    def generate(
        self,
        width: int = 64,
        height: int = 64,
        seed: int = 0,
        preferred_biomes: Optional[List[BiomeType]] = None,
    ) -> TerrainData:
        rng = random.Random(seed)
        terrain = TerrainData(width=width, height=height)

        height_map = self._generate_heightmap(width, height, rng)
        moisture_map = self._generate_moisture_map(width, height, rng)
        temp_map = self._generate_temperature_map(width, height, rng)

        biome_counts: Dict[str, int] = {}

        for y in range(height):
            for x in range(width):
                h = height_map[y][x]
                m = moisture_map[y][x]
                t = temp_map[y][x]

                biome = self._classify_biome(h, m, t, preferred_biomes)
                veg = self._calculate_vegetation(h, m, t, biome)

                tile = TerrainTile(
                    x=x,
                    y=y,
                    height=h,
                    biome=biome,
                    moisture=m,
                    temperature=t,
                    vegetation_density=veg,
                    walkable=h > terrain.sea_level,
                    resources=self._generate_resources(biome, rng),
                )
                terrain.tiles.append(tile)

                biome_name = biome.value
                biome_counts[biome_name] = biome_counts.get(biome_name, 0) + 1

        total = width * height
        terrain.biome_distribution = {
            name: count / total for name, count in biome_counts.items()
        }

        all_heights = [t.height for t in terrain.tiles]
        if all_heights:
            terrain.height_range = (min(all_heights), max(all_heights))

        return terrain

    def _generate_heightmap(
        self, width: int, height: int, rng: random.Random
    ) -> List[List[float]]:
        height_map = [[0.0] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                nx = x / width - 0.5
                ny = y / height - 0.5
                value = self._noise_2d(nx * 4, ny * 4, rng)
                value += 0.5 * self._noise_2d(nx * 8, ny * 8, rng)
                value += 0.25 * self._noise_2d(nx * 16, ny * 16, rng)
                value = (value + 1.0) / 3.0
                height_map[y][x] = max(0.0, min(1.0, value))
        return height_map

    def _generate_moisture_map(
        self, width: int, height: int, rng: random.Random
    ) -> List[List[float]]:
        moisture = [[0.5] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                nx = x / width - 0.5
                ny = y / height - 0.5
                value = self._noise_2d(nx * 3 + 100, ny * 3 + 100, rng)
                value += 0.5 * self._noise_2d(nx * 6 + 100, ny * 6 + 100, rng)
                value = (value + 1.5) / 3.0
                moisture[y][x] = max(0.0, min(1.0, value))
        return moisture

    def _generate_temperature_map(
        self, width: int, height: int, rng: random.Random
    ) -> List[List[float]]:
        temp = [[0.5] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                latitude_factor = 1.0 - abs(y / height - 0.5) * 2.0
                noise_val = self._noise_2d(x * 0.1 + 200, y * 0.1 + 200, rng) * 0.2
                temp[y][x] = max(0.0, min(1.0, latitude_factor + noise_val))
        return temp

    def _classify_biome(
        self,
        height: float,
        moisture: float,
        temperature: float,
        preferred: Optional[List[BiomeType]] = None,
    ) -> BiomeType:
        best_biome = BiomeType.PLAINS
        best_score = -1.0

        candidates = preferred if preferred else list(BiomeType)
        for biome in candidates:
            compat = _BIOME_COMPATIBILITY.get(biome)
            if not compat:
                continue

            h_range = compat["height_range"]
            m_range = compat["moisture"]
            t_range = compat["temp"]

            h_score = 1.0 - min(abs(height - (h_range[0] + h_range[1]) / 2) / 0.5, 1.0)
            m_score = 1.0 - min(abs(moisture - (m_range[0] + m_range[1]) / 2) / 0.5, 1.0)
            t_score = 1.0 - min(abs(temperature - (t_range[0] + t_range[1]) / 2) / 0.5, 1.0)

            in_range = (
                h_range[0] <= height <= h_range[1]
                and m_range[0] <= moisture <= m_range[1]
                and t_range[0] <= temperature <= t_range[1]
            )
            bonus = 0.3 if in_range else 0.0

            score = h_score * 0.4 + m_score * 0.35 + t_score * 0.25 + bonus
            if score > best_score:
                best_score = score
                best_biome = biome

        return best_biome

    def _calculate_vegetation(
        self,
        height: float,
        moisture: float,
        temperature: float,
        biome: BiomeType,
    ) -> float:
        compat = _BIOME_COMPATIBILITY.get(biome)
        if compat:
            return compat["vegetation"] * (0.7 + 0.3 * moisture)
        return 0.0

    def _generate_resources(
        self, biome: BiomeType, rng: random.Random
    ) -> List[str]:
        resource_map: Dict[BiomeType, List[str]] = {
            BiomeType.PLAINS: ["wood", "stone", "herb"],
            BiomeType.FOREST: ["wood", "herb", "mushroom", "fruit"],
            BiomeType.DESERT: ["sand", "cactus", "gem"],
            BiomeType.MOUNTAINS: ["stone", "iron", "gold", "crystal"],
            BiomeType.OCEAN: ["fish", "pearl", "coral"],
            BiomeType.SWAMP: ["herb", "peat", "frog"],
            BiomeType.TUNDRA: ["ice", "fur", "stone"],
            BiomeType.VOLCANIC: ["obsidian", "lava_crystal", "sulfur"],
            BiomeType.CAVE: ["crystal", "iron", "gold", "mushroom"],
            BiomeType.FLOATING_ISLANDS: ["cloud_essence", "feather", "crystal"],
            BiomeType.CRYSTAL: ["crystal", "gem", "mana_shard"],
            BiomeType.MUSHROOM: ["mushroom", "spore", "glow_cap"],
        }
        available = resource_map.get(biome, ["stone"])
        count = rng.randint(0, min(2, len(available)))
        return rng.sample(available, count) if count > 0 else []

    def _noise_2d(self, x: float, y: float, rng: random.Random) -> float:
        n = int(x * 374761393 + y * 668265263) & 0xFFFFFFFF
        rng.seed(n)
        return rng.random() * 2.0 - 1.0


class EnvironmentDesigner:
    """
    Designs atmospheric and environmental settings including
    sky, weather, lighting, and post-processing effects.
    """

    def design(
        self,
        theme: str = "fantasy",
        biome_distribution: Optional[Dict[str, float]] = None,
    ) -> EnvironmentData:
        env = EnvironmentData()

        theme_lower = theme.lower()
        if theme_lower in ("fantasy", "medieval"):
            env.sky_color = [0.3, 0.5, 0.9]
            env.ambient_light = 0.5
            env.sun_intensity = 1.0
            env.particle_effects = ["fireflies", "leaves"]
            env.post_processing = ["bloom", "vignette"]
        elif theme_lower in ("sci_fi",):
            env.sky_color = [0.05, 0.05, 0.15]
            env.ambient_light = 0.3
            env.sun_intensity = 0.8
            env.particle_effects = ["hologram_dust", "neon_rain"]
            env.post_processing = ["chromatic_aberration", "scanlines", "bloom"]
        elif theme_lower in ("horror",):
            env.sky_color = [0.1, 0.08, 0.12]
            env.ambient_light = 0.15
            env.sun_intensity = 0.3
            env.fog_density = 0.6
            env.fog_color = [0.15, 0.12, 0.18]
            env.weather = WeatherType.FOG
            env.time_of_day = TimeOfDay.NIGHT
            env.particle_effects = ["dust_motes", "embers"]
            env.post_processing = ["vignette", "grain", "color_grading"]
        elif theme_lower in ("prehistoric",):
            env.sky_color = [0.5, 0.6, 0.7]
            env.ambient_light = 0.6
            env.sun_intensity = 1.2
            env.particle_effects = ["pollen", "mist"]
            env.post_processing = ["bloom"]
        else:
            env.sky_color = [0.4, 0.6, 0.9]
            env.ambient_light = 0.4
            env.sun_intensity = 1.0

        if biome_distribution:
            if "desert" in biome_distribution and biome_distribution["desert"] > 0.3:
                env.weather = WeatherType.SANDSTORM
                env.fog_density = 0.3
                env.fog_color = [0.8, 0.7, 0.5]
                env.temperature = 0.9
            elif "tundra" in biome_distribution and biome_distribution["tundra"] > 0.3:
                env.weather = WeatherType.SNOW
                env.fog_density = 0.2
                env.fog_color = [0.9, 0.9, 0.95]
            elif "ocean" in biome_distribution and biome_distribution["ocean"] > 0.3:
                env.weather = WeatherType.RAIN
                env.fog_density = 0.15

        return env


class EntityPlacer:
    """
    Places entities strategically throughout the world based on
    biome constraints, difficulty curves, and gameplay balance.
    """

    def populate(
        self,
        terrain: TerrainData,
        entity_types: Optional[List[str]] = None,
        density: float = 0.5,
        seed: int = 0,
    ) -> List[EntityPlacement]:
        rng = random.Random(seed)
        placements: List[EntityPlacement] = []

        default_types = ["enemy", "npc", "collectible", "animal"]
        types = entity_types or default_types

        walkable_tiles = [t for t in terrain.tiles if t.walkable]
        if not walkable_tiles:
            return placements

        target_count = int(len(walkable_tiles) * density * 0.01)
        target_count = max(5, min(target_count, 200))

        rng.shuffle(walkable_tiles)

        for i in range(min(target_count, len(walkable_tiles))):
            tile = walkable_tiles[i]
            entity_type = rng.choice(types)

            placement = EntityPlacement(
                entity_type=entity_type,
                name=f"{entity_type}_{i}",
                position=[
                    tile.x * terrain.tile_size,
                    tile.height * 10.0,
                    tile.y * terrain.tile_size,
                ],
                behavior=self._default_behavior(entity_type),
                difficulty=self._calculate_difficulty(tile, entity_type),
                tags=[tile.biome.value, entity_type],
            )
            placements.append(placement)

        return placements

    def _default_behavior(self, entity_type: str) -> str:
        behavior_map = {
            "enemy": "patrol",
            "npc": "idle",
            "collectible": "static",
            "animal": "wander",
            "boss": "aggressive",
            "merchant": "idle",
        }
        return behavior_map.get(entity_type, "idle")

    def _calculate_difficulty(self, tile: TerrainTile, entity_type: str) -> int:
        base = 1
        if entity_type == "boss":
            base = 5
        elif entity_type == "enemy":
            base = 2

        height_bonus = int(tile.height * 3)
        biome_bonus = {
            "volcanic": 2, "mountains": 1, "cave": 2,
            "crystal": 1, "floating_islands": 1,
        }.get(tile.biome.value, 0)

        return min(base + height_bonus + biome_bonus, 10)


class StructureGenerator:
    """
    Generates and places structures in the world based on
    biome compatibility and world theme.
    """

    def generate(
        self,
        terrain: TerrainData,
        theme: str = "fantasy",
        structure_count: int = 5,
        seed: int = 0,
    ) -> List[StructurePlacement]:
        rng = random.Random(seed)
        structures: List[StructurePlacement] = []

        biome_tiles: Dict[BiomeType, List[TerrainTile]] = {}
        for tile in terrain.tiles:
            if tile.walkable:
                if tile.biome not in biome_tiles:
                    biome_tiles[tile.biome] = []
                biome_tiles[tile.biome].append(tile)

        theme_structures = self._get_theme_structures(theme)

        for i in range(structure_count):
            struct_type = rng.choice(theme_structures)
            compatible_biomes = _STRUCTURE_BIOME_AFFINITY.get(struct_type, [BiomeType.PLAINS])

            available_biomes = [b for b in compatible_biomes if b in biome_tiles and biome_tiles[b]]
            if not available_biomes:
                available_biomes = list(biome_tiles.keys())

            if not available_biomes:
                continue

            chosen_biome = rng.choice(available_biomes)
            tile = rng.choice(biome_tiles[chosen_biome])

            structure = StructurePlacement(
                structure_type=struct_type,
                name=f"{struct_type.value}_{i}",
                position=[
                    tile.x * terrain.tile_size,
                    tile.height * 10.0,
                    tile.y * terrain.tile_size,
                ],
                biome=chosen_biome,
                floors=rng.randint(1, 3),
                rooms=rng.randint(2, 8),
                npcs=rng.randint(0, 5),
                loot_tier=rng.randint(1, 5),
                tags=[theme, struct_type.value, chosen_biome.value],
            )
            structures.append(structure)

        return structures

    def _get_theme_structures(self, theme: str) -> List[StructureType]:
        theme_map: Dict[str, List[StructureType]] = {
            "fantasy": [
                StructureType.VILLAGE, StructureType.DUNGEON,
                StructureType.CASTLE, StructureType.TEMPLE,
                StructureType.TOWER, StructureType.SHRINE,
            ],
            "sci_fi": [
                StructureType.TOWER, StructureType.PORTAL,
                StructureType.RUINS, StructureType.CAMP,
                StructureType.MINE,
            ],
            "medieval": [
                StructureType.VILLAGE, StructureType.CASTLE,
                StructureType.TOWER, StructureType.BRIDGE,
                StructureType.TEMPLE, StructureType.MINE,
            ],
            "post_apocalyptic": [
                StructureType.RUINS, StructureType.CAMP,
                StructureType.MINE, StructureType.TOWER,
            ],
            "horror": [
                StructureType.DUNGEON, StructureType.RUINS,
                StructureType.SHRINE, StructureType.MINE,
            ],
        }
        return theme_map.get(theme.lower(), [
            StructureType.VILLAGE, StructureType.DUNGEON,
            StructureType.TOWER, StructureType.TEMPLE,
        ])


class WorldComposer:
    """
    Assembles all world generation layers into a coherent,
    playable game world with spawn points and regions.
    """

    def compose(
        self,
        terrain: TerrainData,
        environment: EnvironmentData,
        structures: List[StructurePlacement],
        entities: List[EntityPlacement],
        world_name: str = "",
        description: str = "",
    ) -> WorldData:
        world = WorldData(
            name=world_name or "Generated World",
            description=description,
            terrain=terrain,
            environment=environment,
            structures=structures,
            entities=entities,
        )

        world.spawn_points = self._generate_spawn_points(terrain, structures)
        world.regions = self._define_regions(terrain, structures)

        return world

    def _generate_spawn_points(
        self,
        terrain: TerrainData,
        structures: List[StructurePlacement],
    ) -> List[Dict[str, Any]]:
        spawns: List[Dict[str, Any]] = []

        plains_tiles = [t for t in terrain.tiles if t.biome == BiomeType.PLAINS and t.walkable]
        if plains_tiles:
            center = plains_tiles[len(plains_tiles) // 2]
            spawns.append({
                "id": str(uuid.uuid4()),
                "name": "Player Start",
                "position": [center.x * terrain.tile_size, center.height * 10.0, center.y * terrain.tile_size],
                "type": "player_start",
                "is_default": True,
            })

        for struct in structures:
            if struct.structure_type in (StructureType.VILLAGE, StructureType.CAMP):
                spawns.append({
                    "id": str(uuid.uuid4()),
                    "name": f"Spawn near {struct.name}",
                    "position": struct.position,
                    "type": "checkpoint",
                    "is_default": False,
                })

        if not spawns:
            walkable = [t for t in terrain.tiles if t.walkable]
            if walkable:
                tile = walkable[len(walkable) // 2]
                spawns.append({
                    "id": str(uuid.uuid4()),
                    "name": "Default Spawn",
                    "position": [tile.x * terrain.tile_size, tile.height * 10.0, tile.y * terrain.tile_size],
                    "type": "player_start",
                    "is_default": True,
                })

        return spawns

    def _define_regions(
        self,
        terrain: TerrainData,
        structures: List[StructurePlacement],
    ) -> List[Dict[str, Any]]:
        regions: List[Dict[str, Any]] = []

        biome_groups: Dict[str, List[TerrainTile]] = {}
        for tile in terrain.tiles:
            if tile.walkable:
                biome_groups.setdefault(tile.biome.value, []).append(tile)

        for biome_name, tiles in biome_groups.items():
            if not tiles:
                continue

            min_x = min(t.x for t in tiles)
            max_x = max(t.x for t in tiles)
            min_y = min(t.y for t in tiles)
            max_y = max(t.y for t in tiles)

            struct_in_region = [
                s for s in structures
                if s.biome.value == biome_name
            ]

            region = {
                "id": str(uuid.uuid4()),
                "name": f"{biome_name.title()} Region",
                "biome": biome_name,
                "bounds": {
                    "min_x": min_x, "max_x": max_x,
                    "min_y": min_y, "max_y": max_y,
                },
                "tile_count": len(tiles),
                "structure_count": len(struct_in_region),
                "difficulty_range": [1, 5],
                "discovered": False,
            }
            regions.append(region)

        return regions


class WorldBuilder:
    """
    Procedural world generation system for the SparkLabs AI-Native Game Engine.

    Transforms natural language world descriptions into complete, playable
    game worlds through a multi-phase generation pipeline:

    1. Parse: Extract world theme, biomes, and features from prompt
    2. Terrain: Generate heightmaps, biomes, and vegetation
    3. Environment: Design sky, weather, and atmosphere
    4. Structures: Place buildings, dungeons, and landmarks
    5. Populate: Spawn entities with strategic placement
    6. Compose: Assemble all layers into a coherent world

    Usage:
        builder = WorldBuilder()
        world = await builder.build("A fantasy world with mountains and forests")
        print(world.to_dict())
    """

    def __init__(self):
        self._terrain_gen = TerrainGenerator()
        self._env_designer = EnvironmentDesigner()
        self._entity_placer = EntityPlacer()
        self._structure_gen = StructureGenerator()
        self._composer = WorldComposer()

        self._worlds: Dict[str, WorldData] = {}
        self._build_count: int = 0
        self._total_entities_placed: int = 0
        self._total_structures_placed: int = 0

    async def build(
        self,
        prompt: str,
        world_name: str = "",
        width: int = 64,
        height: int = 64,
        seed: Optional[int] = None,
        entity_density: float = 0.5,
        structure_count: int = 5,
    ) -> WorldData:
        """
        Build a complete world from a natural language description.
        """
        if seed is None:
            seed = int(time.time() * 1000) % (2**31)

        world = WorldData(
            name=world_name or "Generated World",
            description=prompt,
            seed=seed,
        )

        try:
            world.phase = WorldPhase.PARSING
            theme = self._parse_theme(prompt)
            preferred_biomes = self._parse_biomes(prompt)

            world.phase = WorldPhase.GENERATING_TERRAIN
            world.terrain = self._terrain_gen.generate(
                width=width,
                height=height,
                seed=seed,
                preferred_biomes=preferred_biomes,
            )

            world.phase = WorldPhase.GENERATING_ENVIRONMENT
            world.environment = self._env_designer.design(
                theme=theme,
                biome_distribution=world.terrain.biome_distribution,
            )

            world.phase = WorldPhase.GENERATING_STRUCTURES
            world.structures = self._structure_gen.generate(
                terrain=world.terrain,
                theme=theme,
                structure_count=structure_count,
                seed=seed + 1,
            )
            self._total_structures_placed += len(world.structures)

            world.phase = WorldPhase.POPULATING
            entity_types = self._parse_entity_types(prompt, theme)
            world.entities = self._entity_placer.populate(
                terrain=world.terrain,
                entity_types=entity_types,
                density=entity_density,
                seed=seed + 2,
            )
            self._total_entities_placed += len(world.entities)

            world.phase = WorldPhase.COMPOSING
            world = self._composer.compose(
                terrain=world.terrain,
                environment=world.environment,
                structures=world.structures,
                entities=world.entities,
                world_name=world_name,
                description=prompt,
            )

            world.phase = WorldPhase.COMPLETED
            world.completed_at = time.time()
            self._build_count += 1
            self._worlds[world.id] = world

        except Exception:
            world.phase = WorldPhase.FAILED
            world.completed_at = time.time()

        return world

    def get_world(self, world_id: str) -> Optional[WorldData]:
        return self._worlds.get(world_id)

    def list_worlds(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": w.id,
                "name": w.name,
                "phase": w.phase.value,
                "seed": w.seed,
                "entity_count": len(w.entities),
                "structure_count": len(w.structures),
                "region_count": len(w.regions),
                "created_at": w.created_at,
            }
            for w in self._worlds.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_worlds": len(self._worlds),
            "build_count": self._build_count,
            "total_entities_placed": self._total_entities_placed,
            "total_structures_placed": self._total_structures_placed,
            "avg_entities_per_world": (
                self._total_entities_placed / max(self._build_count, 1)
            ),
            "avg_structures_per_world": (
                self._total_structures_placed / max(self._build_count, 1)
            ),
        }

    def _parse_theme(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        for theme, keywords in _WORLD_KEYWORDS.items():
            if any(kw in prompt_lower for kw in keywords):
                return theme
        return "fantasy"

    def _parse_biomes(self, prompt: str) -> List[BiomeType]:
        prompt_lower = prompt.lower()
        biome_keywords: Dict[BiomeType, List[str]] = {
            BiomeType.FOREST: ["forest", "wood", "tree", "jungle"],
            BiomeType.DESERT: ["desert", "sand", "arid", "dune"],
            BiomeType.MOUNTAINS: ["mountain", "peak", "hill", "highland"],
            BiomeType.OCEAN: ["ocean", "sea", "water", "island"],
            BiomeType.SWAMP: ["swamp", "marsh", "bog", "wetland"],
            BiomeType.TUNDRA: ["tundra", "ice", "snow", "frozen", "arctic"],
            BiomeType.VOLCANIC: ["volcano", "lava", "magma", "fire"],
            BiomeType.CAVE: ["cave", "underground", "dungeon", "cavern"],
            BiomeType.FLOATING_ISLANDS: ["floating", "sky", "cloud", "aerial"],
            BiomeType.CRYSTAL: ["crystal", "gem", "prism"],
            BiomeType.MUSHROOM: ["mushroom", "fungus", "spore"],
        }

        biomes: List[BiomeType] = []
        for biome, keywords in biome_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                biomes.append(biome)

        if not biomes:
            biomes = [BiomeType.PLAINS, BiomeType.FOREST]

        return biomes

    def _parse_entity_types(self, prompt: str, theme: str) -> List[str]:
        prompt_lower = prompt.lower()
        types = ["enemy", "npc", "collectible"]

        if "boss" in prompt_lower:
            types.append("boss")
        if "merchant" in prompt_lower or "shop" in prompt_lower:
            types.append("merchant")
        if "animal" in prompt_lower or "creature" in prompt_lower:
            types.append("animal")

        if theme == "sci_fi":
            types = [t.replace("enemy", "robot") if t == "enemy" else t for t in types]
        elif theme == "horror":
            types = [t.replace("enemy", "undead") if t == "enemy" else t for t in types]
        elif theme == "prehistoric":
            types = [t.replace("enemy", "dinosaur") if t == "enemy" else t for t in types]

        return types


_global_builder: Optional[WorldBuilder] = None


def get_world_builder() -> WorldBuilder:
    """Get the global WorldBuilder singleton."""
    global _global_builder
    if _global_builder is None:
        _global_builder = WorldBuilder()
    return _global_builder


def reset_world_builder() -> None:
    """Reset the global WorldBuilder singleton."""
    global _global_builder
    _global_builder = None
