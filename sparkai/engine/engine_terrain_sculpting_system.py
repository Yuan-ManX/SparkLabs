"""
SparkLabs Engine - Terrain Sculpting & Painting System

A comprehensive terrain editing system for the SparkLabs AI-native game
engine. Supports heightmap-based sculpting with multiple brush types,
texture layer painting, foliage placement, chunk-based LOD management,
and AI-assisted procedural terrain generation. Combines manual editing
tools with deterministic procedural generation to produce rich, varied
game worlds.

Architecture:
  TerrainSculptingSystem (singleton)
    |-- BrushType, BrushShape, BrushFalloff, TerrainLayer,
    |   TerrainResolution, FoliageType, TerrainStatus, SculptMode,
    |   TerrainEventKind
    |-- TerrainBrush, HeightmapData, TextureLayer, FoliageInstance,
    |   TerrainChunk, TerrainPatch, SculptStroke,
    |   TerrainSculptingConfig, TerrainSculptingStats,
    |   TerrainSculptingSnapshot, TerrainSculptingEvent
    |-- get_terrain_sculpting_system

Core Capabilities:
  - register_brush / get_brush / list_brushes / remove_brush:
    brush lifecycle management with type, shape, and falloff.
  - create_terrain / get_terrain / list_terrains / remove_terrain:
    terrain patch lifecycle with heightmap data and resolution.
  - sculpt_terrain: apply brush operations (raise, lower, smooth,
    flatten, noise, clay, pinch, inflate, twist, mask) to heightmaps.
  - paint_texture / create_texture_layer / remove_texture_layer:
    texture layer painting with coverage masks and blend modes.
  - add_foliage / remove_foliage / list_foliage:
    foliage instance placement with type, scale, and rotation.
  - set_height / get_height / import_heightmap / export_heightmap:
    direct heightmap value manipulation and data interchange.
  - create_chunk / get_chunk / list_chunks:
    chunk-based spatial subdivision for LOD and streaming.
  - bake_terrain / export_terrain / get_terrain_info:
    terrain finalization, export, and inspection.
  - auto_generate_terrain: AI-assisted procedural terrain generation
    from biome, elevation, and roughness parameters.
  - suggest_foliage: AI-assisted foliage placement suggestions based
    on heightmap analysis (height, slope, biome).
  - optimize_terrain: AI-assisted chunk LOD optimization based on
    camera distance and terrain complexity.
  - tick / set_config / get_config / get_status / get_stats /
    get_snapshot / list_events / reset: system lifecycle and
    observability.

Brush Types:
  - RAISE: increase terrain height
  - LOWER: decrease terrain height
  - SMOOTH: average heights with neighbors
  - FLATTEN: move heights toward a target value
  - PAINT: apply texture layer coverage
  - ERASE: remove texture layer coverage
  - NOISE: add procedural noise to heights
  - CLAY: build up material with a flat cap
  - PINCH: pull heights toward brush center
  - INFLATE: push heights away from brush center
  - TWIST: rotate heights around brush center
  - MASK: mark cells as non-editable

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`TerrainSculptingSystem.get_instance` or the module-level
:func:`get_terrain_sculpting_system` factory.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TERRAINS: int = 1000
_MAX_BRUSHES: int = 500
_MAX_HEIGHTMAPS: int = 1000
_MAX_TEXTURE_LAYERS: int = 5000
_MAX_FOLIAGE: int = 50000
_MAX_CHUNKS: int = 8000
_MAX_STROKES: int = 10000
_MAX_EVENTS: int = 10000
_MAX_BRUSH_SIZE: int = 256
_MIN_BRUSH_SIZE: int = 1
_MAX_RESOLUTION_SIZE: int = 1024


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits within max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits within max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a string or enum value into the given enum class."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into a JSON-serializable form."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance into a dict.

    Checks ``__dataclass_fields__`` BEFORE ``to_dict`` so that dataclass
    instances are serialized by iterating their declared fields rather than
    re-entering their own ``to_dict`` method.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a float to the given range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        if value is None or value == "":
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _mean(values: List[float]) -> float:
    """Return the arithmetic mean of a list of floats."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _compute_falloff(falloff: Any, normalized_distance: float) -> float:
    """Compute brush weight at a normalized distance [0, 1] from center."""
    d = _clamp(normalized_distance, 0.0, 1.0)
    if falloff == BrushFalloff.CONSTANT:
        return 1.0
    if falloff == BrushFalloff.LINEAR:
        return max(0.0, 1.0 - d)
    if falloff == BrushFalloff.SMOOTH:
        # Smoothstep falloff for natural transitions
        return max(0.0, 1.0 - (d * d * (3.0 - 2.0 * d)))
    if falloff == BrushFalloff.SHARP:
        return max(0.0, (1.0 - d) ** 3)
    if falloff == BrushFalloff.SINE:
        return max(0.0, math.cos(d * math.pi * 0.5))
    # Default to linear for CUSTOM or unknown falloff
    return max(0.0, 1.0 - d)


def _brush_weight(shape: Any, falloff: Any, dx: float, dy: float,
                  radius: float) -> float:
    """Compute the combined shape + falloff weight at offset (dx, dy)."""
    if radius <= 0:
        return 0.0
    if shape == BrushShape.SQUARE:
        dist = max(abs(dx), abs(dy))
        if dist > radius:
            return 0.0
        nd = dist / radius
    elif shape == BrushShape.DIAMOND:
        dist = abs(dx) + abs(dy)
        if dist > radius:
            return 0.0
        nd = dist / radius
    elif shape == BrushShape.STAR:
        dist = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx) if (dx != 0 or dy != 0) else 0.0
        star_r = radius * (0.4 + 0.6 * abs(math.cos(2.5 * angle)))
        if dist > star_r:
            return 0.0
        nd = dist / star_r if star_r > 0 else 0.0
    else:
        # CIRCLE and CUSTOM default to circular
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > radius:
            return 0.0
        nd = dist / radius
    return _compute_falloff(falloff, nd)


def _resolution_size(resolution: Any) -> int:
    """Map a TerrainResolution enum to its grid dimension."""
    sizes = {
        TerrainResolution.LOW_64: 64,
        TerrainResolution.MEDIUM_128: 128,
        TerrainResolution.HIGH_256: 256,
        TerrainResolution.ULTRA_512: 512,
        TerrainResolution.EXTREME_1024: 1024,
    }
    return sizes.get(resolution, 64)


def _gen_heightmap(size: int, pattern: str, seed_val: float = 1.0) -> List[List[float]]:
    """Generate a deterministic heightmap for seed terrain data."""
    data: List[List[float]] = []
    for y in range(size):
        row: List[float] = []
        for x in range(size):
            nx = x / max(1, size - 1)
            ny = y / max(1, size - 1)
            if pattern == "plains":
                # Gentle rolling hills with low amplitude
                h = 12.0
                h += 3.0 * math.sin(nx * 6.0 + seed_val) * math.cos(ny * 6.0)
                h += 1.5 * math.sin(nx * 12.0 + 0.5) * math.cos(ny * 14.0)
                h += 0.5 * math.sin(nx * 24.0) * math.cos(ny * 22.0)
            elif pattern == "mountains":
                # Sharp peaks with radial falloff from center
                cx, cy = 0.5, 0.5
                d = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
                h = 90.0 * max(0.0, 1.0 - d * 1.8)
                h += 25.0 * math.sin(nx * 18.0 + seed_val) * math.cos(ny * 18.0)
                h += 10.0 * math.sin(nx * 36.0) * math.cos(ny * 36.0)
                h = max(0.0, h)
            elif pattern == "desert":
                # Rolling dunes with cross-hatched wave patterns
                h = 8.0
                h += 3.0 * math.sin(nx * 5.0 + seed_val)
                h += 2.0 * math.sin(ny * 7.0 + 1.0)
                h += 1.0 * math.sin((nx + ny) * 9.0)
            elif pattern == "volcanic":
                # Volcanic cone with a central crater depression
                cx, cy = 0.5, 0.5
                d = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
                h = 70.0 * max(0.0, 1.0 - d * 2.2)
                if d < 0.1:
                    h -= 35.0  # crater bowl
                h += 4.0 * math.sin(nx * 16.0) * math.cos(ny * 16.0)
                h = max(0.0, h)
            elif pattern == "ocean":
                # Underwater terrain with raised shorelines
                h = -12.0
                h += 4.0 * math.sin(nx * 4.0 + seed_val) * math.cos(ny * 4.0)
                if nx < 0.15 or nx > 0.85 or ny < 0.15 or ny > 0.85:
                    h += 15.0
            elif pattern == "tundra":
                # Flat frozen landscape with minor variation
                h = 20.0
                h += 1.0 * math.sin(nx * 3.0) * math.cos(ny * 3.0)
            else:
                h = 10.0 + 5.0 * math.sin(nx * 4.0) * math.cos(ny * 4.0)
            row.append(round(h, 3))
        data.append(row)
    return data


def _gen_coverage(size: int, heightmap_data: List[List[float]],
                  min_h: float = -9999.0, max_h: float = 9999.0) -> List[List[float]]:
    """Generate a coverage mask based on height thresholds."""
    coverage: List[List[float]] = []
    for y in range(size):
        row: List[float] = []
        for x in range(size):
            h = 0.0
            if y < len(heightmap_data) and x < len(heightmap_data[y]):
                h = heightmap_data[y][x]
            row.append(1.0 if min_h <= h <= max_h else 0.0)
        coverage.append(row)
    return coverage


def _gen_procedural(size: int, biome: str, elevation: float,
                    roughness: float, seed_val: float) -> List[List[float]]:
    """Procedurally generate a heightmap from biome and parameters."""
    data: List[List[float]] = []
    for y in range(size):
        row: List[float] = []
        for x in range(size):
            nx = x / max(1, size - 1)
            ny = y / max(1, size - 1)
            # Multi-octave noise approximation using layered sine functions
            n = 0.0
            amp = 1.0
            freq = 2.0
            for _ in range(4):
                n += amp * math.sin(nx * freq * 6.28 + seed_val) * math.cos(
                    ny * freq * 6.28 + seed_val * 0.7)
                amp *= 0.5
                freq *= 2.0
            n = (n + 2.0) / 4.0  # normalize to approximately 0-1
            n = _clamp(n, 0.0, 1.0)

            if biome == "mountains":
                h = elevation * 60.0 * (n ** 1.5)
            elif biome == "plains":
                h = elevation * 15.0 + n * 8.0 * roughness
            elif biome == "desert":
                h = elevation * 8.0 + math.sin(nx * 8.0) * math.cos(ny * 8.0) * 3.0 * roughness
            elif biome == "ocean":
                h = -elevation * 20.0 + n * 10.0
            elif biome == "volcanic":
                cx, cy = 0.5, 0.5
                d = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
                h = elevation * 50.0 * max(0.0, 1.0 - d * 2.0)
                if d < 0.1:
                    h -= 25.0  # crater
                h += n * 5.0 * roughness
            elif biome == "tundra":
                h = elevation * 20.0 + n * 3.0 * roughness
            else:
                h = elevation * 20.0 + n * 10.0 * roughness
            row.append(round(h, 3))
        data.append(row)
    return data


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class BrushType(str, Enum):
    """All brush operation types for terrain sculpting."""
    RAISE = "raise"
    LOWER = "lower"
    SMOOTH = "smooth"
    FLATTEN = "flatten"
    PAINT = "paint"
    ERASE = "erase"
    NOISE = "noise"
    CLAY = "clay"
    PINCH = "pinch"
    INFLATE = "inflate"
    TWIST = "twist"
    MASK = "mask"


class BrushShape(str, Enum):
    """Geometric shapes that define the footprint of a brush."""
    CIRCLE = "circle"
    SQUARE = "square"
    DIAMOND = "diamond"
    STAR = "star"
    CUSTOM = "custom"


class BrushFalloff(str, Enum):
    """Falloff curves controlling brush intensity from center to edge."""
    CONSTANT = "constant"
    LINEAR = "linear"
    SMOOTH = "smooth"
    SHARP = "sharp"
    SINE = "sine"
    CUSTOM = "custom"


class TerrainLayer(str, Enum):
    """Texture layer types that can be painted onto terrain."""
    BASE = "base"
    GRASS = "grass"
    ROCK = "rock"
    SAND = "sand"
    DIRT = "dirt"
    SNOW = "snow"
    WATER = "water"
    LAVA = "lava"
    METAL = "metal"
    ICE = "ice"
    ASH = "ash"
    MOSS = "moss"
    CUSTOM = "custom"


class TerrainResolution(str, Enum):
    """Heightmap grid resolutions supported by the system."""
    LOW_64 = "low_64"
    MEDIUM_128 = "medium_128"
    HIGH_256 = "high_256"
    ULTRA_512 = "ultra_512"
    EXTREME_1024 = "extreme_1024"


class FoliageType(str, Enum):
    """Categories of foliage that can be placed on terrain."""
    TREE = "tree"
    BUSH = "bush"
    GRASS = "grass"
    FLOWER = "flower"
    ROCK = "rock"
    MUSHROOM = "mushroom"
    FERN = "fern"
    SAPLING = "sapling"
    DEAD_TREE = "dead_tree"
    STUMP = "stump"
    CUSTOM = "custom"


class TerrainStatus(str, Enum):
    """Lifecycle states of a terrain patch."""
    DRAFT = "draft"
    EDITING = "editing"
    BAKED = "baked"
    EXPORTED = "exported"
    ARCHIVED = "archived"
    ERROR = "error"


class SculptMode(str, Enum):
    """Active editing mode for the sculpting system."""
    SCULPT = "sculpt"
    PAINT = "paint"
    FOLIAGE = "foliage"
    MASK = "mask"
    NOISE = "noise"


class TerrainEventKind(str, Enum):
    """Audit event types emitted by the terrain sculpting system."""
    BRUSH_REGISTERED = "brush_registered"
    BRUSH_REMOVED = "brush_removed"
    TERRAIN_CREATED = "terrain_created"
    TERRAIN_REMOVED = "terrain_removed"
    TERRAIN_SCULPTED = "terrain_sculpted"
    TEXTURE_PAINTED = "texture_painted"
    TEXTURE_LAYER_CREATED = "texture_layer_created"
    TEXTURE_LAYER_REMOVED = "texture_layer_removed"
    FOLIAGE_ADDED = "foliage_added"
    FOLIAGE_REMOVED = "foliage_removed"
    HEIGHT_SET = "height_set"
    HEIGHTMAP_IMPORTED = "heightmap_imported"
    CHUNK_CREATED = "chunk_created"
    TERRAIN_BAKED = "terrain_baked"
    TERRAIN_EXPORTED = "terrain_exported"
    TERRAIN_GENERATED = "terrain_generated"
    TERRAIN_OPTIMIZED = "terrain_optimized"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class TerrainBrush:
    """Definition of a sculpting brush with type, shape, and falloff."""
    brush_id: str = ""
    name: str = ""
    brush_type: BrushType = BrushType.RAISE
    shape: BrushShape = BrushShape.CIRCLE
    falloff: BrushFalloff = BrushFalloff.SMOOTH
    size: int = 10
    inner_radius: float = 0.0
    strength: float = 1.0
    color: str = "#FFFFFF"
    spacing: float = 0.25
    target_height: float = 0.0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HeightmapData:
    """A 2D grid of height values representing terrain elevation."""
    heightmap_id: str = ""
    terrain_id: str = ""
    resolution: int = 64
    width: int = 64
    height: int = 64
    min_height: float = 0.0
    max_height: float = 100.0
    data: List[List[float]] = field(default_factory=list)
    mask: Dict[str, bool] = field(default_factory=dict)
    modified_cells: int = 0
    created_at: str = field(default_factory=_now)

    @property
    def cell_count(self) -> int:
        return self.width * self.height

    def is_masked(self, x: int, y: int) -> bool:
        return self.mask.get(f"{x},{y}", False)

    def set_mask(self, x: int, y: int, masked: bool) -> None:
        key = f"{x},{y}"
        if masked:
            self.mask[key] = True
        else:
            self.mask.pop(key, None)

    def to_dict(self) -> Dict[str, Any]:
        result = _dataclass_to_dict(self)
        result["cell_count"] = self.cell_count
        return result


@dataclass
class TextureLayer:
    """A paintable texture layer with a per-cell coverage mask."""
    layer_id: str = ""
    terrain_id: str = ""
    layer_type: TerrainLayer = TerrainLayer.BASE
    texture_path: str = ""
    color: str = "#888888"
    opacity: float = 1.0
    tile_size: float = 1.0
    blend_mode: str = "normal"
    coverage: List[List[float]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FoliageInstance:
    """A single placed foliage object on the terrain."""
    foliage_id: str = ""
    terrain_id: str = ""
    foliage_type: FoliageType = FoliageType.TREE
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    health: float = 1.0
    color: str = "#4CAF50"
    is_static: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainChunk:
    """A spatial subdivision of a terrain for LOD and streaming."""
    chunk_id: str = ""
    terrain_id: str = ""
    chunk_x: int = 0
    chunk_y: int = 0
    size: int = 64
    lod_level: int = 0
    is_loaded: bool = True
    is_dirty: bool = False
    vertex_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    @property
    def is_active(self) -> bool:
        return self.is_loaded and not self.is_dirty

    def to_dict(self) -> Dict[str, Any]:
        result = _dataclass_to_dict(self)
        result["is_active"] = self.is_active
        return result


@dataclass
class TerrainPatch:
    """The main terrain entity with heightmap, layers, foliage, and chunks."""
    terrain_id: str = ""
    name: str = ""
    resolution: TerrainResolution = TerrainResolution.LOW_64
    width: int = 64
    height: int = 64
    heightmap_id: str = ""
    texture_layer_ids: List[str] = field(default_factory=list)
    foliage_ids: List[str] = field(default_factory=list)
    chunk_ids: List[str] = field(default_factory=list)
    status: str = TerrainStatus.DRAFT.value
    biome: str = "plains"
    min_height: float = 0.0
    max_height: float = 100.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    baked_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def foliage_count(self) -> int:
        return len(self.foliage_ids)

    @property
    def chunk_count(self) -> int:
        return len(self.chunk_ids)

    @property
    def layer_count(self) -> int:
        return len(self.texture_layer_ids)

    def to_dict(self) -> Dict[str, Any]:
        result = _dataclass_to_dict(self)
        result["foliage_count"] = self.foliage_count
        result["chunk_count"] = self.chunk_count
        result["layer_count"] = self.layer_count
        return result


@dataclass
class SculptStroke:
    """A recorded sculpting operation for undo history and audit."""
    stroke_id: str = ""
    terrain_id: str = ""
    brush_id: str = ""
    brush_type: str = BrushType.RAISE.value
    center_x: float = 0.0
    center_y: float = 0.0
    strength: float = 1.0
    affected_cells: int = 0
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainSculptingConfig:
    """Global tuning parameters for the terrain sculpting system."""
    default_terrain_size: int = 64
    default_resolution: str = TerrainResolution.LOW_64.value
    default_mode: str = SculptMode.SCULPT.value
    max_brush_size: int = 128
    min_brush_size: int = 1
    default_brush_strength: float = 1.0
    enable_auto_lod: bool = True
    lod_distance: float = 128.0
    enable_collision: bool = True
    height_scale: float = 1.0
    enable_foliage_collision: bool = True
    max_foliage_per_terrain: int = 5000
    texture_blend_steps: int = 8
    enable_undo: bool = True
    max_strokes: int = 2000
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainSculptingStats:
    """Aggregate statistics for the terrain sculpting system."""
    total_terrains: int = 0
    total_brushes: int = 0
    total_foliage: int = 0
    total_chunks: int = 0
    total_strokes: int = 0
    total_bakes: int = 0
    active_terrains: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainSculptingSnapshot:
    """Full state snapshot of the terrain sculpting system."""
    timestamp: str = field(default_factory=_now)
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    terrains: List[Dict[str, Any]] = field(default_factory=list)
    brushes: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainSculptingEvent:
    """An audit event emitted by the terrain sculpting system."""
    event_id: str = ""
    timestamp: str = field(default_factory=_now)
    event_type: str = ""
    terrain_id: str = ""
    brush_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Terrain Sculpting System
# ---------------------------------------------------------------------------


class TerrainSculptingSystem:
    """Manages terrain brushes, heightmaps, texture layers, foliage, chunks,
    and procedural generation for the SparkLabs engine."""

    _instance: Optional["TerrainSculptingSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        # Primary storage containers
        self._brushes: Dict[str, TerrainBrush] = {}
        self._terrains: Dict[str, TerrainPatch] = {}
        self._heightmaps: Dict[str, HeightmapData] = {}
        self._texture_layers: Dict[str, TextureLayer] = {}
        self._foliage: Dict[str, FoliageInstance] = {}
        self._chunks: Dict[str, TerrainChunk] = {}
        self._strokes: List[SculptStroke] = []
        self._events: List[TerrainSculptingEvent] = []
        # Configuration and statistics
        self._config = TerrainSculptingConfig()
        self._stats = TerrainSculptingStats()
        self._tick_count: int = 0
        # Indexes for fast per-terrain lookups
        self._terrain_foliage: Dict[str, List[str]] = {}
        self._terrain_layers: Dict[str, List[str]] = {}
        self._terrain_chunks: Dict[str, List[str]] = {}
        self.initialize()

    @classmethod
    def get_instance(cls) -> "TerrainSculptingSystem":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._seed()
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, terrain_id: str = "", brush_id: str = "",
              description: str = "", data: Optional[Dict[str, Any]] = None) -> None:
        """Append an audit event to the event log."""
        event = TerrainSculptingEvent(
            event_id=_new_id("evt"),
            timestamp=_now(),
            event_type=event_type,
            terrain_id=terrain_id,
            brush_id=brush_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from current storage."""
        self._stats.total_terrains = len(self._terrains)
        self._stats.total_brushes = len(self._brushes)
        self._stats.total_foliage = len(self._foliage)
        self._stats.total_chunks = len(self._chunks)
        self._stats.total_strokes = len(self._strokes)
        self._stats.active_terrains = sum(
            1 for t in self._terrains.values()
            if t.status in (TerrainStatus.DRAFT.value, TerrainStatus.EDITING.value)
        )
        self._stats.tick_count = self._tick_count

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with default brushes, terrains, and data."""
        self._seed_brushes()
        self._seed_terrains()
        self._seed_texture_layers()
        self._seed_foliage()
        self._seed_chunks()
        self._seed_strokes()
        self._seed_events()
        self._refresh_stats()

    def _seed_brushes(self) -> None:
        brush_defs = [
            ("Raise", BrushType.RAISE, BrushShape.CIRCLE, BrushFalloff.SMOOTH, 10, 1.0, "#4CAF50"),
            ("Lower", BrushType.LOWER, BrushShape.CIRCLE, BrushFalloff.SMOOTH, 10, 1.0, "#F44336"),
            ("Smooth", BrushType.SMOOTH, BrushShape.CIRCLE, BrushFalloff.LINEAR, 8, 0.8, "#2196F3"),
            ("Flatten", BrushType.FLATTEN, BrushShape.CIRCLE, BrushFalloff.LINEAR, 12, 0.6, "#FF9800"),
            ("Paint Grass", BrushType.PAINT, BrushShape.CIRCLE, BrushFalloff.SMOOTH, 10, 1.0, "#8BC34A"),
            ("Noise", BrushType.NOISE, BrushShape.CIRCLE, BrushFalloff.SHARP, 6, 0.5, "#9C27B0"),
            ("Clay", BrushType.CLAY, BrushShape.CIRCLE, BrushFalloff.SHARP, 8, 0.7, "#795548"),
            ("Pinch", BrushType.PINCH, BrushShape.CIRCLE, BrushFalloff.SHARP, 6, 0.5, "#607D8B"),
            ("Erase", BrushType.ERASE, BrushShape.CIRCLE, BrushFalloff.LINEAR, 10, 1.0, "#E0E0E0"),
        ]
        for i, (name, btype, bshape, bfalloff, size, strength, color) in enumerate(brush_defs):
            bid = f"brush_seed_{i + 1}"
            self._brushes[bid] = TerrainBrush(
                brush_id=bid, name=name, brush_type=btype, shape=bshape,
                falloff=bfalloff, size=size, strength=strength, color=color,
            )

    def _seed_terrains(self) -> None:
        terrain_defs = [
            ("terrain_plains", "Verdant Plains", "plains",
             TerrainResolution.LOW_64, 0.0, 25.0),
            ("terrain_mountains", "Frostpeak Mountains", "mountains",
             TerrainResolution.LOW_64, 0.0, 120.0),
            ("terrain_desert", "Sunscorched Dunes", "desert",
             TerrainResolution.LOW_64, 0.0, 20.0),
            ("terrain_volcanic", "Ember Caldera", "volcanic",
             TerrainResolution.LOW_64, 0.0, 80.0),
        ]
        for tid, name, pattern, resolution, min_h, max_h in terrain_defs:
            size = _resolution_size(resolution)
            heightmap_data = _gen_heightmap(size, pattern)
            hm_id = f"hm_{tid}"
            self._heightmaps[hm_id] = HeightmapData(
                heightmap_id=hm_id, terrain_id=tid, resolution=size,
                width=size, height=size, min_height=min_h, max_height=max_h,
                data=heightmap_data,
            )
            now = _now()
            self._terrains[tid] = TerrainPatch(
                terrain_id=tid, name=name, resolution=resolution,
                width=size, height=size, heightmap_id=hm_id,
                status=TerrainStatus.EDITING.value, biome=pattern,
                min_height=min_h, max_height=max_h,
                created_at=now, updated_at=now,
            )
            self._terrain_foliage[tid] = []
            self._terrain_layers[tid] = []
            self._terrain_chunks[tid] = []

    def _seed_texture_layers(self) -> None:
        layer_defs = [
            ("layer_plains_grass", "terrain_plains", TerrainLayer.GRASS, "#4CAF50", 5.0, 25.0),
            ("layer_plains_dirt", "terrain_plains", TerrainLayer.DIRT, "#8B4513", -999.0, 5.0),
            ("layer_mountains_rock", "terrain_mountains", TerrainLayer.ROCK, "#808080", 30.0, 120.0),
            ("layer_mountains_snow", "terrain_mountains", TerrainLayer.SNOW, "#FFFAFA", 70.0, 120.0),
            ("layer_desert_sand", "terrain_desert", TerrainLayer.SAND, "#F4E22A", -999.0, 999.0),
            ("layer_volcanic_ash", "terrain_volcanic", TerrainLayer.ASH, "#3A3A3A", 0.0, 50.0),
            ("layer_volcanic_rock", "terrain_volcanic", TerrainLayer.ROCK, "#6E2A2A", 50.0, 999.0),
        ]
        for lid, tid, layer_type, color, min_h, max_h in layer_defs:
            terrain = self._terrains.get(tid)
            if terrain is None:
                continue
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None:
                continue
            coverage = _gen_coverage(heightmap.width, heightmap.data, min_h, max_h)
            self._texture_layers[lid] = TextureLayer(
                layer_id=lid, terrain_id=tid, layer_type=layer_type,
                color=color, coverage=coverage,
            )
            self._terrain_layers[tid].append(lid)

    def _seed_foliage(self) -> None:
        foliage_defs = [
            ("foliage_1", "terrain_plains", FoliageType.TREE, 10, 10, 1.0, 0.0, 1.0),
            ("foliage_2", "terrain_plains", FoliageType.TREE, 20, 15, 1.2, 45.0, 1.0),
            ("foliage_3", "terrain_plains", FoliageType.TREE, 35, 25, 0.8, 90.0, 1.0),
            ("foliage_4", "terrain_plains", FoliageType.TREE, 45, 40, 1.1, 180.0, 1.0),
            ("foliage_5", "terrain_plains", FoliageType.BUSH, 15, 30, 0.5, 0.0, 1.0),
            ("foliage_6", "terrain_plains", FoliageType.BUSH, 40, 20, 0.6, 120.0, 1.0),
            ("foliage_7", "terrain_plains", FoliageType.GRASS, 25, 35, 0.3, 0.0, 1.0),
            ("foliage_8", "terrain_plains", FoliageType.GRASS, 30, 45, 0.3, 60.0, 1.0),
            ("foliage_9", "terrain_mountains", FoliageType.ROCK, 20, 20, 2.0, 0.0, 1.0),
            ("foliage_10", "terrain_mountains", FoliageType.ROCK, 40, 35, 1.5, 45.0, 1.0),
            ("foliage_11", "terrain_mountains", FoliageType.STUMP, 15, 25, 0.7, 0.0, 0.8),
            ("foliage_12", "terrain_volcanic", FoliageType.DEAD_TREE, 30, 30, 1.0, 90.0, 0.5),
        ]
        for fid, tid, ftype, fx, fy, scale, rotation, health in foliage_defs:
            terrain = self._terrains.get(tid)
            if terrain is None:
                continue
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            z = 0.0
            if heightmap and 0 <= fy < heightmap.height and 0 <= fx < heightmap.width:
                z = heightmap.data[fy][fx]
            self._foliage[fid] = FoliageInstance(
                foliage_id=fid, terrain_id=tid, foliage_type=ftype,
                x=float(fx), y=float(fy), z=z, scale=scale,
                rotation=rotation, health=health,
            )
            self._terrain_foliage[tid].append(fid)

    def _seed_chunks(self) -> None:
        chunk_defs = [
            ("chunk_plains_0_0", "terrain_plains", 0, 0, 64),
            ("chunk_mountains_0_0", "terrain_mountains", 0, 0, 64),
            ("chunk_desert_0_0", "terrain_desert", 0, 0, 64),
            ("chunk_volcanic_0_0", "terrain_volcanic", 0, 0, 64),
        ]
        for cid, tid, cx, cy, size in chunk_defs:
            self._chunks[cid] = TerrainChunk(
                chunk_id=cid, terrain_id=tid, chunk_x=cx, chunk_y=cy,
                size=size, vertex_count=size * size,
            )
            self._terrain_chunks[tid].append(cid)

    def _seed_strokes(self) -> None:
        stroke_defs = [
            ("terrain_plains", "brush_seed_1", BrushType.RAISE, 32, 32, 1.0, 45),
            ("terrain_mountains", "brush_seed_3", BrushType.SMOOTH, 30, 30, 0.8, 38),
            ("terrain_desert", "brush_seed_2", BrushType.LOWER, 25, 25, 1.0, 52),
            ("terrain_plains", "brush_seed_4", BrushType.FLATTEN, 40, 40, 0.6, 30),
            ("terrain_volcanic", "brush_seed_6", BrushType.NOISE, 35, 35, 0.5, 28),
        ]
        for tid, bid, btype, cx, cy, strength, affected in stroke_defs:
            self._strokes.append(SculptStroke(
                stroke_id=_new_id("stroke"),
                terrain_id=tid, brush_id=bid, brush_type=btype.value,
                center_x=float(cx), center_y=float(cy),
                strength=strength, affected_cells=affected,
            ))
        _evict_fifo_list(self._strokes, _MAX_STROKES)

    def _seed_events(self) -> None:
        event_defs = [
            (TerrainEventKind.BRUSH_REGISTERED, "", "", "9 brushes registered"),
            (TerrainEventKind.TERRAIN_CREATED, "terrain_plains", "", "Verdant Plains created"),
            (TerrainEventKind.TERRAIN_CREATED, "terrain_mountains", "", "Frostpeak Mountains created"),
            (TerrainEventKind.TERRAIN_SCULPTED, "terrain_plains", "brush_seed_1", "Raised terrain at (32, 32)"),
            (TerrainEventKind.FOLIAGE_ADDED, "terrain_plains", "", "12 foliage instances placed"),
            (TerrainEventKind.TERRAIN_BAKED, "terrain_mountains", "", "Frostpeak Mountains baked"),
        ]
        for etype, tid, bid, desc in event_defs:
            self._events.append(TerrainSculptingEvent(
                event_id=_new_id("evt"),
                timestamp=_now(),
                event_type=etype.value,
                terrain_id=tid, brush_id=bid, description=desc,
            ))
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Brush Management
    # ------------------------------------------------------------------

    def register_brush(self, name: str, brush_type: str = "raise",
                       shape: str = "circle", falloff: str = "smooth",
                       size: int = 10, strength: float = 1.0,
                       inner_radius: float = 0.0, color: str = "#FFFFFF",
                       spacing: float = 0.25, target_height: float = 0.0,
                       metadata: Optional[Dict[str, Any]] = None
                       ) -> Tuple[bool, str, Optional[TerrainBrush]]:
        """Register a new sculpting brush with the given parameters."""
        with self._lock:
            if not name:
                return False, "Brush name is required", None
            if len(self._brushes) >= _MAX_BRUSHES:
                return False, "Maximum brushes reached", None
            btype = _coerce_enum(BrushType, brush_type, BrushType.RAISE)
            bshape = _coerce_enum(BrushShape, shape, BrushShape.CIRCLE)
            bfalloff = _coerce_enum(BrushFalloff, falloff, BrushFalloff.SMOOTH)
            brush = TerrainBrush(
                brush_id=_new_id("brush"),
                name=name,
                brush_type=btype,
                shape=bshape,
                falloff=bfalloff,
                size=_safe_int(size, 10),
                strength=_clamp(_safe_float(strength, 1.0), 0.0, 10.0),
                inner_radius=_clamp(_safe_float(inner_radius, 0.0), 0.0, 1.0),
                color=color,
                spacing=_clamp(_safe_float(spacing, 0.25), 0.01, 1.0),
                target_height=_safe_float(target_height, 0.0),
                metadata=metadata or {},
            )
            self._brushes[brush.brush_id] = brush
            self._emit(TerrainEventKind.BRUSH_REGISTERED.value,
                       description=f"Brush {name} registered")
            return True, "success", brush

    def get_brush(self, brush_id: str) -> Optional[TerrainBrush]:
        """Return a brush by its ID, or None if not found."""
        with self._lock:
            return self._brushes.get(brush_id)

    def list_brushes(self, brush_type: Optional[str] = None,
                     shape: Optional[str] = None,
                     limit: int = 100) -> List[TerrainBrush]:
        """List brushes, optionally filtered by type and shape."""
        with self._lock:
            brushes = list(self._brushes.values())
            if brush_type is not None:
                bt = _coerce_enum(BrushType, brush_type)
                if bt is not None:
                    brushes = [b for b in brushes if b.brush_type == bt]
            if shape is not None:
                bs = _coerce_enum(BrushShape, shape)
                if bs is not None:
                    brushes = [b for b in brushes if b.shape == bs]
            cap = min(_safe_int(limit, 100), _MAX_BRUSHES)
            return brushes[:cap]

    def remove_brush(self, brush_id: str) -> Tuple[bool, str]:
        """Remove a brush by its ID."""
        with self._lock:
            if brush_id not in self._brushes:
                return False, f"Brush {brush_id} not found"
            del self._brushes[brush_id]
            self._emit(TerrainEventKind.BRUSH_REMOVED.value,
                       description=f"Brush {brush_id} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Terrain Management
    # ------------------------------------------------------------------

    def create_terrain(self, name: str, resolution: str = "low_64",
                       biome: str = "plains", min_height: float = 0.0,
                       max_height: float = 100.0,
                       metadata: Optional[Dict[str, Any]] = None
                       ) -> Tuple[bool, str, Optional[TerrainPatch]]:
        """Create a new terrain patch with a blank heightmap."""
        with self._lock:
            if not name:
                return False, "Terrain name is required", None
            if len(self._terrains) >= _MAX_TERRAINS:
                return False, "Maximum terrains reached", None
            res = _coerce_enum(TerrainResolution, resolution, TerrainResolution.LOW_64)
            size = _resolution_size(res)
            tid = _new_id("terrain")
            hm_id = f"hm_{tid}"
            # Initialize a flat heightmap at the average height
            base_h = _safe_float(min_height, 0.0)
            flat_data = [[base_h for _ in range(size)] for _ in range(size)]
            self._heightmaps[hm_id] = HeightmapData(
                heightmap_id=hm_id, terrain_id=tid, resolution=size,
                width=size, height=size, min_height=min_height,
                max_height=max_height, data=flat_data,
            )
            now = _now()
            terrain = TerrainPatch(
                terrain_id=tid, name=name, resolution=res,
                width=size, height=size, heightmap_id=hm_id,
                status=TerrainStatus.DRAFT.value, biome=biome,
                min_height=min_height, max_height=max_height,
                created_at=now, updated_at=now, metadata=metadata or {},
            )
            self._terrains[tid] = terrain
            self._terrain_foliage[tid] = []
            self._terrain_layers[tid] = []
            self._terrain_chunks[tid] = []
            self._emit(TerrainEventKind.TERRAIN_CREATED.value,
                       terrain_id=tid, description=f"Terrain {name} created")
            return True, "success", terrain

    def get_terrain(self, terrain_id: str) -> Optional[TerrainPatch]:
        """Return a terrain patch by its ID, or None if not found."""
        with self._lock:
            return self._terrains.get(terrain_id)

    def list_terrains(self, status: Optional[str] = None,
                      biome: Optional[str] = None,
                      limit: int = 100) -> List[TerrainPatch]:
        """List terrain patches, optionally filtered by status and biome."""
        with self._lock:
            terrains = list(self._terrains.values())
            if status is not None:
                terrains = [t for t in terrains if t.status == status]
            if biome is not None:
                terrains = [t for t in terrains if t.biome == biome]
            cap = min(_safe_int(limit, 100), _MAX_TERRAINS)
            return terrains[:cap]

    def remove_terrain(self, terrain_id: str) -> Tuple[bool, str]:
        """Remove a terrain and all its associated heightmap, layers, foliage,
        and chunks."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found"
            # Remove heightmap
            self._heightmaps.pop(terrain.heightmap_id, None)
            # Remove texture layers
            for lid in self._terrain_layers.get(terrain_id, []):
                self._texture_layers.pop(lid, None)
            self._terrain_layers.pop(terrain_id, None)
            # Remove foliage
            for fid in self._terrain_foliage.get(terrain_id, []):
                self._foliage.pop(fid, None)
            self._terrain_foliage.pop(terrain_id, None)
            # Remove chunks
            for cid in self._terrain_chunks.get(terrain_id, []):
                self._chunks.pop(cid, None)
            self._terrain_chunks.pop(terrain_id, None)
            # Remove the terrain itself
            del self._terrains[terrain_id]
            self._emit(TerrainEventKind.TERRAIN_REMOVED.value,
                       terrain_id=terrain_id,
                       description=f"Terrain {terrain.name} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Sculpting & Heightmap Operations
    # ------------------------------------------------------------------

    def sculpt_terrain(self, terrain_id: str, brush_id: str,
                       center_x: float, center_y: float,
                       strength: float = 1.0, dt: float = 0.016
                       ) -> Tuple[bool, str]:
        """Apply a brush operation to the terrain heightmap at the given
        center coordinates."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found"
            brush = self._brushes.get(brush_id)
            if brush is None:
                return False, f"Brush {brush_id} not found"
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None:
                return False, f"Heightmap for terrain {terrain_id} not found"

            btype = brush.brush_type
            # PAINT and ERASE are handled by paint_texture, not sculpt_terrain
            if btype in (BrushType.PAINT, BrushType.ERASE):
                return False, "Use paint_texture for PAINT/ERASE brushes"

            radius = max(_MIN_BRUSH_SIZE, min(brush.size, _MAX_BRUSH_SIZE))
            cx = int(center_x)
            cy = int(center_y)
            str_val = _clamp(_safe_float(strength, 1.0), 0.0, 10.0) * brush.strength
            speed = _safe_float(dt, 0.016) * 60.0  # normalize to per-frame

            affected = 0
            center_height = 0.0
            if 0 <= cy < heightmap.height and 0 <= cx < heightmap.width:
                center_height = heightmap.data[cy][cx]

            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    px = cx + dx
                    py = cy + dy
                    if not (0 <= px < heightmap.width and 0 <= py < heightmap.height):
                        continue
                    if heightmap.is_masked(px, py):
                        continue
                    weight = _brush_weight(brush.shape, brush.falloff,
                                           float(dx), float(dy), float(radius))
                    if weight <= 0.0:
                        continue

                    current = heightmap.data[py][px]

                    if btype == BrushType.RAISE:
                        new_val = current + weight * str_val * speed
                    elif btype == BrushType.LOWER:
                        new_val = current - weight * str_val * speed
                    elif btype == BrushType.SMOOTH:
                        neighbors: List[float] = []
                        for ny in range(max(0, py - 1), min(heightmap.height, py + 2)):
                            for nx in range(max(0, px - 1), min(heightmap.width, px + 2)):
                                neighbors.append(heightmap.data[ny][nx])
                        avg = _mean(neighbors)
                        new_val = current + (avg - current) * weight * 0.5
                    elif btype == BrushType.FLATTEN:
                        target = brush.target_height
                        new_val = current + (target - current) * weight * 0.5
                    elif btype == BrushType.NOISE:
                        # Deterministic pseudo-random noise from coordinates
                        noise = (math.sin(px * 12.9898 + py * 78.233) * 43758.5453) % 1.0
                        noise = noise - 0.5
                        new_val = current + noise * weight * str_val * 2.0
                    elif btype == BrushType.CLAY:
                        # Build up material with a flat cap at target height
                        cap = brush.target_height if brush.target_height > 0 else center_height + str_val * speed
                        new_val = min(current + weight * str_val * speed, cap)
                    elif btype == BrushType.PINCH:
                        # Pull height toward the center height
                        new_val = current + (center_height - current) * weight * 0.3
                    elif btype == BrushType.INFLATE:
                        # Push height away from the center height
                        diff = current - center_height
                        new_val = current + diff * weight * 0.3
                    elif btype == BrushType.TWIST:
                        # Rotational offset based on angle from center
                        angle = math.atan2(dy, dx) if (dx != 0 or dy != 0) else 0.0
                        new_val = current + math.sin(angle * 3.0) * weight * str_val * speed * 0.5
                    elif btype == BrushType.MASK:
                        heightmap.set_mask(px, py, True)
                        affected += 1
                        continue
                    else:
                        new_val = current

                    heightmap.data[py][px] = round(
                        _clamp(new_val, heightmap.min_height, heightmap.max_height), 3)
                    affected += 1

            heightmap.modified_cells += affected
            terrain.updated_at = _now()
            terrain.status = TerrainStatus.EDITING.value

            # Record the stroke for undo and audit
            stroke = SculptStroke(
                stroke_id=_new_id("stroke"),
                terrain_id=terrain_id, brush_id=brush_id,
                brush_type=btype.value,
                center_x=float(cx), center_y=float(cy),
                strength=str_val, affected_cells=affected,
            )
            self._strokes.append(stroke)
            _evict_fifo_list(self._strokes, _MAX_STROKES)

            self._emit(TerrainEventKind.TERRAIN_SCULPTED.value,
                       terrain_id=terrain_id, brush_id=brush_id,
                       description=f"Sculpted {affected} cells with {brush.name}")
            return True, f"Sculpted {affected} cells"

    def paint_texture(self, terrain_id: str, layer: str,
                      center_x: float, center_y: float,
                      strength: float = 1.0,
                      brush_id: str = "") -> Tuple[bool, str]:
        """Paint a texture layer onto the terrain using a brush footprint."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found"
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None:
                return False, f"Heightmap for terrain {terrain_id} not found"

            # Resolve the target texture layer
            target_layer: Optional[TextureLayer] = None
            layer_enum = _coerce_enum(TerrainLayer, layer)
            for lid in self._terrain_layers.get(terrain_id, []):
                tl = self._texture_layers.get(lid)
                if tl is not None and (layer_enum is None or tl.layer_type == layer_enum):
                    target_layer = tl
                    break
            if target_layer is None:
                return False, f"No texture layer of type {layer} on terrain {terrain_id}"

            # Determine brush parameters
            brush = self._brushes.get(brush_id) if brush_id else None
            radius = brush.size if brush else 10
            shape = brush.shape if brush else BrushShape.CIRCLE
            falloff = brush.falloff if brush else BrushFalloff.SMOOTH
            str_val = _clamp(_safe_float(strength, 1.0), 0.0, 1.0)
            if brush:
                str_val *= brush.strength

            cx = int(center_x)
            cy = int(center_y)
            is_erase = brush is not None and brush.brush_type == BrushType.ERASE
            affected = 0

            # Ensure coverage grid matches heightmap dimensions
            if not target_layer.coverage or len(target_layer.coverage) != heightmap.height:
                target_layer.coverage = [
                    [0.0] * heightmap.width for _ in range(heightmap.height)
                ]

            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    px = cx + dx
                    py = cy + dy
                    if not (0 <= px < heightmap.width and 0 <= py < heightmap.height):
                        continue
                    weight = _brush_weight(shape, falloff,
                                           float(dx), float(dy), float(radius))
                    if weight <= 0.0:
                        continue
                    row = target_layer.coverage[py] if py < len(target_layer.coverage) else []
                    if px >= len(row):
                        continue
                    current = row[px]
                    if is_erase:
                        row[px] = round(_clamp(current - weight * str_val, 0.0, 1.0), 3)
                    else:
                        row[px] = round(_clamp(current + weight * str_val, 0.0, 1.0), 3)
                    affected += 1

            self._emit(TerrainEventKind.TEXTURE_PAINTED.value,
                       terrain_id=terrain_id,
                       description=f"Painted {layer} on {affected} cells")
            return True, f"Painted {affected} cells"

    def set_height(self, terrain_id: str, x: int, y: int,
                   height: float) -> Tuple[bool, str]:
        """Directly set the height value at a specific cell."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found"
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None:
                return False, f"Heightmap for terrain {terrain_id} not found"
            if not (0 <= x < heightmap.width and 0 <= y < heightmap.height):
                return False, f"Coordinates ({x}, {y}) out of bounds"
            if heightmap.is_masked(x, y):
                return False, f"Cell ({x}, {y}) is masked"
            clamped = round(
                _clamp(_safe_float(height, 0.0), heightmap.min_height, heightmap.max_height), 3)
            heightmap.data[y][x] = clamped
            heightmap.modified_cells += 1
            terrain.updated_at = _now()
            self._emit(TerrainEventKind.HEIGHT_SET.value,
                       terrain_id=terrain_id,
                       description=f"Height set to {clamped} at ({x}, {y})")
            return True, "success"

    def get_height(self, terrain_id: str, x: int, y: int) -> Optional[float]:
        """Return the height value at a specific cell, or None if invalid."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return None
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None:
                return None
            if not (0 <= x < heightmap.width and 0 <= y < heightmap.height):
                return None
            return heightmap.data[y][x]

    def import_heightmap(self, terrain_id: str,
                         data: List[List[float]]) -> Tuple[bool, str]:
        """Import a 2D list of height values to replace a terrain's heightmap."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found"
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None:
                return False, f"Heightmap for terrain {terrain_id} not found"
            if not data or not isinstance(data, list):
                return False, "Heightmap data must be a non-empty 2D list"
            new_height = len(data)
            new_width = len(data[0]) if new_height > 0 else 0
            if new_width == 0:
                return False, "Heightmap data rows must not be empty"
            # Validate all rows have consistent width
            for row in data:
                if not isinstance(row, list) or len(row) != new_width:
                    return False, "All heightmap rows must have the same width"
            # Clamp all values to the heightmap's bounds
            clamped_data: List[List[float]] = []
            for row in data:
                clamped_row = [
                    round(_clamp(_safe_float(v, 0.0),
                                 heightmap.min_height, heightmap.max_height), 3)
                    for v in row
                ]
                clamped_data.append(clamped_row)
            heightmap.data = clamped_data
            heightmap.width = new_width
            heightmap.height = new_height
            heightmap.resolution = max(new_width, new_height)
            heightmap.modified_cells += new_width * new_height
            terrain.width = new_width
            terrain.height = new_height
            terrain.updated_at = _now()
            terrain.status = TerrainStatus.EDITING.value
            self._emit(TerrainEventKind.HEIGHTMAP_IMPORTED.value,
                       terrain_id=terrain_id,
                       description=f"Imported {new_width}x{new_height} heightmap")
            return True, f"Imported {new_width}x{new_height} heightmap"

    def export_heightmap(self, terrain_id: str) -> Optional[Dict[str, Any]]:
        """Export a terrain's heightmap data as a serializable dict."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return None
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None:
                return None
            return {
                "heightmap_id": heightmap.heightmap_id,
                "terrain_id": terrain_id,
                "width": heightmap.width,
                "height": heightmap.height,
                "resolution": heightmap.resolution,
                "min_height": heightmap.min_height,
                "max_height": heightmap.max_height,
                "modified_cells": heightmap.modified_cells,
                "data": heightmap.data,
            }

    # ------------------------------------------------------------------
    # Texture Layer Management
    # ------------------------------------------------------------------

    def create_texture_layer(self, terrain_id: str, layer: str,
                             color: str = "#888888",
                             texture_path: str = "",
                             opacity: float = 1.0,
                             tile_size: float = 1.0,
                             blend_mode: str = "normal"
                             ) -> Tuple[bool, str, Optional[TextureLayer]]:
        """Create a new texture layer on a terrain with a blank coverage mask."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found", None
            if len(self._texture_layers) >= _MAX_TEXTURE_LAYERS:
                return False, "Maximum texture layers reached", None
            layer_enum = _coerce_enum(TerrainLayer, layer, TerrainLayer.CUSTOM)
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            width = heightmap.width if heightmap else terrain.width
            height = heightmap.height if heightmap else terrain.height
            coverage = [[0.0] * width for _ in range(height)]
            lid = _new_id("layer")
            tl = TextureLayer(
                layer_id=lid, terrain_id=terrain_id, layer_type=layer_enum,
                texture_path=texture_path, color=color,
                opacity=_clamp(_safe_float(opacity, 1.0), 0.0, 1.0),
                tile_size=_safe_float(tile_size, 1.0),
                blend_mode=blend_mode, coverage=coverage,
            )
            self._texture_layers[lid] = tl
            terrain.texture_layer_ids.append(lid)
            self._terrain_layers.setdefault(terrain_id, []).append(lid)
            terrain.updated_at = _now()
            self._emit(TerrainEventKind.TEXTURE_LAYER_CREATED.value,
                       terrain_id=terrain_id,
                       description=f"Texture layer {layer_enum.value} created")
            return True, "success", tl

    def remove_texture_layer(self, terrain_id: str,
                             layer_id: str) -> Tuple[bool, str]:
        """Remove a texture layer from a terrain."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found"
            if layer_id not in self._texture_layers:
                return False, f"Texture layer {layer_id} not found"
            del self._texture_layers[layer_id]
            if layer_id in terrain.texture_layer_ids:
                terrain.texture_layer_ids.remove(layer_id)
            layer_list = self._terrain_layers.get(terrain_id, [])
            if layer_id in layer_list:
                layer_list.remove(layer_id)
            terrain.updated_at = _now()
            self._emit(TerrainEventKind.TEXTURE_LAYER_REMOVED.value,
                       terrain_id=terrain_id,
                       description=f"Texture layer {layer_id} removed")
            return True, "success"

    def list_texture_layers(self, terrain_id: str) -> List[TextureLayer]:
        """List all texture layers belonging to a terrain."""
        with self._lock:
            result: List[TextureLayer] = []
            for lid in self._terrain_layers.get(terrain_id, []):
                tl = self._texture_layers.get(lid)
                if tl is not None:
                    result.append(tl)
            return result

    # ------------------------------------------------------------------
    # Foliage Management
    # ------------------------------------------------------------------

    def add_foliage(self, terrain_id: str, foliage_type: str,
                    x: float, y: float, scale: float = 1.0,
                    rotation: float = 0.0, health: float = 1.0,
                    color: str = "#4CAF50", is_static: bool = True,
                    metadata: Optional[Dict[str, Any]] = None
                    ) -> Tuple[bool, str, Optional[FoliageInstance]]:
        """Place a single foliage instance on a terrain at the given position."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found", None
            existing = self._terrain_foliage.get(terrain_id, [])
            max_foliage = _safe_int(self._config.max_foliage_per_terrain, 5000)
            if len(existing) >= max_foliage:
                return False, "Maximum foliage per terrain reached", None
            if len(self._foliage) >= _MAX_FOLIAGE:
                return False, "Maximum foliage reached", None
            ftype = _coerce_enum(FoliageType, foliage_type, FoliageType.CUSTOM)
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            z = 0.0
            ix, iy = int(x), int(y)
            if heightmap and 0 <= iy < heightmap.height and 0 <= ix < heightmap.width:
                z = heightmap.data[iy][ix]
            fid = _new_id("foliage")
            instance = FoliageInstance(
                foliage_id=fid, terrain_id=terrain_id, foliage_type=ftype,
                x=_safe_float(x, 0.0), y=_safe_float(y, 0.0), z=z,
                scale=_clamp(_safe_float(scale, 1.0), 0.01, 100.0),
                rotation=_safe_float(rotation, 0.0),
                health=_clamp(_safe_float(health, 1.0), 0.0, 1.0),
                color=color, is_static=is_static,
                metadata=metadata or {},
            )
            self._foliage[fid] = instance
            terrain.foliage_ids.append(fid)
            self._terrain_foliage.setdefault(terrain_id, []).append(fid)
            terrain.updated_at = _now()
            self._emit(TerrainEventKind.FOLIAGE_ADDED.value,
                       terrain_id=terrain_id,
                       description=f"Foliage {ftype.value} placed at ({x}, {y})")
            return True, "success", instance

    def remove_foliage(self, foliage_id: str) -> Tuple[bool, str]:
        """Remove a foliage instance by its ID."""
        with self._lock:
            instance = self._foliage.get(foliage_id)
            if instance is None:
                return False, f"Foliage {foliage_id} not found"
            terrain = self._terrains.get(instance.terrain_id)
            if terrain is not None and foliage_id in terrain.foliage_ids:
                terrain.foliage_ids.remove(foliage_id)
            foliage_list = self._terrain_foliage.get(instance.terrain_id, [])
            if foliage_id in foliage_list:
                foliage_list.remove(foliage_id)
            del self._foliage[foliage_id]
            self._emit(TerrainEventKind.FOLIAGE_REMOVED.value,
                       terrain_id=instance.terrain_id,
                       description=f"Foliage {foliage_id} removed")
            return True, "success"

    def get_foliage(self, foliage_id: str) -> Optional[FoliageInstance]:
        """Return a foliage instance by its ID, or None if not found."""
        with self._lock:
            return self._foliage.get(foliage_id)

    def list_foliage(self, terrain_id: Optional[str] = None,
                     foliage_type: Optional[str] = None,
                     limit: int = 100) -> List[FoliageInstance]:
        """List foliage instances, optionally filtered by terrain and type."""
        with self._lock:
            if terrain_id is not None:
                ids = self._terrain_foliage.get(terrain_id, [])
                result = [self._foliage[fid] for fid in ids if fid in self._foliage]
            else:
                result = list(self._foliage.values())
            if foliage_type is not None:
                ft = _coerce_enum(FoliageType, foliage_type)
                if ft is not None:
                    result = [f for f in result if f.foliage_type == ft]
            cap = min(_safe_int(limit, 100), _MAX_FOLIAGE)
            return result[:cap]

    # ------------------------------------------------------------------
    # Chunk Management
    # ------------------------------------------------------------------

    def create_chunk(self, terrain_id: str, chunk_x: int, chunk_y: int,
                     size: int = 64) -> Tuple[bool, str, Optional[TerrainChunk]]:
        """Create a new terrain chunk at the given grid coordinates."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found", None
            if len(self._chunks) >= _MAX_CHUNKS:
                return False, "Maximum chunks reached", None
            cid = _new_id("chunk")
            chunk = TerrainChunk(
                chunk_id=cid, terrain_id=terrain_id,
                chunk_x=_safe_int(chunk_x, 0), chunk_y=_safe_int(chunk_y, 0),
                size=_safe_int(size, 64),
                vertex_count=_safe_int(size, 64) * _safe_int(size, 64),
            )
            self._chunks[cid] = chunk
            terrain.chunk_ids.append(cid)
            self._terrain_chunks.setdefault(terrain_id, []).append(cid)
            terrain.updated_at = _now()
            self._emit(TerrainEventKind.CHUNK_CREATED.value,
                       terrain_id=terrain_id,
                       description=f"Chunk created at ({chunk_x}, {chunk_y})")
            return True, "success", chunk

    def get_chunk(self, chunk_id: str) -> Optional[TerrainChunk]:
        """Return a chunk by its ID, or None if not found."""
        with self._lock:
            return self._chunks.get(chunk_id)

    def list_chunks(self, terrain_id: Optional[str] = None,
                    limit: int = 100) -> List[TerrainChunk]:
        """List chunks, optionally filtered by terrain."""
        with self._lock:
            if terrain_id is not None:
                ids = self._terrain_chunks.get(terrain_id, [])
                result = [self._chunks[cid] for cid in ids if cid in self._chunks]
            else:
                result = list(self._chunks.values())
            cap = min(_safe_int(limit, 100), _MAX_CHUNKS)
            return result[:cap]

    # ------------------------------------------------------------------
    # Bake, Export, and Inspection
    # ------------------------------------------------------------------

    def bake_terrain(self, terrain_id: str) -> Tuple[bool, str]:
        """Finalize a terrain by marking it as baked and cleaning up chunks."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return False, f"Terrain {terrain_id} not found"
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None:
                return False, f"Heightmap for terrain {terrain_id} not found"
            # Mark all chunks as clean (not dirty)
            for cid in self._terrain_chunks.get(terrain_id, []):
                chunk = self._chunks.get(cid)
                if chunk is not None:
                    chunk.is_dirty = False
                    chunk.lod_level = 0
            # Update terrain status
            now = _now()
            terrain.status = TerrainStatus.BAKED.value
            terrain.baked_at = now
            terrain.updated_at = now
            self._stats.total_bakes += 1
            self._emit(TerrainEventKind.TERRAIN_BAKED.value,
                       terrain_id=terrain_id,
                       description=f"Terrain {terrain.name} baked")
            return True, "success"

    def export_terrain(self, terrain_id: str,
                       fmt: str = "json") -> Optional[Dict[str, Any]]:
        """Export a complete terrain snapshot including heightmap, layers,
        foliage, and chunks."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return None
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            # Gather texture layers
            layers_data: List[Dict[str, Any]] = []
            for lid in self._terrain_layers.get(terrain_id, []):
                tl = self._texture_layers.get(lid)
                if tl is not None:
                    layers_data.append(tl.to_dict())
            # Gather foliage
            foliage_data: List[Dict[str, Any]] = []
            for fid in self._terrain_foliage.get(terrain_id, []):
                fi = self._foliage.get(fid)
                if fi is not None:
                    foliage_data.append(fi.to_dict())
            # Gather chunks
            chunk_data: List[Dict[str, Any]] = []
            for cid in self._terrain_chunks.get(terrain_id, []):
                ch = self._chunks.get(cid)
                if ch is not None:
                    chunk_data.append(ch.to_dict())
            # Update status to exported
            terrain.status = TerrainStatus.EXPORTED.value
            terrain.updated_at = _now()
            self._emit(TerrainEventKind.TERRAIN_EXPORTED.value,
                       terrain_id=terrain_id,
                       description=f"Terrain {terrain.name} exported as {fmt}")
            return {
                "format": fmt,
                "terrain": terrain.to_dict(),
                "heightmap": heightmap.to_dict() if heightmap else None,
                "texture_layers": layers_data,
                "foliage": foliage_data,
                "chunks": chunk_data,
                "exported_at": _now(),
            }

    def get_terrain_info(self, terrain_id: str) -> Optional[Dict[str, Any]]:
        """Return a summary dict with terrain, heightmap, and associated
        object counts."""
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return None
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            foliage_count = len(self._terrain_foliage.get(terrain_id, []))
            layer_count = len(self._terrain_layers.get(terrain_id, []))
            chunk_count = len(self._terrain_chunks.get(terrain_id, []))
            stroke_count = sum(
                1 for s in self._strokes if s.terrain_id == terrain_id)
            # Compute height statistics
            height_stats: Dict[str, float] = {"min": 0.0, "max": 0.0, "avg": 0.0}
            if heightmap and heightmap.data:
                all_vals = [v for row in heightmap.data for v in row]
                if all_vals:
                    height_stats = {
                        "min": round(min(all_vals), 3),
                        "max": round(max(all_vals), 3),
                        "avg": round(_mean(all_vals), 3),
                    }
            return {
                "terrain": terrain.to_dict(),
                "heightmap_id": terrain.heightmap_id,
                "resolution": heightmap.resolution if heightmap else 0,
                "width": heightmap.width if heightmap else terrain.width,
                "height": heightmap.height if heightmap else terrain.height,
                "modified_cells": heightmap.modified_cells if heightmap else 0,
                "masked_cells": len(heightmap.mask) if heightmap else 0,
                "height_stats": height_stats,
                "foliage_count": foliage_count,
                "texture_layer_count": layer_count,
                "chunk_count": chunk_count,
                "stroke_count": stroke_count,
            }

    # ------------------------------------------------------------------
    # System Lifecycle & Observability
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a brief status summary of the system."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_terrains": len(self._terrains),
                "total_brushes": len(self._brushes),
                "total_heightmaps": len(self._heightmaps),
                "total_texture_layers": len(self._texture_layers),
                "total_foliage": len(self._foliage),
                "total_chunks": len(self._chunks),
                "total_strokes": len(self._strokes),
                "total_events": len(self._events),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> TerrainSculptingStats:
        """Return aggregate statistics for the system."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> TerrainSculptingSnapshot:
        """Return a full state snapshot of the system."""
        with self._lock:
            self._refresh_stats()
            return TerrainSculptingSnapshot(
                timestamp=_now(),
                config=self._config.to_dict(),
                stats=self._stats.to_dict(),
                terrains=[t.to_dict() for t in list(self._terrains.values())[:20]],
                brushes=[b.to_dict() for b in list(self._brushes.values())[:20]],
                events=[e.to_dict() for e in self._events[-20:]],
            )

    def get_config(self) -> TerrainSculptingConfig:
        """Return the current system configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, TerrainSculptingConfig]:
        """Update system configuration parameters."""
        with self._lock:
            for key in ("default_terrain_size", "max_brush_size",
                        "min_brush_size", "max_foliage_per_terrain",
                        "texture_blend_steps", "max_strokes"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key,
                            _safe_int(kwargs[key], getattr(self._config, key)))
            for key in ("default_brush_strength", "lod_distance", "height_scale"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key,
                            _safe_float(kwargs[key], getattr(self._config, key)))
            for key in ("enable_auto_lod", "enable_collision",
                        "enable_foliage_collision", "enable_undo"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key, bool(kwargs[key]))
            if "default_resolution" in kwargs and kwargs["default_resolution"] is not None:
                res = _coerce_enum(TerrainResolution, kwargs["default_resolution"],
                                   TerrainResolution.LOW_64)
                self._config.default_resolution = res.value
            if "default_mode" in kwargs and kwargs["default_mode"] is not None:
                mode = _coerce_enum(SculptMode, kwargs["default_mode"],
                                    SculptMode.SCULPT)
                self._config.default_mode = mode.value
            self._emit(TerrainEventKind.CONFIG_UPDATED.value,
                       description="Configuration updated")
            return True, "success", self._config

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the system by one tick, performing auto-LOD if enabled."""
        with self._lock:
            self._tick_count += 1
            dt_val = _safe_float(dt, 0.016)
            auto_optimized = 0
            # Auto-optimize terrain LOD if enabled
            if self._config.enable_auto_lod:
                for terrain in self._terrains.values():
                    if terrain.status in (TerrainStatus.EDITING.value,
                                          TerrainStatus.DRAFT.value):
                        chunk_ids = self._terrain_chunks.get(terrain.terrain_id, [])
                        for cid in chunk_ids:
                            chunk = self._chunks.get(cid)
                            if chunk is None or not chunk.is_loaded:
                                continue
                            # Simplified LOD: mark dirty chunks for re-evaluation
                            if chunk.is_dirty:
                                chunk.is_dirty = False
                                auto_optimized += 1
            self._refresh_stats()
            self._emit(TerrainEventKind.TICK.value,
                       description=f"Tick {self._tick_count}")
            return {
                "tick": self._tick_count,
                "dt": dt_val,
                "total_terrains": len(self._terrains),
                "total_brushes": len(self._brushes),
                "total_foliage": len(self._foliage),
                "total_chunks": len(self._chunks),
                "total_strokes": len(self._strokes),
                "auto_optimized": auto_optimized,
            }

    def reset(self) -> None:
        """Clear all storage and re-seed the system with default data."""
        with self._lock:
            self._brushes.clear()
            self._terrains.clear()
            self._heightmaps.clear()
            self._texture_layers.clear()
            self._foliage.clear()
            self._chunks.clear()
            self._strokes.clear()
            self._events.clear()
            self._terrain_foliage.clear()
            self._terrain_layers.clear()
            self._terrain_chunks.clear()
            self._config = TerrainSculptingConfig()
            self._stats = TerrainSculptingStats()
            self._tick_count = 0
            self._initialized = False
            self._seed()
            self._initialized = True
            self._emit(TerrainEventKind.RESET.value,
                       description="System reset and re-seeded")

    def list_events(self, limit: int = 100) -> List[TerrainSculptingEvent]:
        """Return the most recent audit events."""
        with self._lock:
            cap = min(_safe_int(limit, 100), _MAX_EVENTS)
            return list(self._events[-cap:])

    # ------------------------------------------------------------------
    # AI-Assisted Terrain Generation & Analysis
    # ------------------------------------------------------------------

    def auto_generate_terrain(self, name: str, biome: str = "plains",
                              elevation: float = 1.0, roughness: float = 0.5,
                              resolution: str = "low_64", seed: float = 1.0,
                              metadata: Optional[Dict[str, Any]] = None
                              ) -> Tuple[bool, str, Optional[TerrainPatch]]:
        """Procedurally generate a new terrain from biome and parameters.

        Uses multi-octave noise and biome-specific shaping functions to
        produce a heightmap with realistic terrain features.
        """
        with self._lock:
            if not name:
                return False, "Terrain name is required", None
            if len(self._terrains) >= _MAX_TERRAINS:
                return False, "Maximum terrains reached", None
            res = _coerce_enum(TerrainResolution, resolution, TerrainResolution.LOW_64)
            size = _resolution_size(res)
            elev = _clamp(_safe_float(elevation, 1.0), 0.1, 10.0)
            rough = _clamp(_safe_float(roughness, 0.5), 0.0, 2.0)
            seed_val = _safe_float(seed, 1.0)

            # Generate the heightmap using procedural noise
            data = _gen_procedural(size, biome, elev, rough, seed_val)

            # Compute min and max heights from generated data
            all_vals = [v for row in data for v in row]
            min_h = min(all_vals) if all_vals else 0.0
            max_h = max(all_vals) if all_vals else 100.0
            # Ensure non-zero range for clamping
            if max_h <= min_h:
                max_h = min_h + 1.0

            tid = _new_id("terrain")
            hm_id = f"hm_{tid}"
            self._heightmaps[hm_id] = HeightmapData(
                heightmap_id=hm_id, terrain_id=tid, resolution=size,
                width=size, height=size, min_height=min_h, max_height=max_h,
                data=data,
            )
            now = _now()
            terrain = TerrainPatch(
                terrain_id=tid, name=name, resolution=res,
                width=size, height=size, heightmap_id=hm_id,
                status=TerrainStatus.EDITING.value, biome=biome,
                min_height=min_h, max_height=max_h,
                created_at=now, updated_at=now,
                metadata=metadata or {},
            )
            self._terrains[tid] = terrain
            self._terrain_foliage[tid] = []
            self._terrain_layers[tid] = []
            self._terrain_chunks[tid] = []
            self._emit(TerrainEventKind.TERRAIN_GENERATED.value,
                       terrain_id=tid,
                       description=f"Terrain {name} generated (biome={biome}, "
                                   f"elevation={elev}, roughness={rough})")
            return True, "success", terrain

    def suggest_foliage(self, terrain_id: str, density: float = 0.1,
                        max_suggestions: int = 50
                        ) -> List[Dict[str, Any]]:
        """Analyze the terrain heightmap and suggest foliage placements.

        Examines height, slope, and biome to determine suitable positions
        and foliage types. Returns a list of suggestion dicts.
        """
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return []
            heightmap = self._heightmaps.get(terrain.heightmap_id)
            if heightmap is None or not heightmap.data:
                return []

            density_val = _clamp(_safe_float(density, 0.1), 0.01, 1.0)
            max_sug = _safe_int(max_suggestions, 50)
            step = max(1, int(1.0 / density_val))
            suggestions: List[Dict[str, Any]] = []

            # Compute the height range for relative classification
            all_vals = [v for row in heightmap.data for v in row]
            if not all_vals:
                return []
            h_min = min(all_vals)
            h_max = max(all_vals)
            h_range = max(0.001, h_max - h_min)

            for y in range(0, heightmap.height, step):
                for x in range(0, heightmap.width, step):
                    h = heightmap.data[y][x]
                    # Compute approximate slope from neighbors
                    slope = 0.0
                    if 0 < x < heightmap.width - 1:
                        slope = abs(heightmap.data[y][x + 1] -
                                    heightmap.data[y][x - 1])
                    if 0 < y < heightmap.height - 1:
                        slope = max(slope, abs(heightmap.data[y + 1][x] -
                                               heightmap.data[y - 1][x]))

                    # Classify position and suggest foliage type
                    rel_h = (h - h_min) / h_range  # 0.0 to 1.0
                    suggestion: Optional[Dict[str, Any]] = None

                    if slope > 2.0:
                        # Steep slopes suit rocks
                        suggestion = {
                            "x": float(x), "y": float(y), "height": round(h, 3),
                            "slope": round(slope, 3),
                            "foliage_type": FoliageType.ROCK.value,
                            "reason": "Steep slope suitable for rocks",
                        }
                    elif rel_h < 0.15:
                        # Low elevation suits bushes and grass
                        suggestion = {
                            "x": float(x), "y": float(y), "height": round(h, 3),
                            "slope": round(slope, 3),
                            "foliage_type": FoliageType.BUSH.value,
                            "reason": "Low elevation suitable for bushes",
                        }
                    elif rel_h < 0.6 and slope < 1.0:
                        # Mid elevation with low slope suits trees
                        if terrain.biome == "desert":
                            ftype = FoliageType.ROCK.value
                            reason = "Flat desert area suitable for rocks"
                        elif terrain.biome == "volcanic":
                            ftype = FoliageType.DEAD_TREE.value
                            reason = "Volcanic terrain suitable for dead trees"
                        else:
                            ftype = FoliageType.TREE.value
                            reason = "Flat mid-elevation suitable for trees"
                        suggestion = {
                            "x": float(x), "y": float(y), "height": round(h, 3),
                            "slope": round(slope, 3),
                            "foliage_type": ftype,
                            "reason": reason,
                        }
                    elif rel_h > 0.85:
                        # High elevation suits snow or stumps
                        suggestion = {
                            "x": float(x), "y": float(y), "height": round(h, 3),
                            "slope": round(slope, 3),
                            "foliage_type": FoliageType.STUMP.value,
                            "reason": "High elevation suitable for stumps",
                        }

                    if suggestion is not None:
                        suggestions.append(suggestion)
                        if len(suggestions) >= max_sug:
                            return suggestions
            return suggestions

    def optimize_terrain(self, terrain_id: str, camera_x: float = 0.0,
                         camera_y: float = 0.0,
                         max_lod_distance: float = 0.0
                         ) -> Dict[str, Any]:
        """Optimize chunk LOD levels based on camera distance.

        Adjusts each chunk's LOD level and loaded state according to its
        distance from the camera position. Distant chunks are unloaded
        to reduce memory and rendering cost.
        """
        with self._lock:
            terrain = self._terrains.get(terrain_id)
            if terrain is None:
                return {"error": f"Terrain {terrain_id} not found"}
            lod_dist = _safe_float(max_lod_distance, self._config.lod_distance)
            if lod_dist <= 0:
                lod_dist = self._config.lod_distance

            chunk_ids = self._terrain_chunks.get(terrain_id, [])
            optimized = 0
            unloaded = 0
            loaded = 0

            for cid in chunk_ids:
                chunk = self._chunks.get(cid)
                if chunk is None:
                    continue
                # Compute world-space center of the chunk
                chunk_world_x = chunk.chunk_x * chunk.size + chunk.size * 0.5
                chunk_world_y = chunk.chunk_y * chunk.size + chunk.size * 0.5
                dist = math.sqrt(
                    (chunk_world_x - camera_x) ** 2 +
                    (chunk_world_y - camera_y) ** 2)

                # Determine LOD level and loaded state from distance
                old_lod = chunk.lod_level
                old_loaded = chunk.is_loaded

                if dist < lod_dist * 0.25:
                    chunk.lod_level = 0  # highest detail
                    chunk.is_loaded = True
                elif dist < lod_dist * 0.5:
                    chunk.lod_level = 1
                    chunk.is_loaded = True
                elif dist < lod_dist:
                    chunk.lod_level = 2
                    chunk.is_loaded = True
                else:
                    chunk.lod_level = 3  # lowest detail
                    chunk.is_loaded = False

                if chunk.lod_level != old_lod or chunk.is_loaded != old_loaded:
                    optimized += 1
                if not chunk.is_loaded:
                    unloaded += 1
                else:
                    loaded += 1

            terrain.updated_at = _now()
            self._emit(TerrainEventKind.TERRAIN_OPTIMIZED.value,
                       terrain_id=terrain_id,
                       description=f"Optimized {optimized} chunks "
                                   f"(loaded={loaded}, unloaded={unloaded})")
            return {
                "terrain_id": terrain_id,
                "total_chunks": len(chunk_ids),
                "optimized": optimized,
                "loaded": loaded,
                "unloaded": unloaded,
                "camera": (camera_x, camera_y),
                "max_lod_distance": lod_dist,
            }


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_terrain_sculpting_system() -> TerrainSculptingSystem:
    """Return the shared TerrainSculptingSystem singleton instance."""
    return TerrainSculptingSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "BrushType",
    "BrushShape",
    "BrushFalloff",
    "TerrainLayer",
    "TerrainResolution",
    "FoliageType",
    "TerrainStatus",
    "SculptMode",
    "TerrainEventKind",
    # Data classes
    "TerrainBrush",
    "HeightmapData",
    "TextureLayer",
    "FoliageInstance",
    "TerrainChunk",
    "TerrainPatch",
    "SculptStroke",
    "TerrainSculptingConfig",
    "TerrainSculptingStats",
    "TerrainSculptingSnapshot",
    "TerrainSculptingEvent",
    # Main system
    "TerrainSculptingSystem",
    "get_terrain_sculpting_system",
]