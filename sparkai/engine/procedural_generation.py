"""
SparkLabs Engine - Procedural Generation

Procedural content generation system for AI-native game engine.
Generates terrain, dungeons, loot tables, and environmental
content using configurable noise functions, cellular automata,
and grammar-based generation rules.

Architecture:
  ProceduralGenerator
    |-- TerrainGenerator (heightmap via Perlin/Simplex noise)
    |-- DungeonGenerator (room placement with corridor carving)
    |-- LootTable (weighted random item drops)
    |-- BiomeMapper (temperature/moisture-based biome zones)
    |-- VegetationPlacer (rule-based foliage distribution)

Generation Algorithms:
  - PERLIN: smooth gradient noise for natural terrain
  - CELLULAR: cellular automata for cave-like structures
  - BSP: binary space partition for room layouts
  - L_SYSTEM: Lindenmayer system for organic patterns
  - WANG_TILES: tile-based constraint satisfaction
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class GenerationAlgorithm(Enum):
    PERLIN = "perlin"
    SIMPLEX = "simplex"
    CELLULAR = "cellular"
    BSP = "bsp"
    L_SYSTEM = "l_system"
    WANG_TILES = "wang_tiles"
    RANDOM_WALK = "random_walk"


class BiomeType(Enum):
    DESERT = "desert"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    SWAMP = "swamp"
    TUNDRA = "tundra"
    PLAINS = "plains"
    OCEAN = "ocean"
    VOLCANIC = "volcanic"


@dataclass
class LootEntry:
    item_id: str = ""
    name: str = ""
    weight: float = 1.0
    min_quantity: int = 1
    max_quantity: int = 1
    category: str = "common"
    tags: List[str] = field(default_factory=list)


@dataclass
class LootTable:
    table_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    entries: List[LootEntry] = field(default_factory=list)
    min_rolls: int = 1
    max_rolls: int = 3

    def roll(self, rng: random.Random) -> List[LootEntry]:
        rolls = rng.randint(self.min_rolls, self.max_rolls)
        results: List[LootEntry] = []
        total_weight = sum(e.weight for e in self.entries)
        if total_weight <= 0:
            return results
        for _ in range(rolls):
            roll = rng.uniform(0, total_weight)
            cumulative = 0.0
            for entry in self.entries:
                cumulative += entry.weight
                if roll <= cumulative:
                    results.append(entry)
                    break
        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "name": self.name,
            "entry_count": len(self.entries),
            "rolls": f"{self.min_rolls}-{self.max_rolls}",
        }


@dataclass
class TerrainMap:
    map_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    width: int = 64
    height: int = 64
    heightmap: List[List[float]] = field(default_factory=list)
    biome_map: List[List[str]] = field(default_factory=list)
    seed: int = 42

    def get_tile(self, x: int, y: int) -> Tuple[float, str]:
        if 0 <= x < self.width and 0 <= y < self.height:
            h = self.heightmap[y][x] if self.heightmap else 0.0
            b = self.biome_map[y][x] if self.biome_map else "plains"
            return (h, b)
        return (0.0, "plains")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "map_id": self.map_id,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "min_height": min(min(row) for row in self.heightmap) if self.heightmap else 0,
            "max_height": max(max(row) for row in self.heightmap) if self.heightmap else 0,
        }


@dataclass
class Room:
    x: int = 0
    y: int = 0
    width: int = 5
    height: int = 5
    room_type: str = "normal"

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def intersects(self, other: "Room") -> bool:
        return not (
            self.x + self.width + 1 < other.x
            or other.x + other.width + 1 < self.x
            or self.y + self.height + 1 < other.y
            or other.y + other.height + 1 < self.y
        )


@dataclass
class DungeonMap:
    map_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    width: int = 80
    height: int = 60
    grid: List[List[int]] = field(default_factory=list)
    rooms: List[Room] = field(default_factory=list)
    seed: int = 42

    def to_dict(self) -> Dict[str, Any]:
        return {
            "map_id": self.map_id,
            "width": self.width,
            "height": self.height,
            "room_count": len(self.rooms),
            "seed": self.seed,
            "total_cells": self.width * self.height,
        }


class ProceduralGenerator:
    """Procedural content generation for AI-native game engine."""

    _instance: Optional["ProceduralGenerator"] = None
    _lock = threading.Lock()

    MAX_LOOT_TABLES = 200
    MAX_MAPS = 50

    def __init__(self):
        self._loot_tables: Dict[str, LootTable] = {}
        self._terrain_maps: Dict[str, TerrainMap] = {}
        self._dungeon_maps: Dict[str, DungeonMap] = {}
        self._rng = random.Random()

    @classmethod
    def get_instance(cls) -> "ProceduralGenerator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _perlin_noise_2d(self, x: float, y: float, perm: List[int]) -> float:
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = xf * xf * (3.0 - 2.0 * xf)
        v = yf * yf * (3.0 - 2.0 * yf)
        aa = perm[perm[xi] + yi]
        ab = perm[perm[xi] + yi + 1]
        ba = perm[perm[xi + 1] + yi]
        bb = perm[perm[xi + 1] + yi + 1]
        x1 = (1.0 - u) * (1.0 - v) * self._grad(aa, xf, yf)
        x2 = u * (1.0 - v) * self._grad(ba, xf - 1.0, yf)
        x3 = (1.0 - u) * v * self._grad(ab, xf, yf - 1.0)
        x4 = u * v * self._grad(bb, xf - 1.0, yf - 1.0)
        return x1 + x2 + x3 + x4

    def _grad(self, hash_val: int, x: float, y: float) -> float:
        h = hash_val & 3
        if h == 0:
            return x + y
        elif h == 1:
            return -x + y
        elif h == 2:
            return x - y
        else:
            return -x - y

    def _generate_permutation(self, seed: int) -> List[int]:
        self._rng.seed(seed)
        p = list(range(256))
        self._rng.shuffle(p)
        return p + p

    def generate_terrain(
        self,
        width: int = 64,
        height: int = 64,
        seed: int = 42,
        octaves: int = 4,
        persistence: float = 0.5,
        scale: float = 32.0,
    ) -> TerrainMap:
        terrain = TerrainMap(width=width, height=height, seed=seed)
        perm = self._generate_permutation(seed)
        heightmap: List[List[float]] = []
        biome_map: List[List[str]] = []

        for y in range(height):
            row_h: List[float] = []
            row_b: List[str] = []
            for x in range(width):
                nx = x / scale
                ny = y / scale
                value = 0.0
                amplitude = 1.0
                frequency = 1.0
                max_value = 0.0

                for _ in range(octaves):
                    value += self._perlin_noise_2d(
                        nx * frequency, ny * frequency, perm
                    ) * amplitude
                    max_value += amplitude
                    amplitude *= persistence
                    frequency *= 2.0

                value = (value / max_value + 1.0) / 2.0
                row_h.append(round(value, 4))

                if value < 0.3:
                    biome = "ocean"
                elif value < 0.45:
                    biome = "desert"
                elif value < 0.55:
                    biome = "plains"
                elif value < 0.7:
                    biome = "forest"
                elif value < 0.85:
                    biome = "mountain"
                else:
                    biome = "volcanic"
                row_b.append(biome)

            heightmap.append(row_h)
            biome_map.append(row_b)

        terrain.heightmap = heightmap
        terrain.biome_map = biome_map
        self._terrain_maps[terrain.map_id] = terrain
        return terrain

    def generate_dungeon(
        self,
        width: int = 80,
        height: int = 60,
        seed: int = 42,
        room_count: int = 12,
        min_room_size: int = 4,
        max_room_size: int = 10,
    ) -> DungeonMap:
        self._rng.seed(seed)
        dungeon = DungeonMap(width=width, height=height, seed=seed)
        grid = [[0 for _ in range(width)] for _ in range(height)]
        rooms: List[Room] = []

        for _ in range(room_count * 3):
            rw = self._rng.randint(min_room_size, max_room_size)
            rh = self._rng.randint(min_room_size, max_room_size)
            rx = self._rng.randint(1, width - rw - 2)
            ry = self._rng.randint(1, height - rh - 2)
            room = Room(x=rx, y=ry, width=rw, height=rh)

            if not any(room.intersects(other) for other in rooms):
                rooms.append(room)
                for dy in range(rh):
                    for dx in range(rw):
                        grid[ry + dy][rx + dx] = 1
            if len(rooms) >= room_count:
                break

        rooms.sort(key=lambda r: (r.center[1], r.center[0]))
        for i in range(len(rooms) - 1):
            x1, y1 = rooms[i].center
            x2, y2 = rooms[i + 1].center
            if self._rng.random() < 0.5:
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    grid[y1][x] = 1
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    grid[y][x2] = 1
            else:
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    grid[y][x1] = 1
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    grid[y2][x] = 1

        dungeon.grid = grid
        dungeon.rooms = rooms
        self._dungeon_maps[dungeon.map_id] = dungeon
        return dungeon

    def create_loot_table(
        self,
        name: str,
        min_rolls: int = 1,
        max_rolls: int = 3,
    ) -> LootTable:
        table = LootTable(name=name, min_rolls=min_rolls, max_rolls=max_rolls)
        self._loot_tables[table.table_id] = table
        return table

    def add_loot_entry(
        self,
        table_id: str,
        name: str,
        weight: float = 1.0,
        min_qty: int = 1,
        max_qty: int = 1,
        category: str = "common",
    ) -> Optional[LootEntry]:
        table = self._loot_tables.get(table_id)
        if not table:
            return None
        entry = LootEntry(
            item_id=str(uuid.uuid4())[:8],
            name=name,
            weight=weight,
            min_quantity=min_qty,
            max_quantity=max_qty,
            category=category,
        )
        table.entries.append(entry)
        return entry

    def roll_loot(self, table_id: str) -> List[LootEntry]:
        table = self._loot_tables.get(table_id)
        if not table:
            return []
        return table.roll(self._rng)

    def get_terrain_map(self, map_id: str) -> Optional[TerrainMap]:
        return self._terrain_maps.get(map_id)

    def get_dungeon_map(self, map_id: str) -> Optional[DungeonMap]:
        return self._dungeon_maps.get(map_id)

    def get_loot_table(self, table_id: str) -> Optional[LootTable]:
        return self._loot_tables.get(table_id)

    def list_terrain_maps(self) -> List[TerrainMap]:
        return list(self._terrain_maps.values())

    def list_dungeon_maps(self) -> List[DungeonMap]:
        return list(self._dungeon_maps.values())

    def list_loot_tables(self) -> List[LootTable]:
        return list(self._loot_tables.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "terrain_maps": len(self._terrain_maps),
            "dungeon_maps": len(self._dungeon_maps),
            "loot_tables": len(self._loot_tables),
            "total_loot_entries": sum(len(t.entries) for t in self._loot_tables.values()),
            "total_dungeon_rooms": sum(len(d.rooms) for d in self._dungeon_maps.values()),
        }

    def delete_map(self, map_id: str) -> bool:
        if map_id in self._terrain_maps:
            del self._terrain_maps[map_id]
            return True
        if map_id in self._dungeon_maps:
            del self._dungeon_maps[map_id]
            return True
        return False


def get_procedural_generator() -> ProceduralGenerator:
    return ProceduralGenerator.get_instance()