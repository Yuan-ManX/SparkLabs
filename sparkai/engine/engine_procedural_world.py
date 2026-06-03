"""
SparkLabs Engine - Procedural World Generator

Procedural world generation system for the SparkLabs AI-native
game engine. Generates diverse game worlds including terrains,
biomes, settlements, dungeons, and ecosystems using layered
procedural algorithms.

Architecture:
  EngineProceduralWorld (Singleton)
    |-- Terrain Generator (heightmap-based terrain synthesis)
    |-- Biome Distributor (climate-driven biome placement)
    |-- Settlement Planner (procedural city/village layout)
    |-- Dungeon Forge (room-and-corridor dungeon generation)
    |-- Ecosystem Builder (flora/fauna distribution)
    |-- Road Network (path-based connectivity between regions)
    |-- World Composer (orchestrate all layers into coherent world)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set


class TerrainType(Enum):
    OCEAN = "ocean"
    BEACH = "beach"
    PLAINS = "plains"
    FOREST = "forest"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    SNOW_PEAKS = "snow_peaks"
    DESERT = "desert"
    SWAMP = "swamp"
    TUNDRA = "tundra"
    VOLCANIC = "volcanic"
    RIVER = "river"


class BiomeType(Enum):
    TROPICAL_RAINFOREST = "tropical_rainforest"
    TEMPERATE_FOREST = "temperate_forest"
    BOREAL_FOREST = "boreal_forest"
    SAVANNA = "savanna"
    GRASSLAND = "grassland"
    DESERT = "desert"
    TUNDRA = "tundra"
    MEDITERRANEAN = "mediterranean"
    ALPINE = "alpine"
    WETLAND = "wetland"
    COASTAL = "coastal"


class SettlementType(Enum):
    HAMLET = "hamlet"
    VILLAGE = "village"
    TOWN = "town"
    CITY = "city"
    FORTRESS = "fortress"
    RUINS = "ruins"
    CAMP = "camp"
    OUTPOST = "outpost"


class DungeonStyle(Enum):
    CAVE = "cave"
    RUIN = "ruin"
    DUNGEON = "dungeon"
    TEMPLE = "temple"
    FORTRESS = "fortress"
    MINES = "mines"
    CRYPT = "crypt"
    LABYRINTH = "labyrinth"


class GenerationAlgorithm(Enum):
    PERLIN_NOISE = "perlin_noise"
    SIMPLEX_NOISE = "simplex_noise"
    VORONOI = "voronoi"
    DIAMOND_SQUARE = "diamond_square"
    CELLULAR_AUTOMATA = "cellular_automata"
    BSP = "bsp"
    WAVE_FUNCTION = "wave_function"
    L_SYSTEM = "l_system"


@dataclass
class WorldConfig:
    """Configuration for procedural world generation."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_name: str = "Generated World"
    seed: int = 0
    world_width: int = 256
    world_height: int = 256
    tile_size: int = 32
    ocean_level: float = 0.3
    mountain_level: float = 0.7
    biome_count: int = 4
    settlement_count: int = 8
    dungeon_count: int = 5
    road_density: float = 0.3
    forest_density: float = 0.4
    river_count: int = 3
    climate_temperature: float = 0.5  # 0 = cold, 1 = hot
    climate_humidity: float = 0.5  # 0 = dry, 1 = wet
    algorithm: GenerationAlgorithm = GenerationAlgorithm.SIMPLEX_NOISE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "world_name": self.world_name,
            "seed": self.seed,
            "world_width": self.world_width,
            "world_height": self.world_height,
            "tile_size": self.tile_size,
            "ocean_level": self.ocean_level,
            "mountain_level": self.mountain_level,
            "biome_count": self.biome_count,
            "settlement_count": self.settlement_count,
            "dungeon_count": self.dungeon_count,
            "road_density": self.road_density,
            "forest_density": self.forest_density,
            "river_count": self.river_count,
            "climate_temperature": self.climate_temperature,
            "climate_humidity": self.climate_humidity,
            "algorithm": self.algorithm.value,
        }


@dataclass
class WorldTile:
    """Single tile in the generated world."""
    x: int = 0
    y: int = 0
    terrain_type: TerrainType = TerrainType.PLAINS
    biome_type: BiomeType = BiomeType.GRASSLAND
    elevation: float = 0.0
    moisture: float = 0.0
    temperature: float = 0.5
    is_water: bool = False
    has_road: bool = False
    has_structure: bool = False
    structure_id: str = ""
    decoration_density: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x, "y": self.y,
            "terrain_type": self.terrain_type.value,
            "biome_type": self.biome_type.value,
            "elevation": self.elevation,
            "moisture": self.moisture,
            "temperature": self.temperature,
            "is_water": self.is_water,
            "has_road": self.has_road,
            "has_structure": self.has_structure,
            "structure_id": self.structure_id,
        }


@dataclass
class GeneratedStructure:
    """A structure placed in the world."""
    structure_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    structure_type: str = ""
    x: int = 0
    y: int = 0
    width: int = 1
    height: int = 1
    name: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structure_id": self.structure_id,
            "structure_type": self.structure_type,
            "x": self.x, "y": self.y,
            "width": self.width,
            "height": self.height,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
        }


@dataclass
class GeneratedDungeon:
    """A procedurally generated dungeon."""
    dungeon_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    style: DungeonStyle = DungeonStyle.DUNGEON
    world_x: int = 0
    world_y: int = 0
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    corridors: List[Dict[str, Any]] = field(default_factory=list)
    total_rooms: int = 0
    total_area: int = 0
    difficulty: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dungeon_id": self.dungeon_id,
            "name": self.name,
            "style": self.style.value,
            "world_x": self.world_x,
            "world_y": self.world_y,
            "rooms": self.rooms,
            "corridors": self.corridors,
            "total_rooms": self.total_rooms,
            "total_area": self.total_area,
            "difficulty": self.difficulty,
        }


@dataclass
class GeneratedWorld:
    """Complete generated world result."""
    world_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config: WorldConfig = field(default_factory=WorldConfig)
    tiles: List[List[WorldTile]] = field(default_factory=list)
    structures: List[GeneratedStructure] = field(default_factory=list)
    dungeons: List[GeneratedDungeon] = field(default_factory=list)
    spawn_points: List[Dict[str, int]] = field(default_factory=list)
    poi_list: List[Dict[str, Any]] = field(default_factory=list)
    generation_time: float = 0.0
    world_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_id": self.world_id,
            "config": self.config.to_dict(),
            "structure_count": len(self.structures),
            "dungeon_count": len(self.dungeons),
            "spawn_points": self.spawn_points,
            "poi_list": self.poi_list,
            "generation_time": self.generation_time,
            "world_stats": self.world_stats,
        }


class EngineProceduralWorld:
    """
    Procedural world generation engine.

    Generates complete game worlds using layered procedural algorithms
    including terrain synthesis, biome distribution, settlement placement,
    dungeon generation, and ecosystem building.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._worlds: Dict[str, GeneratedWorld] = {}
        self._total_generated: int = 0
        self._default_config: WorldConfig = WorldConfig()

    @classmethod
    def get_instance(cls) -> "EngineProceduralWorld":
        return cls()

    # ---- World Generation ----

    def generate_world(
        self,
        config: Optional[WorldConfig] = None,
        name: str = "",
    ) -> GeneratedWorld:
        """
        Generate a complete procedural world.

        Orchestrates all generation layers: terrain, biomes, rivers,
        structures, dungeons, roads, and ecosystems.
        """
        cfg = config or self._default_config
        if name:
            cfg.world_name = name

        start_time = _time_module.time()

        # Set random seed
        if cfg.seed:
            random.seed(cfg.seed)

        # Layer 1: Terrain heightmap
        heightmap = self._generate_heightmap(cfg)

        # Layer 2: Moisture and temperature maps
        moisture_map = self._generate_moisture_map(cfg, heightmap)
        temperature_map = self._generate_temperature_map(cfg, heightmap)

        # Layer 3: Tile grid from heightmap
        tiles = self._build_tile_grid(cfg, heightmap, moisture_map, temperature_map)

        # Layer 4: Rivers
        self._generate_rivers(cfg, tiles, heightmap)

        # Layer 5: Biomes
        self._assign_biomes(cfg, tiles)

        # Layer 6: Structures and settlements
        structures = self._generate_settlements(cfg, tiles)

        # Layer 7: Dungeons
        dungeons = self._generate_dungeons(cfg, tiles)

        # Layer 8: Road network
        self._generate_road_network(cfg, tiles, structures)

        # Layer 9: Spawn points and POIs
        spawn_points = self._find_spawn_points(tiles, structures)
        poi_list = self._collect_pois(structures, dungeons)

        generation_time = _time_module.time() - start_time

        world = GeneratedWorld(
            config=cfg,
            tiles=tiles,
            structures=structures,
            dungeons=dungeons,
            spawn_points=spawn_points,
            poi_list=poi_list,
            generation_time=generation_time,
            world_stats=self._compute_world_stats(cfg, tiles),
        )
        self._worlds[world.world_id] = world
        self._total_generated += 1

        return world

    # ---- Heightmap Generation ----

    def _generate_heightmap(self, cfg: WorldConfig) -> List[List[float]]:
        """Generate terrain heightmap using simplex noise."""
        w, h = cfg.world_width, cfg.world_height
        heightmap = [[0.0 for _ in range(w)] for _ in range(h)]

        for y in range(h):
            for x in range(w):
                # Multi-octave simplex-like noise
                nx = x / w - 0.5
                ny = y / h - 0.5
                e = self._simplex_noise(nx * 4, ny * 4, 0)
                e += 0.5 * self._simplex_noise(nx * 8, ny * 8, 1)
                e += 0.25 * self._simplex_noise(nx * 16, ny * 16, 2)
                e += 0.125 * self._simplex_noise(nx * 32, ny * 32, 3)
                e /= 1.875  # Normalize
                heightmap[y][x] = (e + 1.0) / 2.0  # Map to [0, 1]

        return heightmap

    def _generate_moisture_map(
        self, cfg: WorldConfig, heightmap: List[List[float]],
    ) -> List[List[float]]:
        """Generate moisture distribution."""
        w, h = cfg.world_width, cfg.world_height
        moisture = [[0.0 for _ in range(w)] for _ in range(h)]

        for y in range(h):
            for x in range(w):
                nx = x / w - 0.5
                ny = y / h - 0.5
                m = self._simplex_noise(nx * 3 + 1.5, ny * 3 + 1.5, 5)
                m = (m + 1.0) / 2.0
                # Elevation affects moisture
                m *= (1.0 - heightmap[y][x] * 0.5)
                moisture[y][x] = max(0.0, min(1.0, m))

        return moisture

    def _generate_temperature_map(
        self, cfg: WorldConfig, heightmap: List[List[float]],
    ) -> List[List[float]]:
        """Generate temperature distribution."""
        w, h = cfg.world_width, cfg.world_height
        temperature = [[0.0 for _ in range(w)] for _ in range(h)]

        for y in range(h):
            for x in range(w):
                # Latitude-based temperature
                lat_factor = 1.0 - abs(y / h - 0.5) * 2.0
                # Elevation cooling
                elev_factor = 1.0 - heightmap[y][x] * 0.6
                # Noise
                noise = self._simplex_noise(x / w * 2, y / h * 2, 6)
                temp = lat_factor * elev_factor * 0.8 + (noise + 1.0) / 2.0 * 0.2
                temperature[y][x] = max(0.0, min(1.0, temp))

        return temperature

    # ---- Simplex Noise (Simplified) ----

    def _simplex_noise(self, x: float, y: float, seed: int) -> float:
        """Simplified simplex-like noise function."""
        # Using a hash-based approximation
        def _hash(xi: int, yi: int) -> float:
            n = (xi * 374761393 + yi * 668265263 + seed * 174440041) & 0x7FFFFFFF
            return (n % 10000) / 10000.0

        xi = int(math.floor(x))
        yi = int(math.floor(y))
        xf = x - xi
        yf = y - yi

        # Smoothstep
        u = xf * xf * (3.0 - 2.0 * xf)
        v = yf * yf * (3.0 - 2.0 * yf)

        # Bilinear interpolation
        aa = _hash(xi, yi)
        ba = _hash(xi + 1, yi)
        ab = _hash(xi, yi + 1)
        bb = _hash(xi + 1, yi + 1)

        return (aa * (1 - u) + ba * u) * (1 - v) + (ab * (1 - u) + bb * u) * v

    # ---- Tile Grid Building ----

    def _build_tile_grid(
        self,
        cfg: WorldConfig,
        heightmap: List[List[float]],
        moisture: List[List[float]],
        temperature: List[List[float]],
    ) -> List[List[WorldTile]]:
        """Build tile grid from generated maps."""
        w, h = cfg.world_width, cfg.world_height
        tiles = [[WorldTile(x=x, y=y) for x in range(w)] for y in range(h)]

        for y in range(h):
            for x in range(w):
                tile = tiles[y][x]
                e = heightmap[y][x]
                tile.elevation = e
                tile.moisture = moisture[y][x]
                tile.temperature = temperature[y][x]

                # Determine terrain type
                if e < cfg.ocean_level:
                    tile.terrain_type = TerrainType.OCEAN
                    tile.is_water = True
                elif e < cfg.ocean_level + 0.03:
                    tile.terrain_type = TerrainType.BEACH
                elif e < cfg.ocean_level + 0.1:
                    tile.terrain_type = TerrainType.PLAINS
                elif e < cfg.ocean_level + 0.2:
                    tile.terrain_type = TerrainType.FOREST if moisture[y][x] > 0.4 else TerrainType.PLAINS
                elif e < cfg.mountain_level - 0.1:
                    tile.terrain_type = TerrainType.HILLS
                elif e < cfg.mountain_level:
                    tile.terrain_type = TerrainType.MOUNTAINS
                else:
                    tile.terrain_type = TerrainType.SNOW_PEAKS

                # Special terrains
                if moisture[y][x] > 0.7 and e < cfg.ocean_level + 0.1:
                    tile.terrain_type = TerrainType.SWAMP
                if temperature[y][x] > 0.7 and moisture[y][x] < 0.3 and e < cfg.ocean_level + 0.15:
                    tile.terrain_type = TerrainType.DESERT

        return tiles

    # ---- River Generation ----

    def _generate_rivers(
        self,
        cfg: WorldConfig,
        tiles: List[List[WorldTile]],
        heightmap: List[List[float]],
    ) -> None:
        """Generate river systems flowing from high to low elevation."""
        w, h = cfg.world_width, cfg.world_height

        for _ in range(cfg.river_count):
            # Find a high-elevation start point
            attempts = 0
            while attempts < 50:
                sx = random.randint(0, w - 1)
                sy = random.randint(0, h - 1)
                if heightmap[sy][sx] > cfg.mountain_level - 0.05:
                    break
                attempts += 1
            else:
                continue

            # Flow downhill
            cx, cy = sx, sy
            for _ in range(w + h):
                if heightmap[cy][cx] < cfg.ocean_level + 0.02:
                    break

                if 0 <= cx < w and 0 <= cy < h:
                    tile = tiles[cy][cx]
                    if not tile.is_water:
                        tile.terrain_type = TerrainType.RIVER
                        tile.is_water = True

                # Find lowest neighbor
                neighbors = []
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        neighbors.append((heightmap[ny][nx], nx, ny))

                if not neighbors:
                    break
                neighbors.sort(key=lambda n: n[0])
                _, cx, cy = neighbors[0]

    # ---- Biome Assignment ----

    def _assign_biomes(self, cfg: WorldConfig, tiles: List[List[WorldTile]]) -> None:
        """Assign biome types based on temperature and moisture."""
        for row in tiles:
            for tile in row:
                if tile.is_water and tile.terrain_type != TerrainType.RIVER:
                    tile.biome_type = BiomeType.COASTAL
                    continue

                t = tile.temperature
                m = tile.moisture

                if t > 0.7:
                    if m > 0.6:
                        tile.biome_type = BiomeType.TROPICAL_RAINFOREST
                    elif m > 0.3:
                        tile.biome_type = BiomeType.SAVANNA
                    else:
                        tile.biome_type = BiomeType.DESERT
                elif t > 0.4:
                    if m > 0.5:
                        tile.biome_type = BiomeType.TEMPERATE_FOREST
                    elif m > 0.2:
                        tile.biome_type = BiomeType.GRASSLAND
                    else:
                        tile.biome_type = BiomeType.MEDITERRANEAN
                else:
                    if m > 0.4:
                        tile.biome_type = BiomeType.BOREAL_FOREST
                    else:
                        tile.biome_type = BiomeType.TUNDRA

                if tile.elevation > cfg.mountain_level:
                    tile.biome_type = BiomeType.ALPINE

    # ---- Settlement Generation ----

    def _generate_settlements(
        self, cfg: WorldConfig, tiles: List[List[WorldTile]],
    ) -> List[GeneratedStructure]:
        """Place settlements on suitable terrain."""
        structures: List[GeneratedStructure] = []
        w, h = cfg.world_width, cfg.world_height

        settlement_names = [
            "Oakhaven", "Stonebridge", "Riverdale", "Hillcrest",
            "Shadowfen", "Goldcrest", "Ironforge", "Silverwood",
            "Thornwall", "Brightwater", "Darkmoor", "Windfell",
        ]

        for i in range(cfg.settlement_count):
            attempts = 0
            while attempts < 100:
                sx = random.randint(5, w - 6)
                sy = random.randint(5, h - 6)
                tile = tiles[sy][sx]

                if tile.terrain_type in (
                    TerrainType.PLAINS, TerrainType.FOREST,
                    TerrainType.HILLS,
                ) and not tile.is_water:
                    # Check if area is clear
                    populated = any(
                        abs(s.x - sx) < 10 and abs(s.y - sy) < 10
                        for s in structures
                    )
                    if not populated:
                        break
                attempts += 1
            else:
                continue

            # Determine settlement type
            if i < cfg.settlement_count // 4:
                s_type = SettlementType.CITY.value
                size = 3
            elif i < cfg.settlement_count // 2:
                s_type = SettlementType.TOWN.value
                size = 2
            else:
                s_type = SettlementType.VILLAGE.value
                size = 1

            structure = GeneratedStructure(
                structure_type=s_type,
                x=sx, y=sy,
                width=size, height=size,
                name=settlement_names[i % len(settlement_names)],
                description=f"A {s_type} located in the {tile.biome_type.value}",
                properties={"population": random.randint(10 * size, 100 * size)},
            )
            structures.append(structure)

            # Mark tiles as having structures
            for dy in range(-size, size + 1):
                for dx in range(-size, size + 1):
                    nx, ny = sx + dx, sy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        tiles[ny][nx].has_structure = True
                        tiles[ny][nx].structure_id = structure.structure_id

        return structures

    # ---- Dungeon Generation ----

    def _generate_dungeons(
        self, cfg: WorldConfig, tiles: List[List[WorldTile]],
    ) -> List[GeneratedDungeon]:
        """Generate dungeons on suitable terrain."""
        dungeons: List[GeneratedDungeon] = []
        w, h = cfg.world_width, cfg.world_height

        styles = list(DungeonStyle)

        for i in range(cfg.dungeon_count):
            attempts = 0
            while attempts < 100:
                dx = random.randint(5, w - 6)
                dy = random.randint(5, h - 6)
                tile = tiles[dy][dx]

                if tile.terrain_type in (
                    TerrainType.HILLS, TerrainType.MOUNTAINS,
                    TerrainType.FOREST, TerrainType.SWAMP,
                ):
                    break
                attempts += 1
            else:
                continue

            # Generate dungeon rooms
            num_rooms = random.randint(5, 15)
            rooms = self._generate_dungeon_rooms(num_rooms, 30, 30)
            corridors = self._generate_dungeon_corridors(rooms)
            total_area = sum(r["width"] * r["height"] for r in rooms)

            dungeon = GeneratedDungeon(
                name=f"{styles[i % len(styles)].value.capitalize()} of the Depths",
                style=styles[i % len(styles)],
                world_x=dx,
                world_y=dy,
                rooms=rooms,
                corridors=corridors,
                total_rooms=len(rooms),
                total_area=total_area,
                difficulty=0.3 + random.random() * 0.7,
            )
            dungeons.append(dungeon)

        return dungeons

    def _generate_dungeon_rooms(
        self, num_rooms: int, max_w: int, max_h: int,
    ) -> List[Dict[str, Any]]:
        """Generate rooms using BSP-like partitioning."""
        rooms = []
        for _ in range(num_rooms):
            rw = random.randint(3, max(4, max_w // 3))
            rh = random.randint(3, max(4, max_h // 3))
            rx = random.randint(0, max_w - rw)
            ry = random.randint(0, max_h - rh)
            rooms.append({
                "x": rx, "y": ry,
                "width": rw, "height": rh,
                "center_x": rx + rw // 2,
                "center_y": ry + rh // 2,
                "type": random.choice(["entrance", "treasure", "boss", "normal", "puzzle"]),
            })
        return rooms

    def _generate_dungeon_corridors(
        self, rooms: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate corridors connecting rooms."""
        corridors = []
        for i in range(len(rooms) - 1):
            r1 = rooms[i]
            r2 = rooms[i + 1]
            corridors.append({
                "from_x": r1["center_x"],
                "from_y": r1["center_y"],
                "to_x": r2["center_x"],
                "to_y": r2["center_y"],
                "width": 1,
            })
        return corridors

    # ---- Road Network ----

    def _generate_road_network(
        self,
        cfg: WorldConfig,
        tiles: List[List[WorldTile]],
        structures: List[GeneratedStructure],
    ) -> None:
        """Generate roads connecting settlements."""
        if len(structures) < 2:
            return

        w, h = cfg.world_width, cfg.world_height

        # Sort structures by proximity to create a spanning network
        connected = {structures[0].structure_id}
        for _ in range(len(structures) - 1):
            best_dist = float("inf")
            best_a, best_b = None, None

            for sa in structures:
                for sb in structures:
                    if sa.structure_id == sb.structure_id:
                        continue
                    if (sa.structure_id in connected) == (sb.structure_id in connected):
                        continue

                    dist = abs(sa.x - sb.x) + abs(sa.y - sb.y)
                    if dist < best_dist:
                        best_dist = dist
                        best_a, best_b = sa, sb

            if best_a and best_b:
                self._draw_road(tiles, best_a.x, best_a.y, best_b.x, best_b.y, w, h)
                connected.add(best_a.structure_id)
                connected.add(best_b.structure_id)

    def _draw_road(
        self, tiles: List[List[WorldTile]],
        x1: int, y1: int, x2: int, y2: int,
        w: int, h: int,
    ) -> None:
        """Draw a simple road between two points."""
        cx, cy = x1, y1
        while cx != x2 or cy != y2:
            if 0 <= cx < w and 0 <= cy < h:
                if not tiles[cy][cx].is_water:
                    tiles[cy][cx].has_road = True
            if abs(cx - x2) > abs(cy - y2):
                cx += 1 if cx < x2 else -1
            else:
                cy += 1 if cy < y2 else -1

    # ---- Spawn Points and POIs ----

    def _find_spawn_points(
        self,
        tiles: List[List[WorldTile]],
        structures: List[GeneratedStructure],
    ) -> List[Dict[str, int]]:
        """Find suitable spawn points near settlements."""
        w = len(tiles[0]) if tiles else 0
        h = len(tiles)

        spawns = []
        for s in structures[:3]:
            spawns.append({"x": s.x, "y": s.y + 2})

        if not spawns and w > 0 and h > 0:
            spawns.append({"x": w // 2, "y": h // 2})

        return spawns

    def _collect_pois(
        self,
        structures: List[GeneratedStructure],
        dungeons: List[GeneratedDungeon],
    ) -> List[Dict[str, Any]]:
        """Collect all points of interest."""
        pois = []
        for s in structures:
            pois.append({
                "type": s.structure_type,
                "name": s.name,
                "x": s.x, "y": s.y,
                "id": s.structure_id,
            })
        for d in dungeons:
            pois.append({
                "type": "dungeon",
                "name": d.name,
                "x": d.world_x, "y": d.world_y,
                "id": d.dungeon_id,
            })
        return pois

    # ---- Statistics ----

    def _compute_world_stats(
        self, cfg: WorldConfig, tiles: List[List[WorldTile]],
    ) -> Dict[str, Any]:
        """Compute world generation statistics."""
        terrain_counts: Dict[str, int] = {}
        biome_counts: Dict[str, int] = {}
        water_count = 0

        for row in tiles:
            for tile in row:
                t = tile.terrain_type.value
                terrain_counts[t] = terrain_counts.get(t, 0) + 1
                b = tile.biome_type.value
                biome_counts[b] = biome_counts.get(b, 0) + 1
                if tile.is_water:
                    water_count += 1

        total = cfg.world_width * cfg.world_height
        return {
            "total_tiles": total,
            "water_percentage": round(water_count / total * 100, 1),
            "terrain_distribution": terrain_counts,
            "biome_distribution": biome_counts,
            "average_elevation": round(
                sum(tile.elevation for row in tiles for tile in row) / total, 3,
            ),
        }

    # ---- Query Methods ----

    def get_world(self, world_id: str) -> Optional[Dict[str, Any]]:
        world = self._worlds.get(world_id)
        return world.to_dict() if world else None

    def list_worlds(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._worlds.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_worlds_generated": self._total_generated,
            "cached_worlds": len(self._worlds),
            "default_config": self._default_config.to_dict(),
        }

    def generate_dungeon(
        self,
        style: DungeonStyle = DungeonStyle.DUNGEON,
        num_rooms: int = 10,
        max_width: int = 40,
        max_height: int = 40,
    ) -> GeneratedDungeon:
        """Generate a standalone dungeon."""
        rooms = self._generate_dungeon_rooms(num_rooms, max_width, max_height)
        corridors = self._generate_dungeon_corridors(rooms)
        total_area = sum(r["width"] * r["height"] for r in rooms)

        return GeneratedDungeon(
            name=f"Generated {style.value}",
            style=style,
            rooms=rooms,
            corridors=corridors,
            total_rooms=len(rooms),
            total_area=total_area,
            difficulty=0.5,
        )


# Module-level accessor
_procedural_world: Optional[EngineProceduralWorld] = None


def get_procedural_world() -> EngineProceduralWorld:
    global _procedural_world
    if _procedural_world is None:
        _procedural_world = EngineProceduralWorld()
    return _procedural_world