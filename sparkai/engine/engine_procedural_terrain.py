"""
SparkLabs Engine - Procedural Terrain Generation

A comprehensive procedural terrain generation system providing
multi-octave noise generation, heightmap synthesis, hydraulic and
thermal erosion simulation, biome mapping, and terrain mesh
construction for the SparkLabs game engine.

Architecture:
  ProceduralTerrainEngine (Singleton)
    |-- NoiseGenerator       — Perlin, Simplex, and Worley noise
    |-- HeightmapGenerator   — multi-octave fractal heightmap
    |-- ErosionSimulator     — hydraulic and thermal erosion
    |-- BiomeMapper          — terrain type assignment from parameters
    |-- TerrainMeshBuilder   — vertex/index buffer generation
    |-- TerrainChunk         — spatial subdivision with LOD support

Generation Pipeline:
  1. NoiseGenerator produces base noise values at each coordinate
  2. HeightmapGenerator combines multi-octave noise for heightmap
  3. ErosionSimulator applies hydraulic/thermal erosion
  4. BiomeMapper assigns terrain types based on height, slope, moisture
  5. TerrainMeshBuilder generates vertex/index data for rendering
  6. TerrainChunk partitions the terrain spatially with LOD levels

Usage:
    engine = get_procedural_terrain_engine()
    engine.generate_heightmap(size=512, seed=12345)
    engine.apply_erosion(iterations=100)
    engine.build_terrain_mesh(chunk_size=32)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NoiseType(Enum):
    """Type of noise algorithm for generation."""
    PERLIN = "perlin"
    SIMPLEX = "simplex"
    WORLEY = "worley"
    VALUE = "value"
    WHITE = "white"


class TerrainLOD(Enum):
    """Level of detail for terrain chunks."""
    LOD0 = 0
    LOD1 = 1
    LOD2 = 2
    LOD3 = 3
    LOD4 = 4


class ErosionMode(Enum):
    """Type of erosion simulation to apply."""
    HYDRAULIC = "hydraulic"
    THERMAL = "thermal"
    WIND = "wind"
    COMBINED = "combined"


class BiomeType(Enum):
    """Terrain biome classification."""
    TUNDRA = "tundra"
    TAIGA = "taiga"
    TEMPERATE_FOREST = "temperate_forest"
    GRASSLAND = "grassland"
    DESERT = "desert"
    SAVANNA = "savanna"
    TROPICAL_RAINFOREST = "tropical_rainforest"
    MOUNTAIN = "mountain"
    BEACH = "beach"
    OCEAN = "ocean"
    SWAMP = "swamp"
    ICE_CAP = "ice_cap"


class ChunkState(Enum):
    """Lifecycle state of a terrain chunk."""
    UNGENERATED = "ungenerated"
    GENERATING = "generating"
    GENERATED = "generated"
    MESH_BUILT = "mesh_built"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _fade(t: float) -> float:
    """Perlin fade function: 6t^5 - 15t^4 + 10t^3."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _grad(hash_val: int, x: float, y: float) -> float:
    """Convert hash to gradient direction and compute dot product."""
    h = hash_val & 15
    u = x if h < 8 else y
    v = y if h < 4 else (x if h == 12 or h == 14 else 0.0)
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class NoiseGenerator:
    """Multi-type noise generator (Perlin, Simplex, Worley, Value).

    Supports multiple noise algorithms with configurable octaves,
    persistence, lacunarity, and frequency parameters. Generates
    coherent noise used as the foundation for terrain heightmaps.
    """
    generator_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    seed: int = 0
    noise_type: NoiseType = NoiseType.SIMPLEX
    octaves: int = 6
    persistence: float = 0.5
    lacunarity: float = 2.0
    frequency: float = 1.0
    amplitude: float = 1.0
    _permutation: List[int] = field(default_factory=list, repr=False)
    _perm_size: int = 256

    def __post_init__(self) -> None:
        self._generate_permutation()

    def _generate_permutation(self) -> None:
        """Generate a permutation table from the seed."""
        rng = random.Random(self.seed)
        p = list(range(self._perm_size))
        rng.shuffle(p)
        self._permutation = p + p

    def _hash(self, x: int, y: int) -> int:
        return self._permutation[(self._permutation[x & 255] + y) & 255]

    def perlin_noise(self, x: float, y: float) -> float:
        """Compute 2D Perlin noise at (x, y)."""
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)

        u = _fade(xf)
        v = _fade(yf)

        aa = self._hash(xi, yi)
        ab = self._hash(xi, yi + 1)
        ba = self._hash(xi + 1, yi)
        bb = self._hash(xi + 1, yi + 1)

        x1 = _lerp(_grad(aa, xf, yf), _grad(ba, xf - 1, yf), u)
        x2 = _lerp(_grad(ab, xf, yf - 1), _grad(bb, xf - 1, yf - 1), u)

        return _lerp(x1, x2, v)

    def simplex_noise(self, x: float, y: float) -> float:
        """Compute 2D Simplex noise at (x, y)."""
        f2 = 0.5 * (math.sqrt(3.0) - 1.0)
        g2 = (3.0 - math.sqrt(3.0)) / 6.0

        s = (x + y) * f2
        xi = int(math.floor(x + s))
        yi = int(math.floor(y + s))

        t = float(xi + yi) * g2
        x0 = x - (xi - t)
        y0 = y - (yi - t)

        i1 = 1 if x0 > y0 else 0
        j1 = 0 if x0 > y0 else 1

        x1 = x0 - i1 + g2
        y1 = y0 - j1 + g2
        x2 = x0 - 1.0 + 2.0 * g2
        y2 = y0 - 1.0 + 2.0 * g2

        xi = xi & 255
        yi = yi & 255

        t0 = 0.5 - x0 * x0 - y0 * y0
        n0 = 0.0
        if t0 > 0:
            t0 *= t0
            n0 = t0 * t0 * _grad(self._hash(xi, yi), x0, y0)

        t1 = 0.5 - x1 * x1 - y1 * y1
        n1 = 0.0
        if t1 > 0:
            t1 *= t1
            n1 = t1 * t1 * _grad(self._hash(xi + i1, yi + j1), x1, y1)

        t2 = 0.5 - x2 * x2 - y2 * y2
        n2 = 0.0
        if t2 > 0:
            t2 *= t2
            n2 = t2 * t2 * _grad(self._hash(xi + 1, yi + 1), x2, y2)

        return 70.0 * (n0 + n1 + n2)

    def worley_noise(self, x: float, y: float) -> float:
        """Compute 2D Worley (cellular) noise at (x, y)."""
        xi = int(math.floor(x))
        yi = int(math.floor(y))
        min_dist = float("inf")

        for dx in range(-1, 2):
            for dy in range(-1, 2):
                cx = xi + dx
                cy = yi + dy
                h = self._hash(cx & 255, cy & 255)
                feature_x = cx + ((h % 1000) / 1000.0)
                feature_y = cy + (((h // 1000) % 1000) / 1000.0)
                dist = math.sqrt((x - feature_x) ** 2 + (y - feature_y) ** 2)
                min_dist = min(min_dist, dist)

        return min_dist

    def value_noise(self, x: float, y: float) -> float:
        """Compute 2D value noise at (x, y)."""
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)

        u = _fade(xf)
        v = _fade(yf)

        a = self._hash(xi, yi) / 255.0
        b = self._hash(xi + 1, yi) / 255.0
        c = self._hash(xi, yi + 1) / 255.0
        d = self._hash(xi + 1, yi + 1) / 255.0

        return _lerp(_lerp(a, b, u), _lerp(c, d, u), v)

    def sample(self, x: float, y: float) -> float:
        """Sample noise at (x, y) using the configured noise type."""
        if self.noise_type == NoiseType.PERLIN:
            return self.perlin_noise(x, y)
        elif self.noise_type == NoiseType.SIMPLEX:
            return self.simplex_noise(x, y)
        elif self.noise_type == NoiseType.WORLEY:
            return self.worley_noise(x, y)
        elif self.noise_type == NoiseType.VALUE:
            return self.value_noise(x, y)
        elif self.noise_type == NoiseType.WHITE:
            return random.Random(self.seed + int(x * 1000 + y)).random()
        return 0.0

    def sample_octave(self, x: float, y: float) -> float:
        """Sample multi-octave noise at (x, y)."""
        value = 0.0
        max_value = 0.0
        freq = self.frequency
        amp = self.amplitude

        for _ in range(self.octaves):
            value += self.sample(x * freq, y * freq) * amp
            max_value += amp
            freq *= self.lacunarity
            amp *= self.persistence

        return value / max_value if max_value > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generator_id": self.generator_id,
            "seed": self.seed,
            "noise_type": self.noise_type.value,
            "octaves": self.octaves,
            "persistence": self.persistence,
            "lacunarity": self.lacunarity,
            "frequency": self.frequency,
            "amplitude": self.amplitude,
        }


@dataclass
class HeightmapGenerator:
    """Generates heightmaps using multi-octave noise synthesis.

    Combines multiple noise layers with different frequencies and
    amplitudes to produce realistic terrain heightmaps. Supports
    ridged noise, domain warping, and terrace effects.
    """
    generator_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    size: int = 256
    noise_generator: NoiseGenerator = field(default_factory=NoiseGenerator)
    height_multiplier: float = 100.0
    height_offset: float = 0.0
    use_ridged: bool = False
    ridge_offset: float = 0.9
    domain_warp_strength: float = 0.0
    terrace_levels: int = 0
    _heightmap: List[List[float]] = field(default_factory=list, repr=False)
    _generated: bool = False

    def generate(self, seed: Optional[int] = None) -> List[List[float]]:
        """Generate a heightmap of the configured size."""
        if seed is not None:
            self.noise_generator.seed = seed
            self.noise_generator._generate_permutation()

        self._heightmap = []
        for y in range(self.size):
            row = []
            for x in range(self.size):
                nx = x / self.size
                ny = y / self.size

                if self.domain_warp_strength > 0.001:
                    warp_x = self.noise_generator.sample(nx * 3, ny * 3) * self.domain_warp_strength
                    warp_y = self.noise_generator.sample(nx * 3 + 5.2, ny * 3 + 1.7) * self.domain_warp_strength
                    nx += warp_x
                    ny += warp_y

                value = self.noise_generator.sample_octave(nx, ny)

                if self.use_ridged:
                    value = self.ridge_offset - abs(value)
                    value = value * value

                value = value * self.height_multiplier + self.height_offset

                if self.terrace_levels > 1:
                    value = self._apply_terrace(value)

                row.append(value)
            self._heightmap.append(row)

        self._generated = True
        return self._heightmap

    def _apply_terrace(self, value: float) -> float:
        """Apply terrace effect to height value."""
        normalized = (value - self.height_offset) / self.height_multiplier
        step = 1.0 / (self.terrace_levels - 1)
        terrace = round(normalized / step) * step
        return terrace * self.height_multiplier + self.height_offset

    def get_height(self, x: int, y: int) -> float:
        if not self._generated or not self._heightmap:
            return 0.0
        if 0 <= x < self.size and 0 <= y < self.size:
            return self._heightmap[y][x]
        return 0.0

    def get_height_bilinear(self, x: float, y: float) -> float:
        """Get height with bilinear interpolation for smooth sampling."""
        if not self._generated or not self._heightmap:
            return 0.0

        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        x1 = min(x0 + 1, self.size - 1)
        y1 = min(y0 + 1, self.size - 1)

        fx = x - x0
        fy = y - y0

        h00 = self.get_height(x0, y0)
        h10 = self.get_height(x1, y0)
        h01 = self.get_height(x0, y1)
        h11 = self.get_height(x1, y1)

        return _lerp(_lerp(h00, h10, fx), _lerp(h01, h11, fx), fy)

    def compute_normal(self, x: int, y: int, spacing: float = 1.0) -> Tuple[float, float, float]:
        """Compute the surface normal at a heightmap position."""
        h = self.get_height(x, y)
        hx = self.get_height(x + 1, y) - self.get_height(x - 1, y)
        hy = self.get_height(x, y + 1) - self.get_height(x, y - 1)

        nx = -hx / (2.0 * spacing)
        ny = -hy / (2.0 * spacing)
        nz = 1.0

        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length > 0.0001:
            return (nx / length, ny / length, nz / length)
        return (0.0, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generator_id": self.generator_id,
            "size": self.size,
            "height_multiplier": self.height_multiplier,
            "height_offset": self.height_offset,
            "use_ridged": self.use_ridged,
            "terrace_levels": self.terrace_levels,
            "generated": self._generated,
            "noise_generator": self.noise_generator.to_dict(),
            "min_height": min(min(row) for row in self._heightmap) if self._heightmap else 0.0,
            "max_height": max(max(row) for row in self._heightmap) if self._heightmap else 0.0,
        }


@dataclass
class ErosionSimulator:
    """Simulates hydraulic and thermal erosion on heightmaps.

    Implements particle-based hydraulic erosion where water droplets
    flow downhill, carrying and depositing sediment. Also supports
    thermal erosion for talus slope simulation.
    """
    simulator_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    erosion_mode: ErosionMode = ErosionMode.HYDRAULIC
    iterations: int = 50000
    erosion_rate: float = 0.01
    deposition_rate: float = 0.01
    evaporation_rate: float = 0.01
    min_slope: float = 0.01
    sediment_capacity: float = 4.0
    erosion_radius: float = 3.0
    talus_angle: float = 0.5
    _total_eroded: float = 0.0
    _total_deposited: float = 0.0

    def simulate(self, heightmap: List[List[float]],
                 size: int) -> List[List[float]]:
        """Apply erosion simulation to a heightmap."""
        hmap = [row[:] for row in heightmap]

        if self.erosion_mode in (ErosionMode.HYDRAULIC, ErosionMode.COMBINED):
            hmap = self._hydraulic_erosion(hmap, size)

        if self.erosion_mode in (ErosionMode.THERMAL, ErosionMode.COMBINED):
            hmap = self._thermal_erosion(hmap, size)

        if self.erosion_mode == ErosionMode.WIND:
            hmap = self._wind_erosion(hmap, size)

        return hmap

    def _hydraulic_erosion(self, hmap: List[List[float]],
                           size: int) -> List[List[float]]:
        """Simulate particle-based hydraulic erosion."""
        for _ in range(self.iterations):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 1)

            pos_x = float(x)
            pos_y = float(y)
            velocity = 0.0
            water = 1.0
            sediment = 0.0

            for _ in range(30):
                ix = int(pos_x) % size
                iy = int(pos_y) % size

                if ix < 0 or ix >= size or iy < 0 or iy >= size:
                    break

                # Compute gradient
                h = hmap[iy][ix]
                hx = (hmap[iy][min(ix + 1, size - 1)] -
                      hmap[iy][max(ix - 1, 0)])
                hy = (hmap[min(iy + 1, size - 1)][ix] -
                      hmap[max(iy - 1, 0)][ix])

                grad_x = hx / 2.0
                grad_y = hy / 2.0
                grad_len = math.sqrt(grad_x * grad_x + grad_y * grad_y)

                if grad_len < 0.0001:
                    break

                velocity = 0.95 * velocity + grad_len * 0.5
                capacity = max(grad_len, self.min_slope) * velocity * water * self.sediment_capacity

                if sediment > capacity:
                    deposit = (sediment - capacity) * self.deposition_rate
                    hmap[iy][ix] += deposit
                    sediment -= deposit
                    self._total_deposited += deposit
                else:
                    erode = min((capacity - sediment) * self.erosion_rate, -grad_len * 0.1)
                    hmap[iy][ix] -= erode
                    sediment += erode
                    self._total_eroded += erode

                water *= (1.0 - self.evaporation_rate)
                pos_x -= grad_x / (grad_len + 0.0001)
                pos_y -= grad_y / (grad_len + 0.0001)

                if water < 0.01:
                    break

        return hmap

    def _thermal_erosion(self, hmap: List[List[float]],
                         size: int) -> List[List[float]]:
        """Simulate thermal erosion (talus slope)."""
        for _ in range(self.iterations // 10):
            x = random.randint(1, size - 2)
            y = random.randint(1, size - 2)

            h = hmap[y][x]
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < size and 0 <= ny < size:
                    diff = h - hmap[ny][nx]
                    if diff > self.talus_angle:
                        move = (diff - self.talus_angle) * 0.5
                        hmap[y][x] -= move
                        hmap[ny][nx] += move
                        self._total_eroded += move

        return hmap

    def _wind_erosion(self, hmap: List[List[float]],
                      size: int) -> List[List[float]]:
        """Simulate wind erosion."""
        for _ in range(self.iterations // 10):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 1)
            h = hmap[y][x]
            if h > 0:
                erode = h * self.erosion_rate * random.uniform(0.5, 1.0)
                hmap[y][x] -= erode
                self._total_eroded += erode

                dx = random.randint(-2, 2)
                dy = random.randint(-2, 2)
                nx, ny = x + dx, y + dy
                if 0 <= nx < size and 0 <= ny < size:
                    deposit = erode * self.deposition_rate
                    hmap[ny][nx] += deposit
                    self._total_deposited += deposit

        return hmap

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulator_id": self.simulator_id,
            "erosion_mode": self.erosion_mode.value,
            "iterations": self.iterations,
            "erosion_rate": self.erosion_rate,
            "deposition_rate": self.deposition_rate,
            "total_eroded": self._total_eroded,
            "total_deposited": self._total_deposited,
        }


@dataclass
class BiomeMapper:
    """Assigns terrain biome types based on height, slope, and moisture.

    Uses a set of parameter rules to classify each terrain point into
    a biome type. Biomes influence terrain coloring, vegetation density,
    and gameplay properties.
    """
    mapper_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    biome_map: Dict[BiomeType, Dict[str, Any]] = field(default_factory=dict)
    _biome_grid: List[List[BiomeType]] = field(default_factory=list, repr=False)
    _generated: bool = False

    def __post_init__(self) -> None:
        if not self.biome_map:
            self._init_default_biomes()

    def _init_default_biomes(self) -> None:
        """Initialize default biome rules based on height and moisture."""
        self.biome_map = {
            BiomeType.OCEAN: {"min_height": -1.0, "max_height": -0.05, "min_moisture": 0.0, "max_moisture": 1.0},
            BiomeType.BEACH: {"min_height": -0.05, "max_height": 0.05, "min_moisture": 0.0, "max_moisture": 1.0},
            BiomeType.GRASSLAND: {"min_height": 0.05, "max_height": 0.3, "min_moisture": 0.3, "max_moisture": 0.6},
            BiomeType.DESERT: {"min_height": 0.05, "max_height": 0.3, "min_moisture": 0.0, "max_moisture": 0.3},
            BiomeType.TEMPERATE_FOREST: {"min_height": 0.05, "max_height": 0.4, "min_moisture": 0.6, "max_moisture": 1.0},
            BiomeType.TAIGA: {"min_height": 0.2, "max_height": 0.5, "min_moisture": 0.4, "max_moisture": 0.8},
            BiomeType.TUNDRA: {"min_height": 0.4, "max_height": 0.6, "min_moisture": 0.3, "max_moisture": 0.7},
            BiomeType.MOUNTAIN: {"min_height": 0.5, "max_height": 1.0, "min_moisture": 0.0, "max_moisture": 1.0},
            BiomeType.ICE_CAP: {"min_height": 0.6, "max_height": 1.0, "min_moisture": 0.0, "max_moisture": 0.3},
            BiomeType.SWAMP: {"min_height": -0.05, "max_height": 0.1, "min_moisture": 0.7, "max_moisture": 1.0},
            BiomeType.SAVANNA: {"min_height": 0.05, "max_height": 0.35, "min_moisture": 0.15, "max_moisture": 0.45},
            BiomeType.TROPICAL_RAINFOREST: {"min_height": 0.05, "max_height": 0.3, "min_moisture": 0.8, "max_moisture": 1.0},
        }

    def classify(self, height: float, moisture: float, slope: float = 0.0) -> BiomeType:
        """Classify a terrain point into a biome based on parameters."""
        height_norm = max(-1.0, min(1.0, height))
        moisture_norm = max(0.0, min(1.0, moisture))

        for biome, rules in self.biome_map.items():
            if (rules["min_height"] <= height_norm <= rules["max_height"] and
                    rules["min_moisture"] <= moisture_norm <= rules["max_moisture"]):
                return biome

        return BiomeType.GRASSLAND

    def generate_biome_map(self, heightmap: List[List[float]],
                           moisture_map: Optional[List[List[float]]] = None,
                           size: int = 256) -> List[List[BiomeType]]:
        """Generate a biome grid from heightmap and moisture data."""
        self._biome_grid = []
        for y in range(size):
            row = []
            for x in range(size):
                h = heightmap[y][x]
                if moisture_map:
                    m = moisture_map[y][x]
                else:
                    m = (math.sin(x / size * math.pi * 2) * 0.5 + 0.5) * 0.5 + \
                        (math.sin(y / size * math.pi * 3) * 0.5 + 0.5) * 0.5

                hx = (heightmap[y][min(x + 1, size - 1)] -
                      heightmap[y][max(x - 1, 0)]) / 2.0
                hy = (heightmap[min(y + 1, size - 1)][x] -
                      heightmap[max(y - 1, 0)][x]) / 2.0
                slope = math.sqrt(hx * hx + hy * hy)

                row.append(self.classify(h, m, slope))
            self._biome_grid.append(row)

        self._generated = True
        return self._biome_grid

    def get_biome(self, x: int, y: int) -> BiomeType:
        if not self._generated or not self._biome_grid:
            return BiomeType.GRASSLAND
        if 0 <= y < len(self._biome_grid) and 0 <= x < len(self._biome_grid[0]):
            return self._biome_grid[y][x]
        return BiomeType.GRASSLAND

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapper_id": self.mapper_id,
            "biome_count": len(self.biome_map),
            "biomes": [b.value for b in self.biome_map.keys()],
            "generated": self._generated,
        }


@dataclass
class TerrainMeshBuilder:
    """Constructs vertex and index buffers for terrain rendering.

    Generates vertex positions, normals, UV coordinates, and triangle
    indices from a heightmap. Supports LOD simplification by skipping
    vertices at higher detail levels.
    """
    builder_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    chunk_size: int = 32
    vertex_spacing: float = 1.0
    _vertices: List[float] = field(default_factory=list, repr=False)
    _indices: List[int] = field(default_factory=list, repr=False)
    _normals: List[float] = field(default_factory=list, repr=False)
    _uvs: List[float] = field(default_factory=list, repr=False)
    _vertex_count: int = 0
    _triangle_count: int = 0

    def build_mesh(self, heightmap: List[List[float]], size: int,
                   lod: TerrainLOD = TerrainLOD.LOD0) -> Tuple[List[float], List[int], List[float], List[float]]:
        """Build vertex and index buffers for the terrain mesh."""
        lod_skip = 1 << lod.value
        vertex_count = (size // lod_skip) + 1

        vertices = []
        normals = []
        uvs = []
        indices = []

        for y in range(0, size + 1, lod_skip):
            for x in range(0, size + 1, lod_skip):
                hx = min(x, size - 1)
                hy = min(y, size - 1)
                h = heightmap[hy][hx]

                vertices.extend([x * self.vertex_spacing, h, y * self.vertex_spacing])

                u = x / size
                v = y / size
                uvs.extend([u, v])

                h_left = heightmap[hy][max(hx - 1, 0)]
                h_right = heightmap[hy][min(hx + 1, size - 1)]
                h_up = heightmap[max(hy - 1, 0)][hx]
                h_down = heightmap[min(hy + 1, size - 1)][hx]

                nx = (h_left - h_right) / (2.0 * self.vertex_spacing)
                ny = 1.0
                nz = (h_up - h_down) / (2.0 * self.vertex_spacing)
                length = math.sqrt(nx * nx + ny * ny + nz * nz)
                if length > 0.0001:
                    normals.extend([nx / length, ny / length, nz / length])
                else:
                    normals.extend([0.0, 1.0, 0.0])

        row_count = vertex_count
        for y in range(row_count - 1):
            for x in range(row_count - 1):
                tl = y * row_count + x
                tr = y * row_count + x + 1
                bl = (y + 1) * row_count + x
                br = (y + 1) * row_count + x + 1

                indices.extend([tl, bl, tr])
                indices.extend([tr, bl, br])

        self._vertices = vertices
        self._indices = indices
        self._normals = normals
        self._uvs = uvs
        self._vertex_count = len(vertices) // 3
        self._triangle_count = len(indices) // 3

        return vertices, indices, normals, uvs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "builder_id": self.builder_id,
            "chunk_size": self.chunk_size,
            "vertex_count": self._vertex_count,
            "triangle_count": self._triangle_count,
        }


@dataclass
class TerrainChunk:
    """Spatial subdivision of terrain with LOD support.

    Represents a rectangular portion of the terrain grid at a specific
    LOD level. Chunks manage their own generation state and can be
    independently generated, eroded, and meshed.
    """
    chunk_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    origin_x: int = 0
    origin_y: int = 0
    chunk_size: int = 32
    lod: TerrainLOD = TerrainLOD.LOD0
    state: ChunkState = ChunkState.UNGENERATED
    heightmap: Optional[List[List[float]]] = None
    biome_grid: Optional[List[List[BiomeType]]] = None
    vertex_count: int = 0
    triangle_count: int = 0
    generation_time: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "origin_x": self.origin_x,
            "origin_y": self.origin_y,
            "chunk_size": self.chunk_size,
            "lod": self.lod.value,
            "state": self.state.value,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "generation_time": self.generation_time,
            "error_message": self.error_message,
        }


# ---------------------------------------------------------------------------
# ProceduralTerrainEngine — Unified Terrain Generation Singleton
# ---------------------------------------------------------------------------

class ProceduralTerrainEngine:
    """Complete procedural terrain generation engine for SparkLabs.

    Provides noise generation, heightmap synthesis, erosion simulation,
    biome mapping, and terrain mesh construction. Supports chunk-based
    terrain with LOD for efficient rendering of large worlds.
    """

    _instance: Optional["ProceduralTerrainEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "ProceduralTerrainEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ProceduralTerrainEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._noise_generator = NoiseGenerator()
        self._heightmap_generator = HeightmapGenerator()
        self._erosion_simulator = ErosionSimulator()
        self._biome_mapper = BiomeMapper()
        self._mesh_builder = TerrainMeshBuilder()
        self._heightmap: Optional[List[List[float]]] = None
        self._biome_grid: Optional[List[List[BiomeType]]] = None
        self._size: int = 256
        self._chunks: Dict[str, TerrainChunk] = {}
        self._seed: int = 0
        self._frame_count: int = 0
        self._generation_count: int = 0

    def generate_heightmap(self, size: int = 256, seed: int = 0,
                           noise_type: NoiseType = NoiseType.SIMPLEX,
                           octaves: int = 6, persistence: float = 0.5,
                           height_multiplier: float = 100.0) -> List[List[float]]:
        """Generate a full terrain heightmap."""
        self._size = size
        self._seed = seed

        self._noise_generator = NoiseGenerator(
            seed=seed, noise_type=noise_type, octaves=octaves,
            persistence=persistence,
        )
        self._heightmap_generator = HeightmapGenerator(
            size=size, noise_generator=self._noise_generator,
            height_multiplier=height_multiplier,
        )
        self._heightmap = self._heightmap_generator.generate(seed)
        self._generation_count += 1
        return self._heightmap

    def get_heightmap(self) -> Optional[List[List[float]]]:
        return self._heightmap

    def get_height(self, x: int, y: int) -> float:
        if self._heightmap is None:
            return 0.0
        return self._heightmap_generator.get_height(x, y)

    def apply_erosion(self, iterations: int = 50000,
                      erosion_mode: ErosionMode = ErosionMode.HYDRAULIC,
                      erosion_rate: float = 0.01) -> List[List[float]]:
        """Apply erosion simulation to the current heightmap."""
        if self._heightmap is None:
            return []

        self._erosion_simulator = ErosionSimulator(
            erosion_mode=erosion_mode, iterations=iterations,
            erosion_rate=erosion_rate,
        )
        self._heightmap = self._erosion_simulator.simulate(
            self._heightmap, self._size
        )
        return self._heightmap

    def generate_biomes(self, moisture_map: Optional[List[List[float]]] = None
                        ) -> List[List[BiomeType]]:
        """Generate biome map from the current heightmap."""
        if self._heightmap is None:
            return []

        self._biome_grid = self._biome_mapper.generate_biome_map(
            self._heightmap, moisture_map, self._size
        )
        return self._biome_grid

    def get_biome_grid(self) -> Optional[List[List[BiomeType]]]:
        return self._biome_grid

    def build_terrain_mesh(self, chunk_size: int = 32,
                           lod: TerrainLOD = TerrainLOD.LOD0
                           ) -> Tuple[List[float], List[int], List[float], List[float]]:
        """Build vertex and index buffers for the terrain mesh."""
        if self._heightmap is None:
            return [], [], [], []

        self._mesh_builder = TerrainMeshBuilder(chunk_size=chunk_size)
        return self._mesh_builder.build_mesh(self._heightmap, self._size, lod)

    def create_chunk(self, origin_x: int, origin_y: int,
                     chunk_size: int = 32,
                     lod: TerrainLOD = TerrainLOD.LOD0) -> TerrainChunk:
        """Create a new terrain chunk at the specified origin."""
        chunk = TerrainChunk(
            origin_x=origin_x, origin_y=origin_y,
            chunk_size=chunk_size, lod=lod,
        )
        self._chunks[chunk.chunk_id] = chunk
        return chunk

    def generate_chunk(self, chunk_id: str) -> Optional[TerrainChunk]:
        """Generate the heightmap and mesh for a specific chunk."""
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return None
        if self._heightmap is None:
            chunk.state = ChunkState.ERROR
            chunk.error_message = "No global heightmap generated"
            return chunk

        chunk.state = ChunkState.GENERATING
        start_time = _time_module.time()

        chunk_heightmap = []
        for y in range(chunk.origin_y, min(chunk.origin_y + chunk.chunk_size, self._size)):
            row = []
            for x in range(chunk.origin_x, min(chunk.origin_x + chunk.chunk_size, self._size)):
                row.append(self._heightmap[y][x])
            chunk_heightmap.append(row)

        chunk.heightmap = chunk_heightmap
        chunk.state = ChunkState.GENERATED
        chunk.generation_time = _time_module.time() - start_time
        return chunk

    def get_chunk(self, chunk_id: str) -> Optional[TerrainChunk]:
        return self._chunks.get(chunk_id)

    def update(self, delta_time: float) -> None:
        """Execute one frame of terrain processing."""
        self._frame_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "size": self._size,
            "seed": self._seed,
            "heightmap_generated": self._heightmap is not None,
            "biome_grid_generated": self._biome_grid is not None,
            "chunk_count": len(self._chunks),
            "generation_count": self._generation_count,
            "frame_count": self._frame_count,
            "noise_generator": self._noise_generator.to_dict(),
            "heightmap_generator": self._heightmap_generator.to_dict(),
            "erosion_simulator": self._erosion_simulator.to_dict(),
            "biome_mapper": self._biome_mapper.to_dict(),
            "mesh_builder": self._mesh_builder.to_dict(),
        }


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------

def get_procedural_terrain_engine() -> ProceduralTerrainEngine:
    """Get the global ProceduralTerrainEngine singleton instance."""
    return ProceduralTerrainEngine()