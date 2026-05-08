"""
SparkLabs Engine - Terrain System

2D procedural terrain generation and management for game worlds.
Provides heightmap-based terrain, auto-tiling, biome blending,
and terrain editing tools. The AI agent uses this system to
generate diverse game worlds algorithmically.

Architecture:
  TerrainSystem
    |-- HeightmapGenerator (noise-based elevation)
    |-- BiomeMapper (temperature/moisture → terrain type)
    |-- AutoTiler (rule-based tileset mapping)
    |-- TerrainChunk (region with LOD support)
    |-- TerrainBrush (editing tools: raise, lower, smooth, flatten)

Generation Algorithms:
  - PERLIN: classic gradient noise
  - SIMPLEX: improved gradient noise  
  - VORONOI: cell-based biome distribution
  - DIAMOND_SQUARE: fractal heightmap
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TerrainType(Enum):
    WATER = "water"
    SAND = "sand"
    GRASS = "grass"
    DIRT = "dirt"
    STONE = "stone"
    SNOW = "snow"
    FOREST = "forest"
    SWAMP = "swamp"
    LAVA = "lava"


class NoiseAlgorithm(Enum):
    PERLIN = "perlin"
    SIMPLEX = "simplex"
    VALUE = "value"
    DIAMOND_SQUARE = "diamond_square"


@dataclass
class TerrainCell:
    x: int
    y: int
    height: float = 0.0
    terrain_type: TerrainType = TerrainType.GRASS
    moisture: float = 0.5
    temperature: float = 0.5
    flags: int = 0

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "height": round(self.height, 3),
            "terrain": self.terrain_type.value,
        }


@dataclass
class TerrainChunk:
    chunk_x: int
    chunk_y: int
    width: int
    height: int
    cells: List[List[TerrainCell]] = field(default_factory=list)
    generated: bool = False
    modified: bool = False


@dataclass
class BiomeRule:
    name: str
    terrain_type: TerrainType
    min_height: float = -1.0
    max_height: float = 1.0
    min_moisture: float = 0.0
    max_moisture: float = 1.0
    min_temperature: float = 0.0
    max_temperature: float = 1.0


class TerrainSystem:
    """
    Procedural 2D terrain generation and editing.

    Generates heightmaps and biome distributions for game
    worlds using noise algorithms. Supports auto-tiling
    rulesets and brush-based terrain editing. AI agents use
    this to procedurally generate landscapes and modify
    them in response to game events.
    """

    _instance: Optional["TerrainSystem"] = None

    def __init__(self):
        self._chunks: Dict[Tuple[int, int], TerrainChunk] = {}
        self._biome_rules: List[BiomeRule] = []
        self._permutation: List[int] = list(range(256)) * 2
        random.shuffle(self._permutation[:256])
        self._seed: int = 42
        self._default_chunk_size: int = 16
        self._register_default_biomes()

    @classmethod
    def get_instance(cls) -> "TerrainSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_seed(self, seed: int) -> None:
        self._seed = seed
        random.seed(seed)
        self._permutation = list(range(256)) * 2
        random.shuffle(self._permutation[:256])

    def generate_heightmap(
        self,
        width: int,
        height: int,
        algorithm: NoiseAlgorithm = NoiseAlgorithm.PERLIN,
        scale: float = 0.05,
        octaves: int = 4,
        persistence: float = 0.5,
    ) -> List[List[float]]:
        heights = [[0.0] * width for _ in range(height)]

        for y in range(height):
            for x in range(width):
                if algorithm == NoiseAlgorithm.PERLIN:
                    heights[y][x] = self._perlin_noise(x * scale, y * scale, octaves, persistence)
                elif algorithm == NoiseAlgorithm.SIMPLEX:
                    heights[y][x] = self._simplex_noise(x * scale, y * scale)
                else:
                    heights[y][x] = self._value_noise(x * scale, y * scale)

        return heights

    def generate_terrain(
        self,
        width: int,
        height: int,
        scale: float = 0.05,
        octaves: int = 4,
    ) -> List[List[TerrainCell]]:
        heightmap = self.generate_heightmap(width, height, scale=scale, octaves=octaves)
        moisture_map = self.generate_heightmap(width, height, scale=scale * 1.3, octaves=3)
        temp_map = self.generate_heightmap(width, height, scale=scale * 0.7, octaves=3)

        cells = []
        for y in range(height):
            row = []
            for x in range(width):
                h = heightmap[y][x]
                m = (moisture_map[y][x] + 1.0) / 2.0
                t = (temp_map[y][x] + 1.0) / 2.0
                terrain = self._resolve_biome(h, m, t)
                row.append(TerrainCell(x=x, y=y, height=h, terrain_type=terrain, moisture=m, temperature=t))
            cells.append(row)

        return cells

    def generate_chunk(self, chunk_x: int, chunk_y: int) -> TerrainChunk:
        size = self._default_chunk_size
        key = (chunk_x, chunk_y)
        if key in self._chunks:
            return self._chunks[key]

        ox = chunk_x * size
        oy = chunk_y * size
        cells = self.generate_terrain(size, size, scale=0.05)
        for row in cells:
            for cell in row:
                cell.x += ox
                cell.y += oy

        chunk = TerrainChunk(
            chunk_x=chunk_x,
            chunk_y=chunk_y,
            width=size,
            height=size,
            cells=cells,
            generated=True,
        )
        self._chunks[key] = chunk
        return chunk

    def get_cell(self, x: int, y: int) -> Optional[TerrainCell]:
        size = self._default_chunk_size
        cx, cy = x // size, y // size
        chunk = self._chunks.get((cx, cy))
        if not chunk:
            return None
        lx, ly = x % size, y % size
        if 0 <= ly < chunk.height and 0 <= lx < chunk.width:
            return chunk.cells[ly][lx]
        return None

    def set_terrain(self, x: int, y: int, terrain_type: TerrainType) -> bool:
        cell = self.get_cell(x, y)
        if not cell:
            return False
        cell.terrain_type = terrain_type
        size = self._default_chunk_size
        key = (x // size, y // size)
        if key in self._chunks:
            self._chunks[key].modified = True
        return True

    def raise_terrain(self, x: int, y: int, amount: float) -> bool:
        cell = self.get_cell(x, y)
        if not cell:
            return False
        cell.height = max(-1.0, min(1.0, cell.height + amount))
        return True

    def smooth_area(self, cx: int, cy: int, radius: int) -> int:
        count = 0
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                neighbors = []
                cell = self.get_cell(cx + dx, cy + dy)
                if not cell:
                    continue
                for ny in range(-1, 2):
                    for nx in range(-1, 2):
                        n = self.get_cell(cx + dx + nx, cy + dy + ny)
                        if n:
                            neighbors.append(n.height)
                if neighbors:
                    cell.height = sum(neighbors) / len(neighbors)
                    count += 1
        return count

    def add_biome_rule(self, rule: BiomeRule) -> None:
        self._biome_rules.append(rule)

    def list_biomes(self) -> List[BiomeRule]:
        return list(self._biome_rules)

    def _resolve_biome(self, height: float, moisture: float, temperature: float) -> TerrainType:
        for rule in self._biome_rules:
            if (
                rule.min_height <= height <= rule.max_height
                and rule.min_moisture <= moisture <= rule.max_moisture
            ):
                return rule.terrain_type

        if height < -0.3:
            return TerrainType.WATER
        elif height < -0.1:
            return TerrainType.SAND
        elif height < 0.2:
            return TerrainType.GRASS
        elif height < 0.5:
            return TerrainType.STONE
        else:
            return TerrainType.SNOW

    def _fade(self, t: float) -> float:
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _grad(self, hash_val: int, x: float, y: float) -> float:
        h = hash_val & 3
        u = x if h < 1 or h == 3 else -x
        v = y if h < 2 else -y
        return u + v

    def _perlin_noise(self, x: float, y: float, octaves: int = 1, persistence: float = 0.5) -> float:
        total = 0.0
        freq = 1.0
        amp = 1.0
        max_val = 0.0

        for _ in range(octaves):
            ix = int(math.floor(x * freq)) & 255
            iy = int(math.floor(y * freq)) & 255
            xf = (x * freq) - math.floor(x * freq)
            yf = (y * freq) - math.floor(y * freq)
            u = self._fade(xf)
            v = self._fade(yf)

            aa = self._permutation[self._permutation[ix] + iy]
            ab = self._permutation[self._permutation[ix] + iy + 1]
            ba = self._permutation[self._permutation[ix + 1] + iy]
            bb = self._permutation[self._permutation[ix + 1] + iy + 1]

            x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1.0, yf), u)
            x2 = self._lerp(self._grad(ab, xf, yf - 1.0), self._grad(bb, xf - 1.0, yf - 1.0), u)
            total += self._lerp(x1, x2, v) * amp
            max_val += amp
            freq *= 2.0
            amp *= persistence

        return total / max_val if max_val > 0 else 0.0

    def _simplex_noise(self, x: float, y: float) -> float:
        return self._perlin_noise(x, y, 1)

    def _value_noise(self, x: float, y: float) -> float:
        ix = int(math.floor(x)) & 255
        iy = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = self._fade(xf)
        v = self._fade(yf)
        a = self._permutation[self._permutation[ix] + iy]
        b = self._permutation[self._permutation[ix + 1] + iy]
        c = self._permutation[self._permutation[ix] + iy + 1]
        d = self._permutation[self._permutation[ix + 1] + iy + 1]
        val = self._lerp(self._lerp(a / 255.0, b / 255.0, u), self._lerp(c / 255.0, d / 255.0, u), v)
        return val * 2.0 - 1.0

    def _register_default_biomes(self) -> None:
        defaults = [
            BiomeRule("deep_water", TerrainType.WATER, -1.0, -0.45),
            BiomeRule("shallow_water", TerrainType.WATER, -0.45, -0.3),
            BiomeRule("beach", TerrainType.SAND, -0.3, -0.15),
            BiomeRule("grassland", TerrainType.GRASS, -0.15, 0.15),
            BiomeRule("forest", TerrainType.FOREST, -0.1, 0.25, 0.4, 1.0),
            BiomeRule("swamp", TerrainType.SWAMP, -0.2, 0.05, 0.6, 1.0),
            BiomeRule("rocky", TerrainType.STONE, 0.2, 0.5),
            BiomeRule("mountain", TerrainType.STONE, 0.5, 0.75),
            BiomeRule("snow", TerrainType.SNOW, 0.7, 1.0),
            BiomeRule("lava_field", TerrainType.LAVA, 0.3, 1.0, 0.0, 0.2, 0.8, 1.0),
        ]
        self._biome_rules = defaults

    def get_stats(self) -> dict:
        return {
            "chunks": len(self._chunks),
            "chunk_size": self._default_chunk_size,
            "biome_rules": len(self._biome_rules),
            "seed": self._seed,
            "generated": all(c.generated for c in self._chunks.values()),
        }

    def reset(self) -> None:
        self._chunks.clear()
        self._biome_rules = []
        self._register_default_biomes()
        self.set_seed(self._seed)


def get_terrain_system() -> TerrainSystem:
    return TerrainSystem.get_instance()
