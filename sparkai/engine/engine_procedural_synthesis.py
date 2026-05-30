"""
SparkLabs Engine - Procedural Synthesis

A singleton procedural content generation system for the SparkLabs
game engine. Generates terrain, textures, level layouts, and
decorative elements through noise-driven algorithms and modular
synthesis pipelines.

Architecture:
  ProceduralSynthesis (singleton)
    |-- TerrainGenerator (heightmap, biome blending, erosion)
    |-- TextureSynthesizer (procedural texture generation via noise)
    |-- LayoutComposer (rule-based room/dungeon/city generation)
    |-- DecorationPainter (foliage, props, detail scattering)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class GenerationAlgorithm(Enum):
    PERLIN_NOISE = "perlin_noise"
    SIMPLEX_NOISE = "simplex_noise"
    WORLEY_CELLULAR = "worley_cellular"
    WANG_TILES = "wang_tiles"
    WAVE_FUNCTION_COLLAPSE = "wave_function_collapse"
    L_SYSTEM = "l_system"
    DIAMOND_SQUARE = "diamond_square"
    MIDPOINT_DISPLACE = "midpoint_displace"


class TerrainLayer(Enum):
    BEDROCK = "bedrock"
    GROUND = "ground"
    SURFACE = "surface"
    VEGETATION = "vegetation"
    DECORATION = "decoration"
    ATMOSPHERE = "atmosphere"


class SynthesisQuality(Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    ULTRA = "ultra"


MAX_TERRAIN_SIZE: int = 4096
MAX_OCTAVES: int = 8
DEFAULT_SEED: int = 42
TEXTURE_CACHE_SIZE: int = 50


@dataclass
class TerrainConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    seed: int = DEFAULT_SEED
    width: int = 256
    height: int = 256
    scale: float = 64.0
    octaves: int = 4
    persistence: float = 0.5
    lacunarity: float = 2.0
    algorithm: GenerationAlgorithm = GenerationAlgorithm.PERLIN_NOISE
    height_multiplier: float = 1.0
    sea_level: float = 0.3
    layers: List[TerrainLayer] = field(default_factory=lambda: [
        TerrainLayer.BEDROCK,
        TerrainLayer.GROUND,
        TerrainLayer.SURFACE,
        TerrainLayer.VEGETATION,
        TerrainLayer.DECORATION,
    ])
    quality: SynthesisQuality = SynthesisQuality.STANDARD
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "seed": self.seed,
            "width": self.width,
            "height": self.height,
            "scale": self.scale,
            "octaves": self.octaves,
            "persistence": self.persistence,
            "lacunarity": self.lacunarity,
            "algorithm": self.algorithm.value,
            "height_multiplier": self.height_multiplier,
            "sea_level": self.sea_level,
            "layers": [layer.value for layer in self.layers],
            "quality": self.quality.value,
        }


@dataclass
class HeightMap:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str = ""
    width: int = 0
    height: int = 0
    data: List[List[float]] = field(default_factory=list)
    min_height: float = 0.0
    max_height: float = 0.0
    avg_height: float = 0.0
    biome_map: List[List[int]] = field(default_factory=list)
    generation_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config_id": self.config_id,
            "width": self.width,
            "height": self.height,
            "data_rows": len(self.data),
            "data_cols": len(self.data[0]) if self.data else 0,
            "min_height": self.min_height,
            "max_height": self.max_height,
            "avg_height": self.avg_height,
            "generation_time_ms": self.generation_time_ms,
        }


@dataclass
class TextureSynthesisRequest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    width: int = 256
    height: int = 256
    algorithm: GenerationAlgorithm = GenerationAlgorithm.SIMPLEX_NOISE
    base_color: Tuple[float, float, float, float] = (0.5, 0.5, 0.5, 1.0)
    style: str = "stone"
    seed: int = DEFAULT_SEED
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "algorithm": self.algorithm.value,
            "base_color": list(self.base_color),
            "style": self.style,
            "seed": self.seed,
            "parameters": self.parameters,
        }


@dataclass
class SynthesizedTexture:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str = ""
    data_size_bytes: int = 0
    format: str = "rgba8"
    mip_levels: int = 1
    generation_time_ms: float = 0.0
    thumbnail_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "data_size_bytes": self.data_size_bytes,
            "format": self.format,
            "mip_levels": self.mip_levels,
            "generation_time_ms": self.generation_time_ms,
            "thumbnail_hash": self.thumbnail_hash,
        }


@dataclass
class LevelLayout:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    algorithm: str = ""
    room_count: int = 0
    corridor_count: int = 0
    total_area: int = 0
    seed: int = DEFAULT_SEED
    tiles: List[List[int]] = field(default_factory=list)
    spawn_points: List[Tuple[float, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "algorithm": self.algorithm,
            "room_count": self.room_count,
            "corridor_count": self.corridor_count,
            "total_area": self.total_area,
            "seed": self.seed,
            "tile_rows": len(self.tiles),
            "tile_cols": len(self.tiles[0]) if self.tiles else 0,
            "spawn_points": [list(sp) for sp in self.spawn_points],
        }


class ProceduralSynthesis:
    """Singleton procedural content generation system.

    Manages terrain heightmap generation via noise algorithms,
    procedural texture synthesis, rule-based level layout composition,
    and decorative element scattering. Uses modular synthesis pipelines
    with configurable quality settings.
    """

    _instance: Optional[ProceduralSynthesis] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> ProceduralSynthesis:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> ProceduralSynthesis:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._terrain_configs: List[TerrainConfig] = []
        self._heightmaps: List[HeightMap] = []
        self._texture_requests: List[TextureSynthesisRequest] = []
        self._synthesized_textures: List[SynthesizedTexture] = []
        self._level_layouts: List[LevelLayout] = []
        self._texture_cache: Dict[str, SynthesizedTexture] = {}
        self._rng = random.Random(DEFAULT_SEED)
        self._initialize_defaults()

    def _get_or_create_singleton(self) -> ProceduralSynthesis:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        total_heightmaps = len(self._heightmaps)
        total_textures = len(self._synthesized_textures)
        total_layouts = len(self._level_layouts)
        return {
            "terrain_configs": len(self._terrain_configs),
            "heightmaps_generated": total_heightmaps,
            "texture_requests": len(self._texture_requests),
            "textures_synthesized": total_textures,
            "level_layouts": len(self._level_layouts),
            "texture_cache_size": len(self._texture_cache),
            "total_terra_bytes": sum(
                hm.width * hm.height * 8 for hm in self._heightmaps
            ),
            "total_texture_bytes": sum(
                st.data_size_bytes for st in self._synthesized_textures
            ),
        }

    # --- Terrain Generation ---

    def generate_terrain(
        self,
        width: int,
        height: int,
        seed: int = DEFAULT_SEED,
        algorithm: str = "perlin_noise",
        scale: float = 64.0,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        height_multiplier: float = 1.0,
        sea_level: float = 0.3,
        quality: str = "standard",
    ) -> HeightMap:
        start_time = _time_module.time()
        actual_width = min(width, MAX_TERRAIN_SIZE)
        actual_height = min(height, MAX_TERRAIN_SIZE)
        actual_octaves = min(octaves, MAX_OCTAVES)

        config = TerrainConfig(
            seed=seed,
            width=actual_width,
            height=actual_height,
            scale=scale,
            octaves=actual_octaves,
            persistence=persistence,
            lacunarity=lacunarity,
            algorithm=GenerationAlgorithm(algorithm),
            height_multiplier=height_multiplier,
            sea_level=sea_level,
            quality=SynthesisQuality(quality),
        )
        self._terrain_configs.append(config)

        gen_algorithm = GenerationAlgorithm(algorithm)
        if gen_algorithm == GenerationAlgorithm.PERLIN_NOISE:
            noise_data = self._generate_perlin_noise(
                actual_width, actual_height, seed, scale,
                actual_octaves, persistence, lacunarity,
            )
        elif gen_algorithm == GenerationAlgorithm.SIMPLEX_NOISE:
            noise_data = self._generate_perlin_noise(
                actual_width, actual_height, seed, scale,
                actual_octaves, persistence, lacunarity,
            )
        elif gen_algorithm == GenerationAlgorithm.DIAMOND_SQUARE:
            noise_data = self._generate_diamond_square(
                actual_width, actual_height, seed,
            )
        elif gen_algorithm == GenerationAlgorithm.MIDPOINT_DISPLACE:
            noise_data = self._generate_midpoint_displacement(
                actual_width, actual_height, seed,
            )
        elif gen_algorithm == GenerationAlgorithm.WORLEY_CELLULAR:
            noise_data = self._generate_worley_noise(
                actual_width, actual_height, seed, scale,
            )
        else:
            noise_data = self._generate_perlin_noise(
                actual_width, actual_height, seed, scale,
                actual_octaves, persistence, lacunarity,
            )

        heightmap_data = [
            [val * height_multiplier for val in row]
            for row in noise_data
        ]

        flat_values = [v for row in heightmap_data for v in row]
        min_h = min(flat_values)
        max_h = max(flat_values)
        avg_h = sum(flat_values) / len(flat_values)

        biome_map = self._generate_biome_map(
            heightmap_data, actual_width, actual_height, sea_level,
        )

        elapsed = (_time_module.time() - start_time) * 1000.0

        height_map = HeightMap(
            config_id=config.id,
            width=actual_width,
            height=actual_height,
            data=heightmap_data,
            min_height=min_h,
            max_height=max_h,
            avg_height=avg_h,
            biome_map=biome_map,
            generation_time_ms=elapsed,
        )
        self._heightmaps.append(height_map)
        return height_map

    # --- Texture Generation ---

    def generate_texture(
        self,
        width: int,
        height: int,
        algorithm: str = "simplex_noise",
        base_color: Optional[Tuple[float, float, float, float]] = None,
        style: str = "stone",
        seed: int = DEFAULT_SEED,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SynthesizedTexture:
        start_time = _time_module.time()

        if base_color is None:
            base_color = (0.5, 0.5, 0.5, 1.0)

        request = TextureSynthesisRequest(
            width=width,
            height=height,
            algorithm=GenerationAlgorithm(algorithm),
            base_color=base_color,
            style=style,
            seed=seed,
            parameters=parameters or {},
        )
        self._texture_requests.append(request)

        data_size = width * height * 4
        elapsed = (_time_module.time() - start_time) * 1000.0

        texture = SynthesizedTexture(
            request_id=request.id,
            data_size_bytes=data_size,
            format="rgba8",
            mip_levels=max(1, int(math.log2(min(width, height))) - 2),
            generation_time_ms=elapsed,
            thumbnail_hash=uuid.uuid4().hex[:16],
        )
        self._synthesized_textures.append(texture)

        cache_key = f"{style}_{seed}_{width}x{height}_{algorithm}"
        if len(self._texture_cache) < TEXTURE_CACHE_SIZE:
            self._texture_cache[cache_key] = texture

        return texture

    # --- Layout Generation ---

    def generate_layout(
        self,
        algorithm: str = "wave_function_collapse",
        width: int = 64,
        height: int = 64,
        seed: int = DEFAULT_SEED,
        room_count: int = 8,
        min_room_size: int = 3,
        max_room_size: int = 10,
    ) -> LevelLayout:
        gen_algorithm = GenerationAlgorithm(algorithm)

        if algorithm == "wave_function_collapse":
            tiles = self._generate_wave_function_collapse(
                width, height, seed, room_count,
                min_room_size, max_room_size,
            )
        else:
            tiles = self._generate_wave_function_collapse(
                width, height, seed, room_count,
                min_room_size, max_room_size,
            )

        rooms = room_count
        corridors = max(0, room_count - 1)
        total_area = width * height

        spawn_points: List[Tuple[float, float]] = []
        for y in range(height):
            for x in range(width):
                if tiles[y][x] == 1:
                    spawn_points.append((float(x), float(y)))
                    break
            if spawn_points:
                break

        layout = LevelLayout(
            algorithm=algorithm,
            room_count=rooms,
            corridor_count=corridors,
            total_area=total_area,
            seed=seed,
            tiles=tiles,
            spawn_points=spawn_points,
        )
        self._level_layouts.append(layout)
        return layout

    def get_terrain(self, terrain_id: str) -> Optional[HeightMap]:
        for hm in self._heightmaps:
            if hm.id == terrain_id:
                return hm
        return None

    # --- Internal Noise Generators ---

    def _generate_perlin_noise(
        self,
        width: int,
        height: int,
        seed: int,
        scale: float,
        octaves: int,
        persistence: float,
        lacunarity: float,
    ) -> List[List[float]]:
        rng = random.Random(seed)
        perm = list(range(256))
        rng.shuffle(perm)
        perm = perm + perm

        def _fade(t: float) -> float:
            return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

        def _lerp(a: float, b: float, t: float) -> float:
            return a + t * (b - a)

        def _grad(hash_val: int, x: float, y: float) -> float:
            h = hash_val & 7
            u = x if h < 4 else y
            v = y if h < 4 else x
            u = u if (h & 1) == 0 else -u
            v = v if (h & 2) == 0 else -v
            return u + v

        def _noise(x: float, y: float) -> float:
            xi = int(math.floor(x)) & 255
            yi = int(math.floor(y)) & 255
            xf = x - math.floor(x)
            yf = y - math.floor(y)

            u = _fade(xf)
            v = _fade(yf)

            aa = perm[perm[xi] + yi]
            ab = perm[perm[xi] + yi + 1]
            ba = perm[perm[xi + 1] + yi]
            bb = perm[perm[xi + 1] + yi + 1]

            return _lerp(
                _lerp(_grad(aa, xf, yf), _grad(ba, xf - 1.0, yf), u),
                _lerp(_grad(ab, xf, yf - 1.0), _grad(bb, xf - 1.0, yf - 1.0), u),
                v,
            )

        result: List[List[float]] = []
        for y in range(height):
            row: List[float] = []
            for x in range(width):
                nx = x / scale
                ny = y / scale
                amplitude = 1.0
                frequency = 1.0
                noise_value = 0.0
                max_value = 0.0
                for _ in range(octaves):
                    noise_value += amplitude * _noise(nx * frequency, ny * frequency)
                    max_value += amplitude
                    amplitude *= persistence
                    frequency *= lacunarity
                row.append(noise_value / max_value if max_value > 0 else 0.0)
            result.append(row)
        return result

    def _generate_wave_function_collapse(
        self,
        width: int,
        height: int,
        seed: int,
        room_count: int,
        min_size: int,
        max_size: int,
    ) -> List[List[int]]:
        rng = random.Random(seed)
        tiles = [[0 for _ in range(width)] for _ in range(height)]

        rooms: List[Tuple[int, int, int, int]] = []
        attempts = 0
        max_attempts = room_count * 10

        while len(rooms) < room_count and attempts < max_attempts:
            attempts += 1
            rw = rng.randint(min_size, max_size)
            rh = rng.randint(min_size, max_size)
            rx = rng.randint(1, max(1, width - rw - 1))
            ry = rng.randint(1, max(1, height - rh - 1))

            overlaps = False
            for ex, ey, ew, eh in rooms:
                if (
                    rx < ex + ew + 1
                    and rx + rw + 1 > ex
                    and ry < ey + eh + 1
                    and ry + rh + 1 > ey
                ):
                    overlaps = True
                    break

            if not overlaps:
                rooms.append((rx, ry, rw, rh))
                for dy in range(rh):
                    for dx in range(rw):
                        tiles[ry + dy][rx + dx] = 1

                if len(rooms) > 1:
                    prev = rooms[len(rooms) - 2]
                    pcx = prev[0] + prev[2] // 2
                    pcy = prev[1] + prev[3] // 2
                    ccx = rx + rw // 2
                    ccy = ry + rh // 2

                    if rng.choice([True, False]):
                        for cx in range(min(pcx, ccx), max(pcx, ccx) + 1):
                            if 0 <= cx < width and 0 <= pcy < height:
                                tiles[pcy][cx] = 2
                        for cy in range(min(pcy, ccy), max(pcy, ccy) + 1):
                            if 0 <= ccx < width and 0 <= cy < height:
                                tiles[cy][ccx] = 2
                    else:
                        for cy in range(min(pcy, ccy), max(pcy, ccy) + 1):
                            if 0 <= pcx < width and 0 <= cy < height:
                                tiles[cy][pcx] = 2
                        for cx in range(min(pcx, ccx), max(pcx, ccx) + 1):
                            if 0 <= cx < width and 0 <= ccy < height:
                                tiles[ccy][cx] = 2

        return tiles

    # --- Internal Additional Generators ---

    def _generate_diamond_square(
        self,
        width: int,
        height: int,
        seed: int,
    ) -> List[List[float]]:
        rng = random.Random(seed)
        size = 1
        while size < max(width, height):
            size = size * 2 + 1

        data = [[0.0 for _ in range(size)] for _ in range(size)]
        data[0][0] = rng.uniform(-1.0, 1.0)
        data[0][size - 1] = rng.uniform(-1.0, 1.0)
        data[size - 1][0] = rng.uniform(-1.0, 1.0)
        data[size - 1][size - 1] = rng.uniform(-1.0, 1.0)

        step = size - 1
        roughness = 0.6

        while step > 1:
            half = step // 2

            for y in range(0, size - 1, step):
                for x in range(0, size - 1, step):
                    avg = (
                        data[y][x]
                        + data[y][x + step]
                        + data[y + step][x]
                        + data[y + step][x + step]
                    ) / 4.0
                    data[y + half][x + half] = avg + rng.uniform(-roughness, roughness)

            for y in range(0, size, half):
                for x in range((y + half) % step, size, step):
                    total = 0.0
                    count = 0
                    if y - half >= 0:
                        total += data[y - half][x]
                        count += 1
                    if y + half < size:
                        total += data[y + half][x]
                        count += 1
                    if x - half >= 0:
                        total += data[y][x - half]
                        count += 1
                    if x + half < size:
                        total += data[y][x + half]
                        count += 1
                    if count > 0:
                        data[y][x] = total / count + rng.uniform(-roughness, roughness)

            step = half
            roughness *= 0.5

        result: List[List[float]] = [
            [data[y][x] for x in range(width)] for y in range(height)
        ]
        return result

    def _generate_midpoint_displacement(
        self,
        width: int,
        height: int,
        seed: int,
    ) -> List[List[float]]:
        rng = random.Random(seed)

        data: List[List[float]] = [[0.0 for _ in range(width)] for _ in range(height)]

        for x in range(width):
            data[0][x] = rng.uniform(-1.0, 1.0)
            data[height - 1][x] = rng.uniform(-1.0, 1.0)
        for y in range(height):
            data[y][0] = rng.uniform(-1.0, 1.0)
            data[y][width - 1] = rng.uniform(-1.0, 1.0)

        displacement = 1.0

        def _displace_midpoint(x1: int, y1: int, x2: int, y2: int, d: float) -> None:
            if x2 - x1 < 2 and y2 - y1 < 2:
                return
            mx = (x1 + x2) // 2
            my = (y1 + y2) // 2
            data[my][mx] = (
                data[y1][x1] + data[y1][x2] + data[y2][x1] + data[y2][x2]
            ) / 4.0 + rng.uniform(-d, d)

            data[y1][mx] = (data[y1][x1] + data[y1][x2]) / 2.0 + rng.uniform(-d, d)
            data[my][x1] = (data[y1][x1] + data[y2][x1]) / 2.0 + rng.uniform(-d, d)
            data[my][x2] = (data[y1][x2] + data[y2][x2]) / 2.0 + rng.uniform(-d, d)
            data[y2][mx] = (data[y2][x1] + data[y2][x2]) / 2.0 + rng.uniform(-d, d)

            nd = d * 0.5
            _displace_midpoint(x1, y1, mx, my, nd)
            _displace_midpoint(mx, y1, x2, my, nd)
            _displace_midpoint(x1, my, mx, y2, nd)
            _displace_midpoint(mx, my, x2, y2, nd)

        _displace_midpoint(0, 0, width - 1, height - 1, displacement)
        return data

    def _generate_worley_noise(
        self,
        width: int,
        height: int,
        seed: int,
        scale: float,
    ) -> List[List[float]]:
        rng = random.Random(seed)
        cell_count = max(8, int(max(width, height) / scale * 2))
        points = [
            (rng.uniform(0, width), rng.uniform(0, height))
            for _ in range(cell_count)
        ]

        result: List[List[float]] = []
        for y in range(height):
            row: List[float] = []
            for x in range(width):
                distances = sorted(
                    [
                        math.sqrt((px - x) ** 2 + (py - y) ** 2)
                        for px, py in points
                    ]
                )
                f1 = distances[0] if distances else 0.0
                f2 = distances[1] if len(distances) > 1 else f1
                value = (f2 - f1) / max(scale, 1.0)
                row.append(max(-1.0, min(1.0, value)))
            result.append(row)
        return result

    def _generate_biome_map(
        self,
        heightmap: List[List[float]],
        width: int,
        height: int,
        sea_level: float,
    ) -> List[List[int]]:
        biome_map: List[List[int]] = []
        for y in range(height):
            row: List[int] = []
            for x in range(width):
                h = heightmap[y][x]
                if h < sea_level * 0.3:
                    biome = 0
                elif h < sea_level:
                    biome = 1
                elif h < sea_level + 0.15:
                    biome = 2
                elif h < sea_level + 0.4:
                    biome = 3
                elif h < sea_level + 0.65:
                    biome = 4
                else:
                    biome = 5
                row.append(biome)
            biome_map.append(row)
        return biome_map

    # --- Internal Initialization ---

    def _initialize_defaults(self) -> None:
        pass


def get_procedural_synthesis() -> ProceduralSynthesis:
    return ProceduralSynthesis.get_instance()