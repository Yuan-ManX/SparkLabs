"""
SparkLabs Engine - Voxel Terrain System

A voxel-based terrain engine for the SparkLabs AI-native game engine.
The world is represented as a 3D grid of voxels partitioned into chunks
for streaming and meshing. Each voxel carries a type, color, and hardness.
Chunks progress through a lifecycle from UNLOADED to MESHED and may be
marked DIRTY when their contents change.

The engine provides procedural terrain generation built on value noise and
fractal Brownian motion, three meshing strategies (NAIVE, CULLING, GREEDY),
DDA voxel raycasting, sunlight propagation with ambient occlusion, AABB
collision queries against voxel data, region export/import serialization,
and a small event bus for voxel lifecycle notifications.

All public state is guarded by a reentrant lock and the engine follows the
project singleton pattern with a module-level ``get_voxel_terrain()`` factory.

Architecture:
  VoxelTerrainEngine (Singleton)
    |-- Voxel           (one cell of the world grid)
    |-- VoxelChunk      (a cubic block of voxels)
    |-- ChunkMesh       (vertex/index buffer for one chunk)
    |-- VoxelRegion     (an axis-aligned sub-volume of the world)
    |-- TerrainConfig   (generation and runtime parameters)
    |-- VoxelStats      (aggregated runtime counters)
    |-- VoxelEvent      (an emitted voxel lifecycle event)
    |-- VoxelSnapshot   (point-in-time engine summary)

Usage:
    engine = get_voxel_terrain()
    engine.set_voxel(10, 20, 10, VoxelType.STONE)
    mesh = engine.mesh_chunk(0, 0, 0)
    hit = engine.raycast((0.5, 30.0, 0.5), (0.0, -1.0, 0.0), 64.0)
"""

from __future__ import annotations

import datetime
import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Enumerations
# =============================================================================


class VoxelType(Enum):
    """Classification of a voxel by material composition.

    Values are strings so the enum serializes cleanly to JSON without
    custom encoders.
    """

    AIR = "air"
    SOLID = "solid"
    STONE = "stone"
    DIRT = "dirt"
    GRASS = "grass"
    SAND = "sand"
    WOOD = "wood"
    WATER = "water"
    LAVA = "lava"
    ORE_COAL = "ore_coal"
    ORE_IRON = "ore_iron"
    ORE_GOLD = "ore_gold"
    CUSTOM = "custom"


class ChunkState(Enum):
    """Lifecycle state of a voxel chunk.

    Chunks transition through these states as they are loaded, meshed,
    invalidated, and unloaded.
    """

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    MESHED = "meshed"
    DIRTY = "dirty"


class MeshingStrategy(Enum):
    """Strategy used to build a chunk mesh from voxel data.

    NAIVE emits one quad per exposed face. CULLING skips faces whose
    neighbor is opaque. GREEDY merges adjacent coplanar faces into
    rectangles to reduce triangle count.
    """

    NAIVE = "naive"
    GREEDY = "greedy"
    CULLING = "culling"


class VoxelEventKind(Enum):
    """Kinds of events emitted by the voxel terrain engine."""

    VOXEL_SET = "voxel_set"
    VOXEL_REMOVED = "voxel_removed"
    CHUNK_LOADED = "chunk_loaded"
    CHUNK_UNLOADED = "chunk_unloaded"
    CHUNK_MESHED = "chunk_meshed"
    CHUNK_DIRTY = "chunk_dirty"
    REGION_FILLED = "region_filled"
    TERRAIN_GENERATED = "terrain_generated"
    REGION_EXPORTED = "region_exported"
    REGION_IMPORTED = "region_imported"


# =============================================================================
# Static voxel property tables
# =============================================================================


# Per-type RGBA colors used for meshing and visualization.
_VOXEL_COLORS: Dict[VoxelType, Tuple[float, float, float, float]] = {
    VoxelType.AIR: (0.0, 0.0, 0.0, 0.0),
    VoxelType.SOLID: (0.5, 0.5, 0.5, 1.0),
    VoxelType.STONE: (0.45, 0.45, 0.48, 1.0),
    VoxelType.DIRT: (0.36, 0.22, 0.13, 1.0),
    VoxelType.GRASS: (0.30, 0.62, 0.20, 1.0),
    VoxelType.SAND: (0.83, 0.78, 0.45, 1.0),
    VoxelType.WOOD: (0.40, 0.27, 0.13, 1.0),
    VoxelType.WATER: (0.20, 0.38, 0.85, 0.65),
    VoxelType.LAVA: (0.95, 0.35, 0.10, 1.0),
    VoxelType.ORE_COAL: (0.10, 0.10, 0.10, 1.0),
    VoxelType.ORE_IRON: (0.78, 0.55, 0.40, 1.0),
    VoxelType.ORE_GOLD: (0.95, 0.78, 0.20, 1.0),
    VoxelType.CUSTOM: (0.80, 0.30, 0.80, 1.0),
}

# Per-type hardness used by destruction and physics queries.
_VOXEL_HARDNESS: Dict[VoxelType, float] = {
    VoxelType.AIR: 0.0,
    VoxelType.SOLID: 1.0,
    VoxelType.STONE: 3.0,
    VoxelType.DIRT: 0.8,
    VoxelType.GRASS: 0.6,
    VoxelType.SAND: 0.5,
    VoxelType.WOOD: 2.0,
    VoxelType.WATER: 0.0,
    VoxelType.LAVA: 0.0,
    VoxelType.ORE_COAL: 2.8,
    VoxelType.ORE_IRON: 3.5,
    VoxelType.ORE_GOLD: 3.8,
    VoxelType.CUSTOM: 1.0,
}

# Voxel types that fully occlude the face behind them.
_OPAQUE_TYPES: frozenset = frozenset({
    VoxelType.SOLID,
    VoxelType.STONE,
    VoxelType.DIRT,
    VoxelType.GRASS,
    VoxelType.SAND,
    VoxelType.WOOD,
    VoxelType.ORE_COAL,
    VoxelType.ORE_IRON,
    VoxelType.ORE_GOLD,
    VoxelType.CUSTOM,
})

# Six axis-aligned face directions as (axis, sign) tuples.
# axis: 0=X, 1=Y, 2=Z. sign: +1 or -1.
_FACE_DIRECTIONS: Tuple[Tuple[int, int], ...] = (
    (0, 1), (0, -1),
    (1, 1), (1, -1),
    (2, 1), (2, -1),
)


def voxel_color(vtype: VoxelType) -> Tuple[float, float, float, float]:
    """Return the RGBA color tuple for a voxel type."""
    return _VOXEL_COLORS.get(vtype, _VOXEL_COLORS[VoxelType.CUSTOM])


def voxel_hardness(vtype: VoxelType) -> float:
    """Return the hardness value for a voxel type."""
    return _VOXEL_HARDNESS.get(vtype, 0.0)


def _fade(t: float) -> float:
    """Smoothstep fade curve used by value noise interpolation."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between ``a`` and ``b`` by ``t``."""
    return a + t * (b - a)


# =============================================================================
# Value noise + fractal Brownian motion
# =============================================================================


class _TerrainNoise:
    """Deterministic value noise with fractal Brownian motion sampling.

    The generator uses a permutation table seeded at construction time
    so terrain generation is reproducible for a given seed.
    """

    def __init__(self, seed: int = 1337) -> None:
        self._seed: int = int(seed)
        rng = random.Random(self._seed)
        perm = list(range(256))
        rng.shuffle(perm)
        # Duplicate the table so wrap-around modulo indexing is simple.
        self._perm: List[int] = perm + perm

    def _hash2(self, x: int, y: int) -> int:
        return self._perm[(self._perm[x & 255] + y) & 255]

    def _hash3(self, x: int, y: int, z: int) -> int:
        return self._perm[(self._perm[(self._perm[x & 255] + y) & 255] + z) & 255]

    def value2(self, x: float, y: float) -> float:
        """Sample 2D value noise in the range ``[0, 1)``."""
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = _fade(xf)
        v = _fade(yf)
        a = (self._hash2(xi, yi) & 1023) / 1023.0
        b = (self._hash2(xi + 1, yi) & 1023) / 1023.0
        c = (self._hash2(xi, yi + 1) & 1023) / 1023.0
        d = (self._hash2(xi + 1, yi + 1) & 1023) / 1023.0
        return _lerp(_lerp(a, b, u), _lerp(c, d, u), v)

    def value3(self, x: float, y: float, z: float) -> float:
        """Sample 3D value noise in the range ``[0, 1)``."""
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        zi = int(math.floor(z)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        zf = z - math.floor(z)
        u = _fade(xf)
        v = _fade(yf)
        w = _fade(zf)
        h000 = (self._hash3(xi, yi, zi) & 1023) / 1023.0
        h100 = (self._hash3(xi + 1, yi, zi) & 1023) / 1023.0
        h010 = (self._hash3(xi, yi + 1, zi) & 1023) / 1023.0
        h110 = (self._hash3(xi + 1, yi + 1, zi) & 1023) / 1023.0
        h001 = (self._hash3(xi, yi, zi + 1) & 1023) / 1023.0
        h101 = (self._hash3(xi + 1, yi, zi + 1) & 1023) / 1023.0
        h011 = (self._hash3(xi, yi + 1, zi + 1) & 1023) / 1023.0
        h111 = (self._hash3(xi + 1, yi + 1, zi + 1) & 1023) / 1023.0
        x0 = _lerp(h000, h100, u)
        x1 = _lerp(h010, h110, u)
        x2 = _lerp(h001, h101, u)
        x3 = _lerp(h011, h111, u)
        y0 = _lerp(x0, x1, v)
        y1 = _lerp(x2, x3, v)
        return _lerp(y0, y1, w)

    def fbm2(self, x: float, y: float, octaves: int = 4,
             persistence: float = 0.5, lacunarity: float = 2.0) -> float:
        """Fractal Brownian motion over 2D value noise in ``[0, 1)``."""
        total = 0.0
        amp = 1.0
        freq = 1.0
        max_amp = 0.0
        for _ in range(octaves):
            total += self.value2(x * freq, y * freq) * amp
            max_amp += amp
            freq *= lacunarity
            amp *= persistence
        return total / max_amp if max_amp > 0 else 0.0

    def fbm3(self, x: float, y: float, z: float, octaves: int = 3,
             persistence: float = 0.5, lacunarity: float = 2.0) -> float:
        """Fractal Brownian motion over 3D value noise in ``[0, 1)``."""
        total = 0.0
        amp = 1.0
        freq = 1.0
        max_amp = 0.0
        for _ in range(octaves):
            total += self.value3(x * freq, y * freq, z * freq) * amp
            max_amp += amp
            freq *= lacunarity
            amp *= persistence
        return total / max_amp if max_amp > 0 else 0.0


# =============================================================================
# Data classes
# =============================================================================


@dataclass
class Voxel:
    """A single cell of the world grid.

    Attributes:
        type: Material classification of the voxel.
        color: Optional RGBA override; when ``None`` the type's default
            color is used for rendering.
        metadata: Free-form extension data attached by callers.
    """

    type: VoxelType = VoxelType.AIR
    color: Optional[Tuple[float, float, float, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_solid(self) -> bool:
        """Return True if the voxel blocks movement and raycasts."""
        return self.type != VoxelType.AIR and self.type != VoxelType.WATER

    def is_opaque(self) -> bool:
        """Return True if the voxel fully occludes the face behind it."""
        return self.type in _OPAQUE_TYPES

    def hardness(self) -> float:
        """Return the destruction hardness of this voxel."""
        return voxel_hardness(self.type)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "color": list(self.color) if self.color else None,
            "metadata": dict(self.metadata),
        }


@dataclass
class ChunkMesh:
    """Renderable mesh data for a single chunk.

    Attributes:
        chunk_id: Identifier of the owning chunk.
        vertices: Flat list of vertex coordinates (x, y, z triplets).
        indices: Triangle indices into ``vertices``.
        normals: Flat list of per-vertex normals (x, y, z triplets).
        colors: Flat list of per-vertex RGBA colors.
        strategy: Meshing strategy that produced this mesh.
        built_at: Wall-clock timestamp of mesh construction.
    """

    chunk_id: str = ""
    vertices: List[float] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)
    normals: List[float] = field(default_factory=list)
    colors: List[float] = field(default_factory=list)
    strategy: MeshingStrategy = MeshingStrategy.GREEDY
    built_at: Optional[datetime.datetime] = None

    @property
    def vertex_count(self) -> int:
        return len(self.vertices) // 3

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "vertices": list(self.vertices),
            "indices": list(self.indices),
            "normals": list(self.normals),
            "colors": list(self.colors),
            "strategy": self.strategy.value,
            "built_at": self.built_at.isoformat() if self.built_at else None,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
        }


@dataclass
class VoxelChunk:
    """A cubic block of voxels with lifecycle tracking.

    Chunks store voxels in a flat list ordered by ``(x, y, z)`` with
    ``x`` varying fastest, then ``z``, then ``y``. This layout keeps
    vertical columns contiguous for fast heightmap iteration.

    Attributes:
        cx, cy, cz: Chunk-grid coordinates (world origin divided by
            ``chunk_size``).
        chunk_size: Edge length of the chunk in voxels.
        voxels: Flat list of ``Voxel`` instances (length ``size**3``).
        state: Current lifecycle state.
        mesh: Last built mesh, if any.
    """

    cx: int = 0
    cy: int = 0
    cz: int = 0
    chunk_size: int = 16
    voxels: List[Voxel] = field(default_factory=list)
    state: ChunkState = ChunkState.UNLOADED
    mesh: Optional[ChunkMesh] = None

    @property
    def chunk_id(self) -> str:
        return f"{self.cx},{self.cy},{self.cz}"

    def index(self, x: int, y: int, z: int) -> int:
        """Return the flat-list index for local coordinates ``(x, y, z)``."""
        return (y * self.chunk_size + z) * self.chunk_size + x

    def in_bounds(self, x: int, y: int, z: int) -> bool:
        s = self.chunk_size
        return 0 <= x < s and 0 <= y < s and 0 <= z < s

    def get(self, x: int, y: int, z: int) -> Voxel:
        """Return the voxel at local coordinates, or AIR if out of range."""
        if not self.voxels or not self.in_bounds(x, y, z):
            return _AIR_VOXEL
        return self.voxels[self.index(x, y, z)]

    def set(self, x: int, y: int, z: int, voxel: Voxel) -> None:
        """Write a voxel at local coordinates. Allocates storage if empty."""
        if not self.voxels:
            self.voxels = [_AIR_VOXEL] * (self.chunk_size ** 3)
        if not self.in_bounds(x, y, z):
            return
        self.voxels[self.index(x, y, z)] = voxel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cx": self.cx,
            "cy": self.cy,
            "cz": self.cz,
            "chunk_id": self.chunk_id,
            "chunk_size": self.chunk_size,
            "state": self.state.value,
            "voxel_count": len(self.voxels),
            "has_mesh": self.mesh is not None,
        }


@dataclass
class VoxelRegion:
    """An axis-aligned sub-volume of the world for queries and IO.

    Attributes:
        origin: World-space ``(x, y, z)`` of the minimum corner.
        size: Edge lengths ``(sx, sy, sz)``.
    """

    origin: Tuple[int, int, int] = (0, 0, 0)
    size: Tuple[int, int, int] = (1, 1, 1)

    @property
    def end(self) -> Tuple[int, int, int]:
        ox, oy, oz = self.origin
        sx, sy, sz = self.size
        return (ox + sx, oy + sy, oz + sz)

    def contains(self, x: int, y: int, z: int) -> bool:
        ox, oy, oz = self.origin
        ex, ey, ez = self.end
        return ox <= x < ex and oy <= y < ey and oz <= z < ez

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin": list(self.origin),
            "size": list(self.size),
            "end": list(self.end),
        }


@dataclass
class TerrainConfig:
    """Runtime configuration for the voxel terrain engine.

    Attributes:
        chunk_size: Edge length of a chunk in voxels.
        world_height: Total voxel height of the world column.
        sea_level: Y coordinate of the water plane.
        noise_scale: Frequency multiplier applied to world coordinates
            when sampling the height noise.
        noise_seed: Seed for the deterministic noise generator.
        meshing_strategy: Default strategy used when meshing chunks.
        view_radius: Chunk radius retained around the viewer.
    """

    chunk_size: int = 16
    world_height: int = 32
    sea_level: int = 16
    noise_scale: float = 0.06
    noise_seed: int = 1337
    meshing_strategy: MeshingStrategy = MeshingStrategy.GREEDY
    view_radius: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_size": self.chunk_size,
            "world_height": self.world_height,
            "sea_level": self.sea_level,
            "noise_scale": self.noise_scale,
            "noise_seed": self.noise_seed,
            "meshing_strategy": self.meshing_strategy.value,
            "view_radius": self.view_radius,
        }


@dataclass
class VoxelStats:
    """Aggregated runtime counters for the voxel terrain engine.

    Attributes:
        total_voxels_set: Number of successful ``set_voxel`` calls.
        total_chunks_loaded: Number of chunks that entered LOADED state.
        total_chunks_unloaded: Number of chunks that were unloaded.
        total_meshes_built: Number of chunk meshes built.
        total_rays_cast: Number of raycasts performed.
        total_regions_exported: Number of regions serialized.
        total_regions_imported: Number of regions deserialized.
        total_terrain_generated: Number of generate_terrain invocations.
        last_updated_at: Wall-clock timestamp of the most recent update.
    """

    total_voxels_set: int = 0
    total_chunks_loaded: int = 0
    total_chunks_unloaded: int = 0
    total_meshes_built: int = 0
    total_rays_cast: int = 0
    total_regions_exported: int = 0
    total_regions_imported: int = 0
    total_terrain_generated: int = 0
    last_updated_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_voxels_set": self.total_voxels_set,
            "total_chunks_loaded": self.total_chunks_loaded,
            "total_chunks_unloaded": self.total_chunks_unloaded,
            "total_meshes_built": self.total_meshes_built,
            "total_rays_cast": self.total_rays_cast,
            "total_regions_exported": self.total_regions_exported,
            "total_regions_imported": self.total_regions_imported,
            "total_terrain_generated": self.total_terrain_generated,
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None,
        }


@dataclass
class VoxelEvent:
    """An immutable record of a voxel lifecycle event.

    Attributes:
        id: Auto-generated unique identifier.
        kind: The ``VoxelEventKind`` of the event.
        payload: Free-form payload describing the event.
        timestamp: Time at which the event was emitted.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: VoxelEventKind = VoxelEventKind.VOXEL_SET
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "payload": dict(self.payload),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class VoxelSnapshot:
    """An immutable snapshot of the voxel terrain engine state.

    Attributes:
        chunk_count: Total number of chunks currently retained.
        loaded_chunk_count: Chunks in LOADED or MESHED state.
        dirty_chunk_count: Chunks awaiting a remesh.
        mesh_count: Number of cached chunk meshes.
        voxel_count: Number of non-AIR voxels across retained chunks.
        stats: Aggregated statistic counters.
        config: Runtime configuration at snapshot time.
        timestamp: Time at which the snapshot was taken.
    """

    chunk_count: int = 0
    loaded_chunk_count: int = 0
    dirty_chunk_count: int = 0
    mesh_count: int = 0
    voxel_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_count": self.chunk_count,
            "loaded_chunk_count": self.loaded_chunk_count,
            "dirty_chunk_count": self.dirty_chunk_count,
            "mesh_count": self.mesh_count,
            "voxel_count": self.voxel_count,
            "stats": dict(self.stats),
            "config": dict(self.config),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# Shared sentinel air voxel used for empty cells and out-of-range reads.
_AIR_VOXEL: Voxel = Voxel(type=VoxelType.AIR)


# =============================================================================
# VoxelTerrainEngine — Thread-Safe Singleton
# =============================================================================


class VoxelTerrainEngine:
    """Voxel-based terrain engine for the SparkLabs game engine.

    Stores the world as a dictionary of chunks keyed by their integer
    chunk-grid coordinates. Chunks are streamed in and out around a
    viewer position and meshed on demand using one of three strategies.
    All public methods are thread-safe.
    """

    _instance: Optional["VoxelTerrainEngine"] = None
    _lock = threading.RLock()

    _MAX_EVENTS: int = 1000
    _MAX_HANDLERS: int = 50
    _TERRAIN_RADIUS: int = 1

    def __new__(cls) -> "VoxelTerrainEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "VoxelTerrainEngine":
        """Return the singleton VoxelTerrainEngine instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized: bool = True
        self._chunks: Dict[Tuple[int, int, int], VoxelChunk] = {}
        self._config: TerrainConfig = TerrainConfig()
        self._noise: _TerrainNoise = _TerrainNoise(self._config.noise_seed)
        self._viewer: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._stats: VoxelStats = VoxelStats()
        self._events: List[VoxelEvent] = []
        self._event_handlers: Dict[str, List[Callable[[VoxelEvent], None]]] = {}
        self._creation_time: float = time.time()
        self._seed_default_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate a small default world so the engine works without setup."""
        # Generate a 3x3 footprint of chunks around the origin column,
        # spanning the full world height. This gives the engine visible
        # terrain immediately on first use.
        radius = self._TERRAIN_RADIUS
        vertical_chunks = max(
            1, self._config.world_height // self._config.chunk_size
        )
        for cx in range(-radius, radius + 1):
            for cz in range(-radius, radius + 1):
                for cy in range(0, vertical_chunks):
                    self._generate_chunk_voxels(cx, cy, cz)
        self._stats.last_updated_at = datetime.datetime.now()

    def _generate_chunk_voxels(self, cx: int, cy: int, cz: int) -> VoxelChunk:
        """Allocate and fill a chunk with procedurally generated voxels."""
        size = self._config.chunk_size
        sea = self._config.sea_level
        scale = self._config.noise_scale
        chunk = VoxelChunk(
            cx=cx, cy=cy, cz=cz, chunk_size=size,
            voxels=[_AIR_VOXEL] * (size * size * size),
            state=ChunkState.LOADED,
        )
        base_y = cy * size
        for ly in range(size):
            world_y = base_y + ly
            for lz in range(size):
                world_z = cz * size + lz
                for lx in range(size):
                    world_x = cx * size + lx
                    # Heightmap from 2D fractal noise.
                    h = self._noise.fbm2(
                        world_x * scale, world_z * scale,
                        octaves=4, persistence=0.5, lacunarity=2.0,
                    )
                    height = int(h * self._config.world_height)
                    if height < 1:
                        height = 1
                    if height > self._config.world_height:
                        height = self._config.world_height
                    vtype = VoxelType.AIR
                    if world_y < height:
                        depth = height - world_y
                        if depth == 1:
                            # Surface block.
                            if world_y <= sea + 1:
                                vtype = VoxelType.SAND
                            else:
                                vtype = VoxelType.GRASS
                        elif depth <= 3:
                            vtype = VoxelType.DIRT
                        else:
                            vtype = VoxelType.STONE
                            # Carve ores using 3D noise.
                            ore = self._noise.fbm3(
                                world_x * 0.1, world_y * 0.1, world_z * 0.1,
                                octaves=2,
                            )
                            if world_y < sea // 2:
                                if ore > 0.78:
                                    vtype = VoxelType.ORE_GOLD
                                elif ore > 0.70:
                                    vtype = VoxelType.ORE_IRON
                            elif ore > 0.80:
                                vtype = VoxelType.ORE_COAL
                    elif world_y < sea:
                        # Below sea level and above terrain: fill with water.
                        vtype = VoxelType.WATER
                    chunk.voxels[chunk.index(lx, ly, lz)] = Voxel(type=vtype)
        self._chunks[(cx, cy, cz)] = chunk
        self._stats.total_chunks_loaded += 1
        return chunk

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return runtime statistics about the engine."""
        with self._lock:
            loaded = sum(
                1 for c in self._chunks.values()
                if c.state in (ChunkState.LOADED, ChunkState.MESHED)
            )
            dirty = sum(
                1 for c in self._chunks.values() if c.state == ChunkState.DIRTY
            )
            meshes = sum(1 for c in self._chunks.values() if c.mesh is not None)
            voxel_count = 0
            for c in self._chunks.values():
                for v in c.voxels:
                    if v.type != VoxelType.AIR:
                        voxel_count += 1
            return {
                "status": "ok",
                "uptime_seconds": round(time.time() - self._creation_time, 3),
                "chunk_count": len(self._chunks),
                "loaded_chunk_count": loaded,
                "dirty_chunk_count": dirty,
                "mesh_count": meshes,
                "voxel_count": voxel_count,
                "viewer": list(self._viewer),
                "config": self._config.to_dict(),
                "stats": self._stats.to_dict(),
            }

    def get_snapshot(self) -> VoxelSnapshot:
        """Return a point-in-time snapshot of the engine state."""
        with self._lock:
            status = self.get_status()
            return VoxelSnapshot(
                chunk_count=status["chunk_count"],
                loaded_chunk_count=status["loaded_chunk_count"],
                dirty_chunk_count=status["dirty_chunk_count"],
                mesh_count=status["mesh_count"],
                voxel_count=status["voxel_count"],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
            )

    def reset(self) -> None:
        """Clear all state and re-seed default data."""
        with self._lock:
            self._chunks.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._viewer = (0.0, 0.0, 0.0)
            self._stats = VoxelStats()
            self._noise = _TerrainNoise(self._config.noise_seed)
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Voxel access
    # ------------------------------------------------------------------

    def set_voxel(self, x: int, y: int, z: int,
                  vtype: VoxelType,
                  color: Optional[Tuple[float, float, float, float]] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Write a voxel at world coordinates. Returns True on success."""
        with self._lock:
            size = self._config.chunk_size
            if y < 0 or y >= self._config.world_height:
                return False
            cx = x // size
            cy = y // size
            cz = z // size
            key = (cx, cy, cz)
            chunk = self._chunks.get(key)
            if chunk is None:
                chunk = VoxelChunk(
                    cx=cx, cy=cy, cz=cz, chunk_size=size,
                    voxels=[_AIR_VOXEL] * (size * size * size),
                    state=ChunkState.LOADED,
                )
                self._chunks[key] = chunk
                self._stats.total_chunks_loaded += 1
            lx = x - cx * size
            ly = y - cy * size
            lz = z - cz * size
            chunk.set(lx, ly, lz, Voxel(
                type=vtype, color=color,
                metadata=dict(metadata) if metadata else {},
            ))
            chunk.state = ChunkState.DIRTY
            self._stats.total_voxels_set += 1
            self._stats.last_updated_at = datetime.datetime.now()
            self._emit_event(VoxelEventKind.VOXEL_SET, {
                "x": x, "y": y, "z": z, "type": vtype.value,
            })
            return True

    def get_voxel(self, x: int, y: int, z: int) -> Voxel:
        """Return the voxel at world coordinates, or AIR if unavailable."""
        with self._lock:
            size = self._config.chunk_size
            if y < 0 or y >= self._config.world_height:
                return _AIR_VOXEL
            cx = x // size
            cy = y // size
            cz = z // size
            chunk = self._chunks.get((cx, cy, cz))
            if chunk is None:
                return _AIR_VOXEL
            lx = x - cx * size
            ly = y - cy * size
            lz = z - cz * size
            return chunk.get(lx, ly, lz)

    def fill_region(self, region: VoxelRegion, vtype: VoxelType) -> int:
        """Fill a rectangular region with the given voxel type. Returns count."""
        with self._lock:
            ox, oy, oz = region.origin
            sx, sy, sz = region.size
            count = 0
            for dy in range(sy):
                for dz in range(sz):
                    for dx in range(sx):
                        if self.set_voxel(ox + dx, oy + dy, oz + dz, vtype):
                            count += 1
            self._emit_event(VoxelEventKind.REGION_FILLED, {
                "region": region.to_dict(), "type": vtype.value, "count": count,
            })
            return count

    def fill_sphere(self, center: Tuple[int, int, int],
                    radius: float, vtype: VoxelType) -> int:
        """Fill a spherical volume with the given voxel type. Returns count."""
        with self._lock:
            cx, cy, cz = center
            r = int(math.ceil(radius))
            r2 = radius * radius
            count = 0
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if dx * dx + dy * dy + dz * dz <= r2:
                            if self.set_voxel(cx + dx, cy + dy, cz + dz, vtype):
                                count += 1
            self._emit_event(VoxelEventKind.REGION_FILLED, {
                "center": list(center), "radius": radius,
                "type": vtype.value, "count": count,
            })
            return count

    # ------------------------------------------------------------------
    # Chunk management
    # ------------------------------------------------------------------

    def get_chunk(self, cx: int, cy: int, cz: int) -> Optional[VoxelChunk]:
        """Return the chunk at chunk-grid coordinates, if loaded."""
        with self._lock:
            return self._chunks.get((cx, cy, cz))

    def load_chunk(self, cx: int, cy: int, cz: int) -> VoxelChunk:
        """Ensure a chunk is loaded, generating its voxels if absent."""
        with self._lock:
            key = (cx, cy, cz)
            chunk = self._chunks.get(key)
            if chunk is not None:
                return chunk
            chunk = self._generate_chunk_voxels(cx, cy, cz)
            chunk.state = ChunkState.LOADED
            self._emit_event(VoxelEventKind.CHUNK_LOADED, {
                "cx": cx, "cy": cy, "cz": cz,
            })
            return chunk

    def unload_chunk(self, cx: int, cy: int, cz: int) -> bool:
        """Drop a chunk from memory. Returns True if it was present."""
        with self._lock:
            key = (cx, cy, cz)
            if key not in self._chunks:
                return False
            del self._chunks[key]
            self._stats.total_chunks_unloaded += 1
            self._emit_event(VoxelEventKind.CHUNK_UNLOADED, {
                "cx": cx, "cy": cy, "cz": cz,
            })
            return True

    def update_viewer(self, x: float, y: float, z: float) -> None:
        """Update the viewer position and stream chunks around it."""
        with self._lock:
            self._viewer = (x, y, z)
            size = self._config.chunk_size
            vcx = int(x) // size
            vcz = int(z) // size
            radius = self._config.view_radius
            # Load chunks within the view radius.
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    for cy in range(
                        0, max(1, self._config.world_height // size)
                    ):
                        key = (vcx + dx, cy, vcz + dz)
                        if key not in self._chunks:
                            self.load_chunk(vcx + dx, cy, vcz + dz)
            # Unload chunks outside the view radius plus a one-chunk margin.
            unload_keys: List[Tuple[int, int, int]] = []
            for (ccx, ccy, ccz) in self._chunks.keys():
                if abs(ccx - vcx) > radius + 1 or abs(ccz - vcz) > radius + 1:
                    unload_keys.append((ccx, ccy, ccz))
            for key in unload_keys:
                self.unload_chunk(*key)

    # ------------------------------------------------------------------
    # Meshing
    # ------------------------------------------------------------------

    def _is_exposed(self, neighbor: Optional[Voxel],
                    strategy: MeshingStrategy) -> bool:
        """Decide whether a face should be emitted given its neighbor.

        AIR neighbors always expose the face. None (unloaded) neighbors
        are treated as opaque under NAIVE (no face emitted) and as
        exposed under CULLING and GREEDY (face emitted).
        """
        if neighbor is None:
            return strategy != MeshingStrategy.NAIVE
        if neighbor.type == VoxelType.AIR:
            return True
        return not neighbor.is_opaque()

    def _build_face_mask(self, chunk: VoxelChunk, axis: int, sign: int
                         ) -> List[List[Optional[VoxelType]]]:
        """Build a 2D mask of voxel types that have an exposed face.

        For the layer traversal along ``axis`` with normal ``sign``, the
        mask records the voxel type at each ``(u, v)`` cell where a face
        should be emitted, or ``None`` where no face is needed.
        """
        size = chunk.chunk_size
        strategy = self._config.meshing_strategy
        mask: List[List[Optional[VoxelType]]] = [
            [None] * size for _ in range(size)
        ]
        for layer in range(size):
            for u in range(size):
                for v in range(size):
                    # Map (axis, layer, u, v) to local voxel coordinates.
                    if axis == 0:
                        x, y, z = layer, u, v
                    elif axis == 1:
                        x, y, z = u, layer, v
                    else:
                        x, y, z = u, v, layer
                    voxel = chunk.get(x, y, z)
                    if voxel.type == VoxelType.AIR:
                        continue
                    # Determine the neighbor along the face direction.
                    nx, ny, nz = x, y, z
                    if axis == 0:
                        nx = x + sign
                    elif axis == 1:
                        ny = y + sign
                    else:
                        nz = z + sign
                    neighbor: Optional[Voxel] = None
                    if chunk.in_bounds(nx, ny, nz):
                        neighbor = chunk.get(nx, ny, nz)
                    else:
                        # Look up the neighbor in the adjacent chunk.
                        size_c = self._config.chunk_size
                        if axis == 0:
                            ax = chunk.cx + sign
                            ay, az = chunk.cy, chunk.cz
                        elif axis == 1:
                            ax, az = chunk.cx, chunk.cz
                            ay = chunk.cy + sign
                        else:
                            ax, ay = chunk.cx, chunk.cy
                            az = chunk.cz + sign
                        adj = self._chunks.get((ax, ay, az))
                        if adj is not None:
                            lx = nx - (sign if axis == 0 else 0) * size_c
                            ly = ny - (sign if axis == 1 else 0) * size_c
                            lz = nz - (sign if axis == 2 else 0) * size_c
                            lx %= size_c
                            ly %= size_c
                            lz %= size_c
                            neighbor = adj.get(lx, ly, lz)
                    if self._is_exposed(neighbor, strategy):
                        mask[u][v] = voxel.type
        return mask

    def _emit_quad(self, mesh: ChunkMesh, chunk: VoxelChunk,
                   axis: int, sign: int, layer: int,
                   u: int, v: int, du: int, dv: int,
                   vtype: VoxelType) -> None:
        """Append a single quad to ``mesh`` for the given face rectangle."""
        size = chunk.chunk_size
        # Compute base world-space position of the (u, v) corner.
        # The face lies on the plane at ``layer`` along ``axis``.
        base = [0, 0, 0]
        base[axis] = layer + (1 if sign > 0 else 0)
        # Compute the four corners in local space, then offset by chunk origin.
        origin = [chunk.cx * size, chunk.cy * size, chunk.cz * size]
        corners: List[List[float]] = []
        for su in (0, 1):
            for sv in (0, 1):
                corner = list(base)
                # Map (axis, layer, u, v) coordinates to local space.
                if axis == 0:
                    corner[1] = u + su * du
                    corner[2] = v + sv * dv
                elif axis == 1:
                    corner[0] = u + su * du
                    corner[2] = v + sv * dv
                else:
                    corner[0] = u + su * du
                    corner[1] = v + sv * dv
                corner[0] += origin[0]
                corner[1] += origin[1]
                corner[2] += origin[2]
                corners.append(corner)
        # Quad winding depends on sign to keep front faces consistent.
        order = [0, 1, 2, 2, 1, 3] if sign > 0 else [0, 2, 1, 1, 2, 3]
        base_index = len(mesh.vertices) // 3
        for ci in order:
            c = corners[ci]
            mesh.vertices.extend(c)
        # Normal points along (axis, sign).
        normal = [0.0, 0.0, 0.0]
        normal[axis] = float(sign)
        for _ in range(4):
            mesh.normals.extend(normal)
        color = voxel_color(vtype)
        for _ in range(4):
            mesh.colors.extend(color)
        # Emit two triangles referencing the four new vertices.
        mesh.indices.extend([
            base_index, base_index + 1, base_index + 2,
            base_index + 2, base_index + 1, base_index + 3,
        ])

    def _build_mesh(self, chunk: VoxelChunk) -> ChunkMesh:
        """Build a renderable mesh for the chunk using the configured strategy."""
        mesh = ChunkMesh(
            chunk_id=chunk.chunk_id,
            strategy=self._config.meshing_strategy,
            built_at=datetime.datetime.now(),
        )
        strategy = self._config.meshing_strategy
        size = chunk.chunk_size
        for axis, sign in _FACE_DIRECTIONS:
            mask = self._build_face_mask(chunk, axis, sign)
            if strategy == MeshingStrategy.GREEDY:
                self._emit_greedy_quads(mesh, chunk, axis, sign, mask, size)
            else:
                # NAIVE and CULLING both emit one quad per exposed face;
                # the difference is handled inside ``_build_face_mask``.
                self._emit_naive_quads(mesh, chunk, axis, sign, mask, size)
        return mesh

    def _emit_naive_quads(self, mesh: ChunkMesh, chunk: VoxelChunk,
                          axis: int, sign: int,
                          mask: List[List[Optional[VoxelType]]],
                          size: int) -> None:
        """Emit one 1x1 quad per exposed face in the mask."""
        for layer in range(size):
            for u in range(size):
                for v in range(size):
                    vtype = mask[u][v]
                    if vtype is None:
                        continue
                    self._emit_quad(
                        mesh, chunk, axis, sign, layer,
                        u, v, 1, 1, vtype,
                    )

    def _emit_greedy_quads(self, mesh: ChunkMesh, chunk: VoxelChunk,
                           axis: int, sign: int,
                           mask: List[List[Optional[VoxelType]]],
                           size: int) -> None:
        """Merge coplanar faces of the same type into rectangles.

        Implements the classic width-then-height greedy expansion:
        scan the mask, find the top-left uncovered cell, expand right
        as far as the type matches, then expand down as far as the
        full width still matches. Mark covered cells as None.
        """
        for layer in range(size):
            for u in range(size):
                for v in range(size):
                    vtype = mask[u][v]
                    if vtype is None:
                        continue
                    # Expand width along the u axis.
                    du = 1
                    while u + du < size and mask[u + du][v] == vtype:
                        du += 1
                    # Expand height along the v axis, requiring the
                    # full width to match on every row.
                    dv = 1
                    while v + dv < size:
                        ok = True
                        for k in range(du):
                            if mask[u + k][v + dv] != vtype:
                                ok = False
                                break
                        if not ok:
                            break
                        dv += 1
                    self._emit_quad(
                        mesh, chunk, axis, sign, layer,
                        u, v, du, dv, vtype,
                    )
                    # Clear the covered region so it is not emitted again.
                    for ku in range(du):
                        for kv in range(dv):
                            mask[u + ku][v + kv] = None

    def mesh_chunk(self, cx: int, cy: int, cz: int) -> Optional[ChunkMesh]:
        """Build and cache a mesh for the chunk. Returns None if absent."""
        with self._lock:
            chunk = self._chunks.get((cx, cy, cz))
            if chunk is None:
                return None
            mesh = self._build_mesh(chunk)
            chunk.mesh = mesh
            chunk.state = ChunkState.MESHED
            self._stats.total_meshes_built += 1
            self._stats.last_updated_at = datetime.datetime.now()
            self._emit_event(VoxelEventKind.CHUNK_MESHED, {
                "cx": cx, "cy": cy, "cz": cz,
                "triangles": mesh.triangle_count,
            })
            return mesh

    def mesh_all_dirty(self) -> int:
        """Remesh every chunk in the DIRTY state. Returns the count remeshed."""
        with self._lock:
            dirty_keys: List[Tuple[int, int, int]] = [
                key for key, c in self._chunks.items()
                if c.state == ChunkState.DIRTY
            ]
            for key in dirty_keys:
                cx, cy, cz = key
                chunk = self._chunks.get(key)
                if chunk is None:
                    continue
                mesh = self._build_mesh(chunk)
                chunk.mesh = mesh
                chunk.state = ChunkState.MESHED
                self._stats.total_meshes_built += 1
                self._emit_event(VoxelEventKind.CHUNK_MESHED, {
                    "cx": cx, "cy": cy, "cz": cz,
                    "triangles": mesh.triangle_count,
                })
            return len(dirty_keys)

    # ------------------------------------------------------------------
    # Terrain generation
    # ------------------------------------------------------------------

    def generate_terrain(self, radius: int = 2,
                         seed: Optional[int] = None) -> int:
        """Generate terrain chunks within ``radius`` of the origin.

        Returns the number of chunks generated. If ``seed`` is provided
        the noise generator is reseeded before generation.
        """
        with self._lock:
            if seed is not None:
                self._config.noise_seed = int(seed)
                self._noise = _TerrainNoise(self._config.noise_seed)
            size = self._config.chunk_size
            vertical = max(
                1, self._config.world_height // size
            )
            count = 0
            for cx in range(-radius, radius + 1):
                for cz in range(-radius, radius + 1):
                    for cy in range(0, vertical):
                        key = (cx, cy, cz)
                        if key in self._chunks:
                            continue
                        self._generate_chunk_voxels(cx, cy, cz)
                        count += 1
            self._stats.total_terrain_generated += 1
            self._stats.last_updated_at = datetime.datetime.now()
            self._emit_event(VoxelEventKind.TERRAIN_GENERATED, {
                "radius": radius, "seed": self._config.noise_seed,
                "chunks_generated": count,
            })
            return count

    # ------------------------------------------------------------------
    # Raycasting (DDA voxel traversal)
    # ------------------------------------------------------------------

    def raycast(self, origin: Tuple[float, float, float],
                direction: Tuple[float, float, float],
                max_distance: float = 100.0
                ) -> Optional[Tuple[int, int, int, VoxelType]]:
        """Trace a ray through the voxel grid using the DDA algorithm.

        Returns the first solid voxel hit as ``(x, y, z, type)`` or
        ``None`` if no hit is found within ``max_distance``.
        """
        with self._lock:
            self._stats.total_rays_cast += 1
            ox, oy, oz = origin
            dx, dy, dz = direction
            length = math.sqrt(dx * dx + dy * dy + dz * dz)
            if length < 1e-9:
                return None
            dx /= length
            dy /= length
            dz /= length
            x = int(math.floor(ox))
            y = int(math.floor(oy))
            z = int(math.floor(oz))
            step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            step_z = 1 if dz > 0 else (-1 if dz < 0 else 0)
            # Distance to the next voxel boundary along each axis.
            def _t_to_next(o: float, p: int, s: int, d: float) -> float:
                if d == 0.0:
                    return float("inf")
                if s > 0:
                    return (p + 1 - o) / d
                return (p - o) / d
            t_max_x = _t_to_next(ox, x, step_x, dx)
            t_max_y = _t_to_next(oy, y, step_y, dy)
            t_max_z = _t_to_next(oz, z, step_z, dz)
            t_delta_x = abs(1.0 / dx) if dx != 0 else float("inf")
            t_delta_y = abs(1.0 / dy) if dy != 0 else float("inf")
            t_delta_z = abs(1.0 / dz) if dz != 0 else float("inf")
            travelled = 0.0
            # Check the starting voxel first.
            voxel = self.get_voxel(x, y, z)
            if voxel.is_solid():
                return (x, y, z, voxel.type)
            while travelled <= max_distance:
                if t_max_x < t_max_y and t_max_x < t_max_z:
                    x += step_x
                    travelled = t_max_x
                    t_max_x += t_delta_x
                elif t_max_y < t_max_z:
                    y += step_y
                    travelled = t_max_y
                    t_max_y += t_delta_y
                else:
                    z += step_z
                    travelled = t_max_z
                    t_max_z += t_delta_z
                if travelled > max_distance:
                    break
                voxel = self.get_voxel(x, y, z)
                if voxel.is_solid():
                    return (x, y, z, voxel.type)
            return None

    # ------------------------------------------------------------------
    # Collision queries
    # ------------------------------------------------------------------

    def get_colliding_voxels(self, min_point: Tuple[float, float, float],
                              max_point: Tuple[float, float, float]
                              ) -> List[Tuple[int, int, int, VoxelType]]:
        """Return all solid voxels intersecting the given AABB."""
        with self._lock:
            x0 = int(math.floor(min_point[0]))
            y0 = int(math.floor(min_point[1]))
            z0 = int(math.floor(min_point[2]))
            x1 = int(math.floor(max_point[0]))
            y1 = int(math.floor(max_point[1]))
            z1 = int(math.floor(max_point[2]))
            hits: List[Tuple[int, int, int, VoxelType]] = []
            for x in range(x0, x1 + 1):
                for y in range(y0, y1 + 1):
                    for z in range(z0, z1 + 1):
                        voxel = self.get_voxel(x, y, z)
                        if voxel.is_solid():
                            hits.append((x, y, z, voxel.type))
            return hits

    # ------------------------------------------------------------------
    # Region export / import
    # ------------------------------------------------------------------

    def export_region(self, region: VoxelRegion) -> Dict[str, Any]:
        """Serialize the voxels in ``region`` to a portable dict."""
        with self._lock:
            ox, oy, oz = region.origin
            sx, sy, sz = region.size
            voxels: List[Dict[str, Any]] = []
            for dy in range(sy):
                for dz in range(sz):
                    for dx in range(sx):
                        voxel = self.get_voxel(ox + dx, oy + dy, oz + dz)
                        if voxel.type != VoxelType.AIR:
                            voxels.append({
                                "x": ox + dx,
                                "y": oy + dy,
                                "z": oz + dz,
                                "type": voxel.type.value,
                                "color": list(voxel.color) if voxel.color else None,
                                "metadata": dict(voxel.metadata),
                            })
            self._stats.total_regions_exported += 1
            self._stats.last_updated_at = datetime.datetime.now()
            payload = {
                "region": region.to_dict(),
                "voxel_count": len(voxels),
                "voxels": voxels,
                "exported_at": datetime.datetime.now().isoformat(),
            }
            self._emit_event(VoxelEventKind.REGION_EXPORTED, {
                "region": region.to_dict(), "voxel_count": len(voxels),
            })
            return payload

    def import_region(self, payload: Dict[str, Any]) -> int:
        """Import voxels from a previously exported payload. Returns count."""
        with self._lock:
            voxels = payload.get("voxels", [])
            count = 0
            for entry in voxels:
                try:
                    vtype = VoxelType(entry["type"])
                except (KeyError, ValueError):
                    continue
                color = entry.get("color")
                color_tuple = tuple(color) if color else None
                metadata = entry.get("metadata") or {}
                if self.set_voxel(
                    int(entry["x"]), int(entry["y"]), int(entry["z"]),
                    vtype, color_tuple, metadata,
                ):
                    count += 1
            self._stats.total_regions_imported += 1
            self._stats.last_updated_at = datetime.datetime.now()
            self._emit_event(VoxelEventKind.REGION_IMPORTED, {
                "voxel_count": count,
            })
            return count

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: Any,
        handler: Callable[[VoxelEvent], None],
    ) -> None:
        """Subscribe a handler to voxel events.

        Args:
            kind: The ``VoxelEventKind`` (or its string value) to
                subscribe to. Pass ``None`` to subscribe to all events.
            handler: Callable invoked with each matching ``VoxelEvent``.

        Raises:
            ValueError: If the handler limit (50) has been reached.
        """
        with self._lock:
            total = sum(len(v) for v in self._event_handlers.values())
            if total >= self._MAX_HANDLERS:
                raise ValueError(
                    f"Event handler limit reached ({self._MAX_HANDLERS})"
                )
            if kind is None:
                key = "*"
            elif isinstance(kind, VoxelEventKind):
                key = kind.value
            else:
                key = str(kind)
            self._event_handlers.setdefault(key, []).append(handler)

    def _emit_event(self, kind: VoxelEventKind,
                    payload: Optional[Dict[str, Any]] = None) -> VoxelEvent:
        """Create, log, and dispatch a voxel event (internal use)."""
        event = VoxelEvent(kind=kind, payload=payload or {})
        self._events.append(event)
        if len(self._events) > self._MAX_EVENTS:
            del self._events[: len(self._events) - self._MAX_EVENTS]
        self._dispatch_event(event)
        return event

    def _dispatch_event(self, event: VoxelEvent) -> None:
        """Deliver an event to all matching registered handlers."""
        kind_value = event.kind.value
        for key in (kind_value, "*"):
            handlers = self._event_handlers.get(key)
            if not handlers:
                continue
            for handler in list(handlers):
                try:
                    handler(event)
                except Exception:
                    # A failing handler must not break event dispatch.
                    pass

    def list_events(self, limit: int = 100) -> List[VoxelEvent]:
        """Return the most recent events, newest last."""
        with self._lock:
            if limit <= 0:
                return []
            if limit >= len(self._events):
                return list(self._events)
            return list(self._events[-limit:])

    # ------------------------------------------------------------------
    # Lighting
    # ------------------------------------------------------------------

    def compute_lighting(self, x: int, y: int, z: int) -> Dict[str, float]:
        """Compute sunlight and ambient occlusion at a voxel.

        Sunlight is 1.0 if the voxel has line of sight to the sky above,
        otherwise 0.0. Ambient occlusion approximates the fraction of
        open space among the eight neighbors in the horizontal plane
        and the block above.
        """
        with self._lock:
            # Sunlight: ray straight up to the world ceiling.
            sunlight = 1.0
            ceiling = self._config.world_height
            for sy in range(y + 1, ceiling):
                if self.get_voxel(x, sy, z).is_opaque():
                    sunlight = 0.0
                    break
            # Ambient occlusion: count open neighbors.
            open_count = 0
            total = 0
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dz == 0:
                        continue
                    total += 1
                    neighbor = self.get_voxel(x + dx, y, z + dz)
                    if not neighbor.is_opaque():
                        open_count += 1
            above = self.get_voxel(x, y + 1, z)
            if not above.is_opaque():
                open_count += 1
            total += 1
            ao = open_count / total if total > 0 else 1.0
            return {
                "sunlight": sunlight,
                "ambient_occlusion": round(ao, 4),
                "brightness": round(sunlight * 0.7 + ao * 0.3, 4),
            }

    # ------------------------------------------------------------------
    # Chunk state queries
    # ------------------------------------------------------------------

    def list_chunk_states(self) -> List[Dict[str, Any]]:
        """Return the state of every retained chunk."""
        with self._lock:
            result: List[Dict[str, Any]] = []
            for key, chunk in self._chunks.items():
                cx, cy, cz = key
                result.append({
                    "cx": cx,
                    "cy": cy,
                    "cz": cz,
                    "state": chunk.state.value,
                    "voxel_count": len(chunk.voxels),
                    "has_mesh": chunk.mesh is not None,
                })
            return result

    def get_dirty_chunks(self) -> List[Tuple[int, int, int]]:
        """Return the chunk-grid coordinates of all DIRTY chunks."""
        with self._lock:
            return [
                key for key, c in self._chunks.items()
                if c.state == ChunkState.DIRTY
            ]


# =============================================================================
# Module-level factory
# =============================================================================


def get_voxel_terrain() -> VoxelTerrainEngine:
    """Return the global VoxelTerrainEngine singleton instance."""
    return VoxelTerrainEngine.get_instance()
