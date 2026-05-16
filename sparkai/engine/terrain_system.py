"""
SparkLabs Engine - Terrain System

Grid-based terrain editing and generation system for game worlds.
Provides heightmap manipulation, brush-based sculpting, layer painting,
and procedural terrain generation with LOD chunking.

Architecture:
  TerrainSystem
    |-- TerrainChunk (subdivided terrain regions with LOD)
    |-- TerrainBrush (sculpting and painting tools)
    |-- Heightmap Generator (noise-based procedural generation)
    |-- Layer Painter (multi-layer terrain material blending)
    |-- Smooth Operator (Gaussian and average-based smoothing)

Terrain Layers:
  - SOLID: base ground layer
  - SAND: desert and beach areas
  - GRASS: vegetation-covered terrain
  - ROCK: exposed stone and cliffs
  - SNOW: high-altitude frozen terrain
  - MUD: wetland and swamp areas
  - WATER_SURFACE: shallow water covering
  - LAVA: volcanic terrain
"""

from __future__ import annotations

import math
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class TerrainLayer(Enum):
    SOLID = "solid"
    SAND = "sand"
    GRASS = "grass"
    ROCK = "rock"
    SNOW = "snow"
    MUD = "mud"
    WATER_SURFACE = "water_surface"
    LAVA = "lava"


class BrushShape(Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    DIAMOND = "diamond"
    NOISE = "noise"
    CUSTOM = "custom"


class TerrainType(Enum):
    FLATLANDS = "flatlands"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    CANYON = "canyon"
    ISLAND = "island"
    PLATEAU = "plateau"
    VALLEY = "valley"
    ARCHIPELAGO = "archipelago"
    VOLCANIC = "volcanic"


class NoiseAlgorithm(Enum):
    PERLIN = "perlin"
    SIMPLEX = "simplex"
    WORLEY = "worley"
    RIDGED = "ridged"
    BILLOW = "billow"
    FBM = "fbm"
    DOMAIN_WARP = "domain_warp"


LAYER_COLORS: Dict[TerrainLayer, Tuple[int, int, int]] = {
    TerrainLayer.SOLID: (120, 100, 80),
    TerrainLayer.SAND: (238, 214, 175),
    TerrainLayer.GRASS: (76, 153, 76),
    TerrainLayer.ROCK: (128, 128, 128),
    TerrainLayer.SNOW: (255, 255, 255),
    TerrainLayer.MUD: (101, 67, 33),
    TerrainLayer.WATER_SURFACE: (64, 128, 192),
    TerrainLayer.LAVA: (207, 16, 32),
}


@dataclass
class TerrainChunk:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chunk_x: int = 0
    chunk_y: int = 0
    resolution: int = 32
    heightmap: List[List[float]] = field(default_factory=list)
    layer_mask: List[List[int]] = field(default_factory=list)
    material_ids: List[str] = field(default_factory=list)
    is_dirty: bool = False
    lod_level: int = 0

    def get_size(self) -> int:
        return self.resolution

    def get_height(self, x: int, y: int) -> float:
        if 0 <= y < len(self.heightmap) and 0 <= x < len(self.heightmap[0]):
            return self.heightmap[y][x]
        return 0.0

    def set_height(self, x: int, y: int, height: float) -> bool:
        if 0 <= y < len(self.heightmap) and 0 <= x < len(self.heightmap[0]):
            self.heightmap[y][x] = max(-1.0, min(1.0, height))
            self.is_dirty = True
            return True
        return False

    def get_layer(self, x: int, y: int) -> int:
        if 0 <= y < len(self.layer_mask) and 0 <= x < len(self.layer_mask[0]):
            return self.layer_mask[y][x]
        return 0

    def set_layer(self, x: int, y: int, layer_index: int) -> bool:
        if 0 <= y < len(self.layer_mask) and 0 <= x < len(self.layer_mask[0]):
            self.layer_mask[y][x] = layer_index
            self.is_dirty = True
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chunk_x": self.chunk_x,
            "chunk_y": self.chunk_y,
            "resolution": self.resolution,
            "is_dirty": self.is_dirty,
            "lod_level": self.lod_level,
            "material_count": len(self.material_ids),
        }


@dataclass
class TerrainBrush:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    shape: BrushShape = BrushShape.CIRCLE
    radius: float = 5.0
    hardness: float = 0.75
    falloff_mode: str = "smooth"
    layer: TerrainLayer = TerrainLayer.GRASS
    target_height: float = 0.0

    def get_falloff(self, distance: float) -> float:
        if distance > self.radius:
            return 0.0
        normalized = distance / self.radius

        if self.falloff_mode == "linear":
            return max(0.0, 1.0 - normalized)
        elif self.falloff_mode == "sharp":
            return 1.0 if normalized < self.hardness else 0.0
        else:
            t = max(0.0, min(1.0, 1.0 - normalized))
            return t * t * (3.0 - 2.0 * t)

    def is_inside(self, dx: float, dy: float) -> bool:
        if self.shape == BrushShape.CIRCLE:
            return math.sqrt(dx * dx + dy * dy) <= self.radius
        elif self.shape == BrushShape.SQUARE:
            half = self.radius
            return abs(dx) <= half and abs(dy) <= half
        elif self.shape == BrushShape.DIAMOND:
            return abs(dx) + abs(dy) <= self.radius
        elif self.shape == BrushShape.NOISE:
            return math.sqrt(dx * dx + dy * dy) <= self.radius
        else:
            return math.sqrt(dx * dx + dy * dy) <= self.radius


class TerrainSystem:
    """
    Grid-based terrain editing and generation system.

    Manages terrain chunks with heightmap and layer-mask data,
    supports brush-based sculpting, procedural generation, and
    LOD-aware terrain management.

    Usage:
        ts = get_terrain_system()
        chunk_id = ts.create_terrain(256, 256, 32)
        ts.generate_heightmap(chunk_id, seed=42, algorithm="perlin")
        brush = TerrainBrush(radius=5.0, layer=TerrainLayer.ROCK)
        ts.apply_brush(chunk_id, brush, 50, 50)
    """

    _instance: Optional["TerrainSystem"] = None

    def __init__(self):
        self._chunks: Dict[str, TerrainChunk] = {}
        self._brushes: Dict[str, TerrainBrush] = {}
        self._permutation: List[int] = list(range(256)) * 2
        random.shuffle(self._permutation[:256])
        self._seed: int = 42
        self._total_applies: int = 0

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

    def create_terrain(self, width: int, depth: int, resolution: int) -> str:
        chunks_x = max(1, math.ceil(width / resolution))
        chunks_y = max(1, math.ceil(depth / resolution))

        chunk_ids: List[str] = []
        for cy in range(chunks_y):
            for cx in range(chunks_x):
                r = resolution
                heightmap = [[0.0] * r for _ in range(r)]
                layer_mask = [[0] * r for _ in range(r)]

                chunk = TerrainChunk(
                    chunk_x=cx,
                    chunk_y=cy,
                    resolution=r,
                    heightmap=heightmap,
                    layer_mask=layer_mask,
                )
                self._chunks[chunk.id] = chunk
                chunk_ids.append(chunk.id)

        return chunk_ids[0] if chunk_ids else ""

    def remove_terrain(self, chunk_id: str) -> bool:
        if chunk_id in self._chunks:
            del self._chunks[chunk_id]
            return True
        return False

    def set_height(self, chunk_id: str, x: int, y: int, height: float) -> bool:
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return False
        return chunk.set_height(x, y, height)

    def get_height(self, chunk_id: str, x: int, y: int) -> Optional[float]:
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return None
        if 0 <= y < len(chunk.heightmap) and 0 <= x < len(chunk.heightmap[0]):
            return chunk.heightmap[y][x]
        return None

    def apply_brush(self, chunk_id: str, brush: TerrainBrush, center_x: float, center_y: float) -> bool:
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return False

        self._brushes[brush.id] = brush
        layer_index = list(TerrainLayer).index(brush.layer)
        affected = 0

        r = chunk.resolution
        for dy in range(r):
            for dx in range(r):
                dist = math.sqrt((dx - center_x) ** 2 + (dy - center_y) ** 2)
                if brush.is_inside(dx - center_x, dy - center_y):
                    falloff = brush.get_falloff(dist)
                    current = chunk.heightmap[dy][dx]
                    chunk.heightmap[dy][dx] = current + (brush.target_height - current) * falloff * brush.hardness

                    if falloff > 0.5:
                        chunk.layer_mask[dy][dx] = layer_index

                    affected += 1

        chunk.is_dirty = True
        self._total_applies += 1
        return affected > 0

    def smooth_terrain(self, chunk_id: str, radius: float) -> bool:
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return False

        r = chunk.resolution
        smoothed = [row[:] for row in chunk.heightmap]
        affected = 0

        for y in range(r):
            for x in range(r):
                total = 0.0
                count = 0
                for ny in range(max(0, y - int(radius)), min(r, y + int(radius) + 1)):
                    for nx in range(max(0, x - int(radius)), min(r, x + int(radius) + 1)):
                        total += chunk.heightmap[ny][nx]
                        count += 1
                if count > 0:
                    smoothed[y][x] = total / count
                    affected += 1

        chunk.heightmap = smoothed
        chunk.is_dirty = True
        return True

    def generate_heightmap(self, chunk_id: str, seed: int, algorithm: str) -> bool:
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return False

        self.set_seed(seed)
        r = chunk.resolution

        for y in range(r):
            for x in range(r):
                if algorithm == "perlin":
                    chunk.heightmap[y][x] = self._perlin_noise(x * 0.1, y * 0.1, 4, 0.5)
                elif algorithm == "simplex":
                    chunk.heightmap[y][x] = self._simplex_noise(x * 0.1, y * 0.1)
                elif algorithm == "diamond_square":
                    chunk.heightmap[y][x] = self._value_noise(x * 0.05, y * 0.05)
                else:
                    chunk.heightmap[y][x] = self._perlin_noise(x * 0.1, y * 0.1, 3, 0.6)

        chunk.is_dirty = True
        return True

    def get_chunk(self, chunk_id: str) -> Optional[TerrainChunk]:
        return self._chunks.get(chunk_id)

    def list_chunks(self) -> List[TerrainChunk]:
        return list(self._chunks.values())

    def get_chunk_at(self, world_x: float, world_y: float, resolution: int) -> Optional[TerrainChunk]:
        cx = int(world_x // resolution)
        cy = int(world_y // resolution)
        for chunk in self._chunks.values():
            if chunk.chunk_x == cx and chunk.chunk_y == cy:
                return chunk
        return None

    def create_brush(
        self,
        shape: BrushShape = BrushShape.CIRCLE,
        radius: float = 5.0,
        hardness: float = 0.75,
        falloff_mode: str = "smooth",
        layer: TerrainLayer = TerrainLayer.GRASS,
        target_height: float = 0.0,
    ) -> TerrainBrush:
        brush = TerrainBrush(
            shape=shape,
            radius=radius,
            hardness=hardness,
            falloff_mode=falloff_mode,
            layer=layer,
            target_height=target_height,
        )
        self._brushes[brush.id] = brush
        return brush

    def get_stats(self) -> Dict[str, Any]:
        return {
            "chunk_count": len(self._chunks),
            "brush_count": len(self._brushes),
            "seed": self._seed,
            "total_applies": self._total_applies,
            "dirty_chunks": sum(1 for c in self._chunks.values() if c.is_dirty),
            "chunks": [c.to_dict() for c in self._chunks.values()],
        }

    def reset(self) -> None:
        self._chunks.clear()
        self._brushes.clear()
        self._total_applies = 0
        self.set_seed(42)

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


def get_terrain_system() -> TerrainSystem:
    return TerrainSystem.get_instance()