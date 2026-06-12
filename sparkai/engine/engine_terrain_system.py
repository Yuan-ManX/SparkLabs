"""
SparkLabs Engine - Terrain Generation & Management System

Comprehensive terrain generation and management system providing procedural
landscape generation with heightmaps, texture splatting, chunk-based streaming,
erosion simulation, and editing tools.

Architecture:
  EngineTerrainSystem (Singleton)
    |-- TerrainConfig   — configuration for a terrain instance
    |-- TerrainChunk    — a single chunk of terrain with height data
    |-- ErosionSettings — parameters for erosion simulation
    |-- BiomeLayer      — biome definition for texture/vegetation
    |-- TerrainStats    — runtime statistics snapshot

Terrain Pipeline:
  1. Create a TerrainConfig with size, seed, and algorithm parameters
  2. Generate terrain chunks with height data via the selected algorithm
  3. Apply erosion, biome layers, or manual editing tools
  4. Stream chunks in/out based on camera position and LOD
  5. Export heightmaps to various formats
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TerrainAlgorithm(str, Enum):
    """Noise algorithm used for terrain height generation."""
    PERLIN = "perlin"
    SIMPLEX = "simplex"
    DIAMOND_SQUARE = "diamond_square"
    VORONOI = "voronoi"
    RIDGED = "ridged"
    BILLOW = "billow"


class ErosionType(str, Enum):
    """Type of erosion simulation to apply to terrain."""
    HYDRAULIC = "hydraulic"
    THERMAL = "thermal"
    WIND = "wind"
    FLUVIAL = "fluvial"


class TextureLayer(str, Enum):
    """Layer types for texture splatting on terrain."""
    BASE = "base"
    SLOPE = "slope"
    HEIGHT = "height"
    SPLAT = "splat"
    DETAIL = "detail"


class ChunkState(str, Enum):
    """Runtime state of a terrain chunk for streaming management."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    MODIFIED = "modified"
    STREAMING = "streaming"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TerrainConfig:
    """Configuration for a terrain generation instance.

    Defines the terrain dimensions, noise algorithm parameters,
    and seed for deterministic generation.
    """

    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "terrain"
    width: int = 256
    depth: int = 256
    height_scale: float = 100.0
    seed: int = 42
    algorithm: TerrainAlgorithm = TerrainAlgorithm.PERLIN
    octaves: int = 4
    persistence: float = 0.5
    lacunarity: float = 2.0
    biome_layers: List[BiomeLayer] = field(default_factory=list)
    chunk_size: int = 64
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "width": self.width,
            "depth": self.depth,
            "height_scale": self.height_scale,
            "seed": self.seed,
            "algorithm": self.algorithm.value,
            "octaves": self.octaves,
            "persistence": self.persistence,
            "lacunarity": self.lacunarity,
            "biome_count": len(self.biome_layers),
            "chunk_size": self.chunk_size,
            "created_at": self.created_at,
        }


@dataclass
class TerrainChunk:
    """A single square chunk of terrain height data.

    Represents a sub-region of the terrain grid with its own
    heightmap, texture blending weights, and streaming state.
    """

    chunk_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    config_id: str = ""
    origin_x: int = 0
    origin_z: int = 0
    chunk_size: int = 64
    height_data: List[List[float]] = field(default_factory=list)
    texture_weights: Dict[str, float] = field(default_factory=dict)
    state: ChunkState = ChunkState.UNLOADED
    lod_level: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "config_id": self.config_id,
            "origin_x": self.origin_x,
            "origin_z": self.origin_z,
            "chunk_size": self.chunk_size,
            "height_grid_size": f"{len(self.height_data)}x{len(self.height_data[0]) if self.height_data else 0}",
            "texture_weights": dict(self.texture_weights),
            "state": self.state.value,
            "lod_level": self.lod_level,
        }


@dataclass
class ErosionSettings:
    """Parameters for terrain erosion simulation.

    Controls iterative particle-based erosion with configurable
    rates for material removal, deposition, evaporation, and rainfall.
    """

    settings_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    erosion_type: ErosionType = ErosionType.HYDRAULIC
    iterations: int = 50000
    erosion_rate: float = 0.3
    deposition_rate: float = 0.3
    evaporation_rate: float = 0.02
    rain_amount: float = 0.01

    def to_dict(self) -> Dict[str, Any]:
        return {
            "settings_id": self.settings_id,
            "erosion_type": self.erosion_type.value,
            "iterations": self.iterations,
            "erosion_rate": self.erosion_rate,
            "deposition_rate": self.deposition_rate,
            "evaporation_rate": self.evaporation_rate,
            "rain_amount": self.rain_amount,
        }


@dataclass
class BiomeLayer:
    """Defines a biome layer mapped to a height range on the terrain.

    Each biome specifies visual properties (color, texture), and
    density controls for vegetation, rocks, and grass coverage.
    """

    layer_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "temperate"
    min_height: float = 0.0
    max_height: float = 1.0
    base_color: Tuple[int, int, int, int] = (34, 139, 34, 255)
    texture_id: str = "default"
    tree_density: float = 0.3
    rock_density: float = 0.1
    grass_coverage: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "min_height": self.min_height,
            "max_height": self.max_height,
            "base_color": list(self.base_color),
            "texture_id": self.texture_id,
            "tree_density": self.tree_density,
            "rock_density": self.rock_density,
            "grass_coverage": self.grass_coverage,
        }


@dataclass
class TerrainStats:
    """Aggregated runtime statistics for a terrain instance."""

    total_chunks: int = 0
    loaded_chunks: int = 0
    modified_chunks: int = 0
    vertices_generated: int = 0
    memory_usage_mb: float = 0.0
    generation_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_chunks": self.total_chunks,
            "loaded_chunks": self.loaded_chunks,
            "modified_chunks": self.modified_chunks,
            "vertices_generated": self.vertices_generated,
            "memory_usage_mb": round(self.memory_usage_mb, 4),
            "generation_time_ms": round(self.generation_time_ms, 4),
        }


# ---------------------------------------------------------------------------
# Noise Utility Functions
# ---------------------------------------------------------------------------


def _hash_coords(x: int, y: int, seed: int = 0) -> float:
    """Simple coordinate hash returning a pseudo-random float in [0, 1)."""
    h = seed
    h = (h * 374761393 + x * 668265263) & 0xFFFFFFFF
    h = (h * 668265263 + y * 1274126177) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0x7FFFFFFF) / 0x7FFFFFFF


def _smooth_noise(x: float, z: float, seed: int = 0) -> float:
    """Seeded 2D smooth value noise using coordinate hashing and bilinear interpolation."""
    ix = int(math.floor(x))
    iz = int(math.floor(z))
    fx = x - ix
    fz = z - iz

    # Smoothstep for interpolation
    sx = fx * fx * (3.0 - 2.0 * fx)
    sz = fz * fz * (3.0 - 2.0 * fz)

    n00 = _hash_coords(ix, iz, seed)
    n10 = _hash_coords(ix + 1, iz, seed)
    n01 = _hash_coords(ix, iz + 1, seed)
    n11 = _hash_coords(ix + 1, iz + 1, seed)

    nx0 = n00 + (n10 - n00) * sx
    nx1 = n01 + (n11 - n01) * sx

    return nx0 + (nx1 - nx0) * sz


def _fbm_noise(x: float, z: float, octaves: int, persistence: float,
               lacunarity: float, seed: int = 0) -> float:
    """Fractional Brownian Motion: layered octaves of smooth noise."""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0

    for i in range(octaves):
        value += _smooth_noise(x * frequency, z * frequency, seed + i * 1000) * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    return value / max_value


def _ridged_noise(x: float, z: float, octaves: int, persistence: float,
                  lacunarity: float, seed: int = 0) -> float:
    """Ridged multi-fractal noise: creates ridge-like features by inverting absolute noise."""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0
    prev = 1.0

    for i in range(octaves):
        n = abs(_smooth_noise(x * frequency, z * frequency, seed + i * 1000))
        n = 1.0 - n  # Invert to create ridges
        n *= n       # Sharpen ridges
        n *= prev    # Weight by previous octave
        prev = n
        value += n * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    return value / max_value


def _billow_noise(x: float, z: float, octaves: int, persistence: float,
                  lacunarity: float, seed: int = 0) -> float:
    """Billow noise: absolute value of smooth noise creates billowy cloud-like shapes."""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0

    for i in range(octaves):
        n = abs(_smooth_noise(x * frequency, z * frequency, seed + i * 1000)) * 2.0 - 1.0
        value += n * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    return value / max_value


def _voronoi_noise(x: float, z: float, seed: int = 0) -> float:
    """Voronoi (Worley) noise: distance to nearest random feature point."""
    ix = int(math.floor(x))
    iz = int(math.floor(z))
    fx = x - ix
    fz = z - iz

    min_dist = float('inf')

    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            nx = ix + dx
            nz = iz + dz
            # Generate feature point within cell
            rng = random.Random(_hash_coords(nx, nz, seed) * 1000000 + seed)
            px = nx + rng.random()
            pz = nz + rng.random()
            dist = math.sqrt((fx + ix - px) ** 2 + (fz + iz - pz) ** 2)
            if dist < min_dist:
                min_dist = dist

    # Normalize: max distance in a cell is sqrt(2)
    return min(min_dist / math.sqrt(2), 1.0)


# ---------------------------------------------------------------------------
# Terrain Generation Algorithms
# ---------------------------------------------------------------------------


def _generate_height_perlin(width: int, depth: int, octaves: int,
                             persistence: float, lacunarity: float,
                             seed: int, height_scale: float) -> List[List[float]]:
    """Generate heightmap using FBM (Perlin-like) noise."""
    heights: List[List[float]] = []
    for z in range(depth):
        row: List[float] = []
        for x in range(width):
            nx = x / width * 4.0
            nz = z / depth * 4.0
            h = _fbm_noise(nx, nz, octaves, persistence, lacunarity, seed)
            row.append(h * height_scale)
        heights.append(row)
    return heights


def _generate_height_simplex(width: int, depth: int, octaves: int,
                              persistence: float, lacunarity: float,
                              seed: int, height_scale: float) -> List[List[float]]:
    """Generate heightmap using simplex-like noise (coordinate hashing with FBM)."""
    heights: List[List[float]] = []
    # Skew factors for 2D simplex-like transform
    f2 = 0.5 * (math.sqrt(3.0) - 1.0)
    g2 = (3.0 - math.sqrt(3.0)) / 6.0

    for z in range(depth):
        row: List[float] = []
        for x in range(width):
            # Skew input coordinates for simplex-like lattice
            sx = x / width * 4.0
            sz = z / depth * 4.0
            s = (sx + sz) * f2
            i = math.floor(sx + s)
            j = math.floor(sz + s)
            t = (i + j) * g2
            x0 = sx - (i - t)
            z0 = sz - (j - t)
            # Use FBM on skewed coordinates for multi-octave simplex-like result
            h = _fbm_noise(x0 * 2.0 + i * 0.1, z0 * 2.0 + j * 0.1,
                           octaves, persistence, lacunarity, seed + 5000)
            row.append(h * height_scale)
        heights.append(row)
    return heights


def _generate_height_diamond_square(size: int, seed: int,
                                     height_scale: float) -> List[List[float]]:
    """Generate heightmap using the Diamond-Square algorithm.

    Requires size = 2^n + 1. The algorithm recursively subdivides
    the grid using diamond and square steps with random displacement.
    """
    # Find next power-of-two-plus-one >= requested size
    n = 1
    while (1 << n) + 1 < max(size, size):
        n += 1
    grid_size = (1 << n) + 1

    # Initialize grid
    grid: List[List[float]] = [[0.0] * grid_size for _ in range(grid_size)]
    rng = random.Random(seed)

    # Set corner seeds
    grid[0][0] = rng.uniform(-1.0, 1.0) * height_scale
    grid[0][grid_size - 1] = rng.uniform(-1.0, 1.0) * height_scale
    grid[grid_size - 1][0] = rng.uniform(-1.0, 1.0) * height_scale
    grid[grid_size - 1][grid_size - 1] = rng.uniform(-1.0, 1.0) * height_scale

    step = grid_size - 1
    roughness = 0.65

    while step > 1:
        half = step // 2

        # Diamond step
        for y in range(0, grid_size - 1, step):
            for x in range(0, grid_size - 1, step):
                avg = (grid[y][x] + grid[y][x + step] +
                       grid[y + step][x] + grid[y + step][x + step]) / 4.0
                grid[y + half][x + half] = avg + rng.uniform(-1.0, 1.0) * step * roughness

        # Square step
        for y in range(0, grid_size, half):
            for x in range((y + half) % step, grid_size, half):
                total = 0.0
                count = 0
                if x >= half:
                    total += grid[y][x - half]
                    count += 1
                if x + half < grid_size:
                    total += grid[y][x + half]
                    count += 1
                if y >= half:
                    total += grid[y - half][x]
                    count += 1
                if y + half < grid_size:
                    total += grid[y + half][x]
                    count += 1
                avg = total / count
                grid[y][x] = avg + rng.uniform(-1.0, 1.0) * step * roughness

        step //= 2

    # Normalize and then crop/extract to requested size
    min_h = min(min(row) for row in grid)
    max_h = max(max(row) for row in grid)
    h_range = max_h - min_h if max_h != min_h else 1.0

    # Extract requested portion
    result: List[List[float]] = []
    for z in range(size):
        row: List[float] = []
        for x in range(size):
            z_idx = min(z, grid_size - 1)
            x_idx = min(x, grid_size - 1)
            normalized = (grid[z_idx][x_idx] - min_h) / h_range
            row.append(normalized * height_scale)
        result.append(row)
    return result


def _generate_height_voronoi(width: int, depth: int, seed: int,
                              height_scale: float) -> List[List[float]]:
    """Generate heightmap using Voronoi/Worley noise."""
    heights: List[List[float]] = []
    for z in range(depth):
        row: List[float] = []
        for x in range(width):
            nx = x / width * 5.0
            nz = z / depth * 5.0
            h = _voronoi_noise(nx, nz, seed)
            # Invert so cell centers are peaks
            row.append((1.0 - h) * height_scale)
        heights.append(row)
    return heights


def _generate_height_ridged(width: int, depth: int, octaves: int,
                             persistence: float, lacunarity: float,
                             seed: int, height_scale: float) -> List[List[float]]:
    """Generate heightmap using ridged multi-fractal noise."""
    heights: List[List[float]] = []
    for z in range(depth):
        row: List[float] = []
        for x in range(width):
            nx = x / width * 4.0
            nz = z / depth * 4.0
            h = _ridged_noise(nx, nz, octaves, persistence, lacunarity, seed)
            row.append(h * height_scale)
        heights.append(row)
    return heights


def _generate_height_billow(width: int, depth: int, octaves: int,
                             persistence: float, lacunarity: float,
                             seed: int, height_scale: float) -> List[List[float]]:
    """Generate heightmap using billow noise."""
    heights: List[List[float]] = []
    for z in range(depth):
        row: List[float] = []
        for x in range(width):
            nx = x / width * 4.0
            nz = z / depth * 4.0
            h = _billow_noise(nx, nz, octaves, persistence, lacunarity, seed)
            row.append(h * height_scale)
        heights.append(row)
    return heights


# ---------------------------------------------------------------------------
# EngineTerrainSystem — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class EngineTerrainSystem:
    """
    Comprehensive terrain generation and management system.

    Provides procedural terrain generation using multiple noise algorithms,
    chunk-based streaming, erosion simulation, biome-based texture layering,
    and interactive terrain editing tools.

    Thread-safe via a reentrant lock. Use get_terrain_system() or
    EngineTerrainSystem.get_instance() to obtain the singleton instance.

    Usage:
        ts = get_terrain_system()
        config = ts.create_config(width=512, depth=512, height_scale=200.0,
                                   seed=12345, algorithm=TerrainAlgorithm.PERLIN)
        chunks = ts.generate_terrain(config.config_id)
        height = ts.get_height_at(config.config_id, 100.0, 200.0)
    """

    _instance: Optional["EngineTerrainSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineTerrainSystem":
        """Thread-safe singleton construction with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialize()
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineTerrainSystem":
        """Return the global singleton; create it if necessary."""
        return cls()

    def _initialize(self) -> None:
        """Initialize internal state after construction."""
        self._configs: Dict[str, TerrainConfig] = {}
        self._chunks: Dict[str, Dict[Tuple[int, int], TerrainChunk]] = {}
        self._erosion_settings: Dict[str, ErosionSettings] = {}
        self._total_configs_created: int = 0
        self._total_chunks_generated: int = 0
        self._total_vertices: int = 0

    # ------------------------------------------------------------------
    # Configuration Management
    # ------------------------------------------------------------------

    def create_config(
        self,
        width: int = 256,
        depth: int = 256,
        height_scale: float = 100.0,
        seed: int = 42,
        algorithm: TerrainAlgorithm = TerrainAlgorithm.PERLIN,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
    ) -> TerrainConfig:
        """Create a new terrain configuration and return its descriptor.

        Args:
            width: Width of the terrain grid in vertices.
            depth: Depth of the terrain grid in vertices.
            height_scale: Maximum height amplitude.
            seed: Random seed for deterministic generation.
            algorithm: Noise algorithm to use for generation.
            octaves: Number of noise octaves for fractal detail.
            persistence: Amplitude multiplier per octave.
            lacunarity: Frequency multiplier per octave.

        Returns:
            A new TerrainConfig instance.
        """
        with self._lock:
            config = TerrainConfig(
                name=f"terrain_{self._total_configs_created + 1}",
                width=width,
                depth=depth,
                height_scale=height_scale,
                seed=seed,
                algorithm=algorithm,
                octaves=octaves,
                persistence=persistence,
                lacunarity=lacunarity,
            )
            self._configs[config.config_id] = config
            self._chunks[config.config_id] = {}
            self._total_configs_created += 1
            return config

    def list_configs(self) -> List[TerrainConfig]:
        """Return all registered terrain configurations."""
        with self._lock:
            return list(self._configs.values())

    def delete_config(self, config_id: str) -> bool:
        """Remove a terrain configuration and all associated chunks.

        Args:
            config_id: The configuration to delete.

        Returns:
            True if the config was found and deleted, False otherwise.
        """
        with self._lock:
            if config_id not in self._configs:
                return False
            del self._configs[config_id]
            self._chunks.pop(config_id, None)
            return True

    def clone_config(self, config_id: str, new_name: str) -> Optional[TerrainConfig]:
        """Create a copy of an existing terrain configuration.

        Args:
            config_id: The source configuration to clone.
            new_name: Name for the cloned configuration.

        Returns:
            The cloned TerrainConfig, or None if the source is not found.
        """
        with self._lock:
            source = self._configs.get(config_id)
            if source is None:
                return None
            cloned = TerrainConfig(
                name=new_name,
                width=source.width,
                depth=source.depth,
                height_scale=source.height_scale,
                seed=source.seed,
                algorithm=source.algorithm,
                octaves=source.octaves,
                persistence=source.persistence,
                lacunarity=source.lacunarity,
                biome_layers=list(source.biome_layers),
                chunk_size=source.chunk_size,
            )
            self._configs[cloned.config_id] = cloned
            self._chunks[cloned.config_id] = {}
            self._total_configs_created += 1
            return cloned

    # ------------------------------------------------------------------
    # Terrain Generation
    # ------------------------------------------------------------------

    def generate_terrain(self, config_id: str) -> List[TerrainChunk]:
        """Generate all terrain chunks for a given configuration.

        The terrain is split into square chunks of config.chunk_size,
        each containing its own height data sub-grid.

        Args:
            config_id: The configuration to generate terrain for.

        Returns:
            List of generated TerrainChunk instances.
        """
        config = self._configs.get(config_id)
        if config is None:
            return []

        t_start = _time_module.time()

        with self._lock:
            # Generate full heightmap
            if config.algorithm == TerrainAlgorithm.DIAMOND_SQUARE:
                full_heights = _generate_height_diamond_square(
                    config.width, config.seed, config.height_scale
                )
            elif config.algorithm == TerrainAlgorithm.SIMPLEX:
                full_heights = _generate_height_simplex(
                    config.width, config.depth, config.octaves,
                    config.persistence, config.lacunarity,
                    config.seed, config.height_scale,
                )
            elif config.algorithm == TerrainAlgorithm.VORONOI:
                full_heights = _generate_height_voronoi(
                    config.width, config.depth, config.seed, config.height_scale,
                )
            elif config.algorithm == TerrainAlgorithm.RIDGED:
                full_heights = _generate_height_ridged(
                    config.width, config.depth, config.octaves,
                    config.persistence, config.lacunarity,
                    config.seed, config.height_scale,
                )
            elif config.algorithm == TerrainAlgorithm.BILLOW:
                full_heights = _generate_height_billow(
                    config.width, config.depth, config.octaves,
                    config.persistence, config.lacunarity,
                    config.seed, config.height_scale,
                )
            else:
                full_heights = _generate_height_perlin(
                    config.width, config.depth, config.octaves,
                    config.persistence, config.lacunarity,
                    config.seed, config.height_scale,
                )

            # Split into chunks
            chunk_map: Dict[Tuple[int, int], TerrainChunk] = {}
            cs = config.chunk_size
            chunks_x = (config.width + cs - 1) // cs
            chunks_z = (config.depth + cs - 1) // cs

            for cz in range(chunks_z):
                for cx in range(chunks_x):
                    origin_x = cx * cs
                    origin_z = cz * cs
                    chunk_data: List[List[float]] = []
                    for lz in range(cs):
                        gz = origin_z + lz
                        if gz >= config.depth:
                            break
                        row: List[float] = []
                        for lx in range(cs):
                            gx = origin_x + lx
                            if gx >= config.width:
                                break
                            row.append(full_heights[gz][gx])
                        chunk_data.append(row)

                    chunk = TerrainChunk(
                        config_id=config_id,
                        origin_x=origin_x,
                        origin_z=origin_z,
                        chunk_size=cs,
                        height_data=chunk_data,
                        state=ChunkState.LOADED,
                    )
                    key = (origin_x, origin_z)
                    chunk_map[key] = chunk
                    self._total_chunks_generated += 1

            self._chunks[config_id] = chunk_map
            self._total_vertices += config.width * config.depth

            chunks = list(chunk_map.values())

        # Compute approximate memory usage
        bytes_per_float = 8
        per_chunk_mem = cs * cs * bytes_per_float
        total_mem = len(chunks) * per_chunk_mem / (1024.0 * 1024.0)

        t_end = _time_module.time()
        config.generation_time_ms = (t_end - t_start) * 1000.0
        config.memory_usage_mb = total_mem

        return chunks

    # ------------------------------------------------------------------
    # Chunk Access
    # ------------------------------------------------------------------

    def get_chunk(self, config_id: str, origin_x: int, origin_z: int) -> Optional[TerrainChunk]:
        """Retrieve a specific terrain chunk by its origin coordinates.

        Args:
            config_id: The terrain configuration.
            origin_x: X origin of the chunk in world space.
            origin_z: Z origin of the chunk in world space.

        Returns:
            The TerrainChunk if found, None otherwise.
        """
        chunk_map = self._chunks.get(config_id, {})
        return chunk_map.get((origin_x, origin_z))

    def get_height_at(self, config_id: str, world_x: float, world_z: float) -> float:
        """Sample the terrain height at any world-space position.

        Uses bilinear interpolation within the chunk's local height grid
        for smooth sampling between vertices.

        Args:
            config_id: The terrain configuration.
            world_x: World-space X coordinate.
            world_z: World-space Z coordinate.

        Returns:
            Interpolated height value at the given position.
        """
        config = self._configs.get(config_id)
        if config is None:
            return 0.0

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return 0.0

        ix = int(math.floor(world_x))
        iz = int(math.floor(world_z))

        if ix < 0 or ix >= config.width or iz < 0 or iz >= config.depth:
            return 0.0

        # Find which chunk contains this coordinate
        cs = config.chunk_size
        chunk_ox = (ix // cs) * cs
        chunk_oz = (iz // cs) * cs
        chunk = chunk_map.get((chunk_ox, chunk_oz))
        if chunk is None or not chunk.height_data:
            return 0.0

        local_x = ix - chunk_ox
        local_z = iz - chunk_oz

        if (local_z >= len(chunk.height_data) or
                local_x >= len(chunk.height_data[0]) if chunk.height_data else True):
            return 0.0

        # Bilinear interpolation
        fx = world_x - ix
        fz = world_z - iz

        h00 = chunk.height_data[local_z][local_x]
        h10 = h00
        h01 = h00
        h11 = h00

        if local_x + 1 < len(chunk.height_data[0]):
            h10 = chunk.height_data[local_z][local_x + 1]
        if local_z + 1 < len(chunk.height_data):
            h01 = chunk.height_data[local_z + 1][local_x]
        if (local_x + 1 < len(chunk.height_data[0]) and
                local_z + 1 < len(chunk.height_data)):
            h11 = chunk.height_data[local_z + 1][local_x + 1]

        h0 = h00 + (h10 - h00) * fx
        h1 = h01 + (h11 - h01) * fx
        return h0 + (h1 - h0) * fz

    # ------------------------------------------------------------------
    # Terrain Editing
    # ------------------------------------------------------------------

    def set_height_at(self, config_id: str, world_x: float, world_z: float,
                       new_height: float) -> bool:
        """Edit the terrain height at a specific world position.

        Args:
            config_id: The terrain configuration.
            world_x: World-space X coordinate.
            world_z: World-space Z coordinate.
            new_height: New height value to set.

        Returns:
            True if the edit was applied, False if out of bounds.
        """
        config = self._configs.get(config_id)
        if config is None:
            return False

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return False

        ix = int(math.floor(world_x))
        iz = int(math.floor(world_z))

        if ix < 0 or ix >= config.width or iz < 0 or iz >= config.depth:
            return False

        cs = config.chunk_size
        chunk_ox = (ix // cs) * cs
        chunk_oz = (iz // cs) * cs
        chunk = chunk_map.get((chunk_ox, chunk_oz))
        if chunk is None or not chunk.height_data:
            return False

        local_x = ix - chunk_ox
        local_z = iz - chunk_oz

        if (local_z < len(chunk.height_data) and
                local_x < len(chunk.height_data[0])):
            with self._lock:
                chunk.height_data[local_z][local_x] = new_height
                chunk.state = ChunkState.MODIFIED
            return True
        return False

    def flatten_area(self, config_id: str, center_x: float, center_z: float,
                      radius: float) -> List[TerrainChunk]:
        """Flatten a circular area of terrain to the average height within the radius.

        Args:
            config_id: The terrain configuration.
            center_x: World X center of the flatten area.
            center_z: World Z center of the flatten area.
            radius: Radius of the area to flatten.

        Returns:
            List of chunks that were modified.
        """
        config = self._configs.get(config_id)
        if config is None:
            return []

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return []

        # Compute average height within the circle
        heights: List[float] = []
        r_int = int(math.ceil(radius))
        for dz in range(-r_int, r_int + 1):
            for dx in range(-r_int, r_int + 1):
                if math.sqrt(dx * dx + dz * dz) <= radius:
                    wx = int(center_x) + dx
                    wz = int(center_z) + dz
                    if 0 <= wx < config.width and 0 <= wz < config.depth:
                        h = self.get_height_at(config_id, float(wx), float(wz))
                        heights.append(h)

        if not heights:
            return []

        avg_height = sum(heights) / len(heights)
        modified_chunks: Dict[str, TerrainChunk] = {}

        with self._lock:
            for dz in range(-r_int, r_int + 1):
                for dx in range(-r_int, r_int + 1):
                    if math.sqrt(dx * dx + dz * dz) <= radius:
                        wx = int(center_x) + dx
                        wz = int(center_z) + dz
                        if 0 <= wx < config.width and 0 <= wz < config.depth:
                            cs = config.chunk_size
                            cox = (wx // cs) * cs
                            coz = (wz // cs) * cs
                            chunk = chunk_map.get((cox, coz))
                            if chunk and chunk.height_data:
                                lx = wx - cox
                                lz = wz - coz
                                if (lz < len(chunk.height_data) and
                                        lx < len(chunk.height_data[0])):
                                    chunk.height_data[lz][lx] = avg_height
                                    chunk.state = ChunkState.MODIFIED
                                    modified_chunks[chunk.chunk_id] = chunk

        return list(modified_chunks.values())

    def raise_area(self, config_id: str, center_x: float, center_z: float,
                    radius: float, amount: float) -> List[TerrainChunk]:
        """Raise a circular area of terrain by a specified amount.

        Args:
            config_id: The terrain configuration.
            center_x: World X center of the raise area.
            center_z: World Z center of the raise area.
            radius: Radius of the area to affect.
            amount: Amount to add to the existing height.

        Returns:
            List of chunks that were modified.
        """
        config = self._configs.get(config_id)
        if config is None:
            return []

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return []

        r_int = int(math.ceil(radius))
        modified_chunks: Dict[str, TerrainChunk] = {}

        with self._lock:
            for dz in range(-r_int, r_int + 1):
                for dx in range(-r_int, r_int + 1):
                    dist = math.sqrt(dx * dx + dz * dz)
                    if dist <= radius:
                        wx = int(center_x) + dx
                        wz = int(center_z) + dz
                        if 0 <= wx < config.width and 0 <= wz < config.depth:
                            cs = config.chunk_size
                            cox = (wx // cs) * cs
                            coz = (wz // cs) * cs
                            chunk = chunk_map.get((cox, coz))
                            if chunk and chunk.height_data:
                                lx = wx - cox
                                lz = wz - coz
                                if (lz < len(chunk.height_data) and
                                        lx < len(chunk.height_data[0])):
                                    # Falloff at edges
                                    falloff = 1.0 - (dist / radius)
                                    falloff = max(0.0, falloff * falloff)
                                    chunk.height_data[lz][lx] += amount * falloff
                                    chunk.state = ChunkState.MODIFIED
                                    modified_chunks[chunk.chunk_id] = chunk

        return list(modified_chunks.values())

    def generate_island(self, config_id: str,
                         shore_threshold: float = 0.3) -> List[TerrainChunk]:
        """Mask terrain below sea level to create an island.

        Heights below shore_threshold * height_scale are clamped to zero,
        and regions near the edges of the terrain are tapered to create
        a natural island shape.

        Args:
            config_id: The terrain configuration.
            shore_threshold: Fraction of max height that defines sea level.

        Returns:
            List of modified TerrainChunk instances.
        """
        config = self._configs.get(config_id)
        if config is None:
            return []

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return []

        sea_level = shore_threshold * config.height_scale
        half_w = config.width / 2.0
        half_d = config.depth / 2.0
        max_edge_dist = math.sqrt(half_w * half_w + half_d * half_d)

        modified_chunks: Dict[str, TerrainChunk] = {}

        with self._lock:
            for chunk in chunk_map.values():
                if not chunk.height_data:
                    continue
                modified = False
                for lz in range(len(chunk.height_data)):
                    row = chunk.height_data[lz]
                    for lx in range(len(row)):
                        wx = chunk.origin_x + lx
                        wz = chunk.origin_z + lz

                        # Distance falloff from center
                        dx = (wx - half_w) / half_w
                        dz = (wz - half_d) / half_d
                        edge_dist = math.sqrt(dx * dx + dz * dz)
                        edge_falloff = max(0.0, 1.0 - edge_dist)

                        if row[lx] < sea_level:
                            row[lx] = 0.0
                            modified = True
                        else:
                            # Taper heights near edges
                            row[lx] *= edge_falloff
                            modified = True

                if modified:
                    chunk.state = ChunkState.MODIFIED
                    modified_chunks[chunk.chunk_id] = chunk

        return list(modified_chunks.values())

    # ------------------------------------------------------------------
    # Erosion Simulation
    # ------------------------------------------------------------------

    def apply_erosion(self, config_id: str,
                       erosion_settings: ErosionSettings) -> List[TerrainChunk]:
        """Apply erosion simulation to the terrain.

        Simulates hydraulic erosion using an iterative particle-based approach.
        Each particle (raindrop) picks up sediment as it flows downhill and
        deposits it in flatter areas.

        Args:
            config_id: The terrain configuration to erode.
            erosion_settings: Parameters controlling the erosion simulation.

        Returns:
            List of chunks that were modified by the erosion pass.
        """
        config = self._configs.get(config_id)
        if config is None:
            return []

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return []

        cs = config.chunk_size
        width = config.width
        depth = config.depth

        # Flatten heightmap into a single 2D array for erosion simulation
        heights: List[List[float]] = [[0.0] * width for _ in range(depth)]
        for chunk in chunk_map.values():
            if not chunk.height_data:
                continue
            for lz in range(len(chunk.height_data)):
                for lx in range(len(chunk.height_data[lz])):
                    wx = chunk.origin_x + lx
                    wz = chunk.origin_z + lz
                    if wz < depth and wx < width:
                        heights[wz][wx] = chunk.height_data[lz][lx]

        rng = random.Random(config.seed + 9999)
        er = erosion_settings.erosion_rate
        dr = erosion_settings.deposition_rate
        ev = erosion_settings.evaporation_rate

        for _ in range(erosion_settings.iterations):
            # Spawn raindrop at random position
            px = rng.randint(1, width - 2)
            pz = rng.randint(1, depth - 2)
            sediment = 0.0
            water = 1.0

            # Particle lifetime: travel until water evaporates or edge reached
            for _step in range(200):
                if water <= 0.0:
                    break

                ipx = int(px)
                ipz = int(pz)

                if ipx <= 0 or ipx >= width - 1 or ipz <= 0 or ipz >= depth - 1:
                    break

                # Compute gradient (downhill direction)
                h_center = heights[ipz][ipx]
                h_right = heights[ipz][ipx + 1]
                h_left = heights[ipz][ipx - 1]
                h_down = heights[ipz + 1][ipx]
                h_up = heights[ipz - 1][ipx]

                grad_x = (h_right - h_left) * 0.5
                grad_z = (h_down - h_up) * 0.5
                grad_mag = math.sqrt(grad_x * grad_x + grad_z * grad_z)

                if grad_mag < 0.0001:
                    # Flat area: deposit sediment
                    deposit = sediment * dr
                    heights[ipz][ipx] += deposit
                    sediment -= deposit
                else:
                    # Move downhill
                    px += grad_x / (grad_mag + 0.0001)
                    pz += grad_z / (grad_mag + 0.0001)

                    # Erode
                    height_diff = h_center - heights[int(pz)][int(px)]
                    if height_diff > 0:
                        erode_amount = min(height_diff * er, water * erosion_settings.rain_amount)
                        heights[ipz][ipx] -= erode_amount
                        sediment += erode_amount
                    else:
                        # Deposit
                        deposit_amount = min(abs(height_diff) * dr, sediment)
                        heights[ipz][ipx] += deposit_amount
                        sediment -= deposit_amount

                water -= ev

        # Write modified heights back to chunks
        modified_chunks: Dict[str, TerrainChunk] = {}
        with self._lock:
            for chunk in chunk_map.values():
                if not chunk.height_data:
                    continue
                modified = False
                for lz in range(len(chunk.height_data)):
                    for lx in range(len(chunk.height_data[lz])):
                        wx = chunk.origin_x + lx
                        wz = chunk.origin_z + lz
                        if wz < depth and wx < width:
                            old_h = chunk.height_data[lz][lx]
                            new_h = heights[wz][wx]
                            if abs(old_h - new_h) > 0.001:
                                chunk.height_data[lz][lx] = new_h
                                modified = True
                if modified:
                    chunk.state = ChunkState.MODIFIED
                    modified_chunks[chunk.chunk_id] = chunk

        self._erosion_settings[erosion_settings.settings_id] = erosion_settings
        return list(modified_chunks.values())

    # ------------------------------------------------------------------
    # Biome Layer Management
    # ------------------------------------------------------------------

    def add_biome_layer(self, config_id: str, biome: BiomeLayer) -> Optional[TerrainConfig]:
        """Add a biome layer to a terrain configuration.

        Args:
            config_id: The terrain configuration.
            biome: The BiomeLayer to add.

        Returns:
            The updated TerrainConfig, or None if not found.
        """
        with self._lock:
            config = self._configs.get(config_id)
            if config is None:
                return None
            config.biome_layers.append(biome)
            return config

    # ------------------------------------------------------------------
    # Texture Weight Computation
    # ------------------------------------------------------------------

    def generate_texture_weights(self, config_id: str) -> Dict[str, Any]:
        """Compute texture blending weights based on height and slope.

        Assigns weight values to each texture layer type based on the
        terrain's height distribution and slope angles.

        Args:
            config_id: The terrain configuration.

        Returns:
            Dict mapping texture layer names to weight values and metadata.
        """
        config = self._configs.get(config_id)
        if config is None:
            return {}

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return {}

        # Collect height statistics
        all_heights: List[float] = []
        for chunk in chunk_map.values():
            if not chunk.height_data:
                continue
            for row in chunk.height_data:
                all_heights.extend(row)

        if not all_heights:
            return {}

        min_h = min(all_heights)
        max_h = max(all_heights)
        h_range = max_h - min_h if max_h != min_h else 1.0

        # Compute slope statistics
        slopes: List[float] = []
        for chunk in chunk_map.values():
            if not chunk.height_data or len(chunk.height_data) < 2:
                continue
            rows = chunk.height_data
            for lz in range(len(rows) - 1):
                for lx in range(len(rows[lz]) - 1):
                    h00 = rows[lz][lx]
                    h10 = rows[lz][lx + 1]
                    h01 = rows[lz + 1][lx]
                    dx = abs(h10 - h00)
                    dz = abs(h01 - h00)
                    slopes.append(max(dx, dz))

        avg_slope = sum(slopes) / len(slopes) if slopes else 0.0

        # Assign weights based on terrain characteristics
        weights: Dict[str, float] = {
            TextureLayer.BASE.value: 0.3,
            TextureLayer.SLOPE.value: min(1.0, avg_slope / (h_range * 0.01 + 0.001)),
            TextureLayer.HEIGHT.value: 0.25,
            TextureLayer.SPLAT.value: 0.15,
            TextureLayer.DETAIL.value: 0.1,
        }

        # Normalize
        total = sum(weights.values()) or 1.0
        for key in weights:
            weights[key] = round(weights[key] / total, 4)

        with self._lock:
            for chunk in chunk_map.values():
                chunk.texture_weights = dict(weights)

        return {
            "config_id": config_id,
            "weights": weights,
            "terrain_stats": {
                "min_height": round(min_h, 2),
                "max_height": round(max_h, 2),
                "avg_slope": round(avg_slope, 4),
            },
        }

    # ------------------------------------------------------------------
    # Chunk Streaming
    # ------------------------------------------------------------------

    def stream_chunk(self, config_id: str, chunk_x: int,
                      chunk_z: int) -> Optional[TerrainChunk]:
        """Load or unload a chunk based on its current state.

        UNLOADED or LOADING chunks become LOADED; LOADED chunks become
        UNLOADED (simulating streaming memory management).

        Args:
            config_id: The terrain configuration.
            chunk_x: X-origin of the chunk.
            chunk_z: Z-origin of the chunk.

        Returns:
            The chunk in its new state, or None if not found.
        """
        chunk_map = self._chunks.get(config_id, {})
        chunk = chunk_map.get((chunk_x, chunk_z))
        if chunk is None:
            return None

        with self._lock:
            if chunk.state in (ChunkState.UNLOADED, ChunkState.LOADING):
                chunk.state = ChunkState.LOADED
            elif chunk.state == ChunkState.LOADED:
                chunk.state = ChunkState.UNLOADED
            elif chunk.state == ChunkState.STREAMING:
                chunk.state = ChunkState.LOADED
            # Modified chunks preserve their state
            return chunk

    def update_lod(self, config_id: str, camera_x: float, camera_z: float,
                    view_distance: float) -> List[TerrainChunk]:
        """Update LOD levels for all chunks based on camera distance.

        Chunks closer than view_distance/3 get LOD 0 (full detail),
        chunks within view_distance get LOD 1 (half detail),
        chunks beyond get LOD 2 (quarter detail) and are set to STREAMING.

        Args:
            config_id: The terrain configuration.
            camera_x: Camera world X position.
            camera_z: Camera world Z position.
            view_distance: Maximum visible distance.

        Returns:
            List of chunks with updated LOD levels.
        """
        config = self._configs.get(config_id)
        if config is None:
            return []

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return []

        updated: List[TerrainChunk] = []
        near_dist = view_distance / 3.0
        mid_dist = view_distance
        cs = config.chunk_size

        with self._lock:
            for chunk in chunk_map.values():
                # Compute chunk center
                cx = chunk.origin_x + cs / 2.0
                cz = chunk.origin_z + cs / 2.0
                dx = cx - camera_x
                dz = cz - camera_z
                dist = math.sqrt(dx * dx + dz * dz)

                old_lod = chunk.lod_level
                old_state = chunk.state

                if dist <= near_dist:
                    chunk.lod_level = 0
                    if chunk.state == ChunkState.STREAMING:
                        chunk.state = ChunkState.LOADED
                elif dist <= mid_dist:
                    chunk.lod_level = 1
                    if chunk.state == ChunkState.STREAMING:
                        chunk.state = ChunkState.LOADED
                else:
                    chunk.lod_level = 2
                    if chunk.state == ChunkState.LOADED:
                        chunk.state = ChunkState.STREAMING

                if chunk.lod_level != old_lod or chunk.state != old_state:
                    updated.append(chunk)

        return updated

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def compute_slope_at(self, config_id: str, world_x: float,
                          world_z: float) -> float:
        """Compute the slope steepness at a given world position.

        Uses central difference approximation to calculate the gradient
        magnitude, which represents how steep the terrain is at that point.

        Args:
            config_id: The terrain configuration.
            world_x: World X coordinate.
            world_z: World Z coordinate.

        Returns:
            Slope steepness as a float (0 = flat, higher = steeper).
        """
        config = self._configs.get(config_id)
        if config is None:
            return 0.0

        step = 1.0
        h_center = self.get_height_at(config_id, world_x, world_z)
        h_right = self.get_height_at(config_id, world_x + step, world_z)
        h_left = self.get_height_at(config_id, world_x - step, world_z)
        h_forward = self.get_height_at(config_id, world_x, world_z + step)
        h_back = self.get_height_at(config_id, world_x, world_z - step)

        dz_dx = (h_right - h_left) / (2.0 * step)
        dz_dz = (h_forward - h_back) / (2.0 * step)

        return math.sqrt(dz_dx * dz_dx + dz_dz * dz_dz)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_heightmap(self, config_id: str,
                          file_format: str = "raw") -> str:
        """Simulated heightmap export that returns a description of the output.

        Args:
            config_id: The terrain configuration to export.
            file_format: Target format (raw, png, exr, csv).

        Returns:
            A string describing the export operation.
        """
        config = self._configs.get(config_id)
        if config is None:
            return "export failed: config not found"

        chunk_map = self._chunks.get(config_id, {})
        if not chunk_map:
            return "export failed: no terrain data generated"

        total_heights = config.width * config.depth
        return (
            f"Exported heightmap '{config.name}' as {file_format.upper()}: "
            f"{config.width}x{config.depth}, {total_heights} samples, "
            f"height_scale={config.height_scale:.1f}, "
            f"seed={config.seed}, chunks={len(chunk_map)}"
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self, config_id: str) -> Optional[TerrainStats]:
        """Compute runtime statistics for a terrain instance.

        Args:
            config_id: The terrain configuration.

        Returns:
            A TerrainStats snapshot, or None if the config is not found.
        """
        config = self._configs.get(config_id)
        if config is None:
            return None

        chunk_map = self._chunks.get(config_id, {})

        loaded = sum(1 for c in chunk_map.values()
                      if c.state == ChunkState.LOADED)
        modified = sum(1 for c in chunk_map.values()
                        if c.state == ChunkState.MODIFIED)

        # Approximate memory: each height float = 8 bytes
        total_floats = 0
        for c in chunk_map.values():
            for row in c.height_data:
                total_floats += len(row)

        mem_mb = total_floats * 8.0 / (1024.0 * 1024.0)

        return TerrainStats(
            total_chunks=len(chunk_map),
            loaded_chunks=loaded,
            modified_chunks=modified,
            vertices_generated=config.width * config.depth,
            memory_usage_mb=mem_mb,
            generation_time_ms=getattr(config, 'generation_time_ms', 0.0),
        )


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_terrain_system() -> EngineTerrainSystem:
    """Return the singleton EngineTerrainSystem instance."""
    return EngineTerrainSystem.get_instance()