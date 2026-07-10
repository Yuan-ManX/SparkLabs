"""
SparkLabs Engine - Voxel World Building System

Block-based world construction, destruction, and procedural generation.
Manages voxel materials, 3D chunks, individual blocks, stampable
structures, reversible modifications, and biome-driven terrain
generation. Designed for the SparkLabs AI-native game engine.

Architecture:
  VoxelWorldSystem (singleton)
    |-- VoxelMaterialType, ChunkState, StructureType, BiomeType,
       ModificationType, VoxelWorldEventKind
    |-- VoxelMaterial, VoxelBlock, VoxelChunk, VoxelStructure,
       VoxelModification, BiomeConfig, VoxelWorldConfig,
       VoxelWorldStats, VoxelWorldSnapshot, VoxelWorldEvent
    |-- get_voxel_world_system

Core Capabilities:
  - register_material / get_material / list_materials / remove_material
  - register_biome / get_biome / list_biomes / remove_biome
  - get_chunk / list_chunks / generate_chunk / unload_chunk
  - get_block / set_block / remove_block / fill_area / clear_area
  - register_structure / get_structure / list_structures
  - place_structure / remove_structure
  - get_modifications / undo_modification
  - get_blocks_in_range / count_blocks_by_material
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`VoxelWorldSystem.get_instance` or the module-level
:func:`get_voxel_world_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_MATERIALS: int = 512
_MAX_BIOMES: int = 128
_MAX_CHUNKS: int = 4096
_MAX_STRUCTURES: int = 1024
_MAX_BLOCKS_PER_CHUNK: int = 65536
_MAX_MODIFICATIONS: int = 10000
_MAX_EVENTS: int = 10000
_FLUID_TICK_BUDGET: int = 256


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _chunk_key(chunk_x: int, chunk_y: int, chunk_z: int) -> str:
    return f"{chunk_x},{chunk_y},{chunk_z}"


def _block_key(x: int, y: int, z: int) -> str:
    return f"{x},{y},{z}"


def _dataclass_to_dict(obj: Any) -> Any:
    # Check __dataclass_fields__ BEFORE to_dict to avoid infinite recursion.
    # A dataclass instance has both attributes; iterating its fields directly
    # prevents re-entering its own to_dict method.
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            elif isinstance(v, Enum):
                result[k] = v.value
            else:
                result[k] = v
        return result
    if isinstance(obj, Enum):
        return obj.value
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VoxelMaterialType(str, Enum):
    """All block material types supported by the voxel world."""
    AIR = "air"
    STONE = "stone"
    DIRT = "dirt"
    GRASS = "grass"
    WOOD = "wood"
    LEAVES = "leaves"
    WATER = "water"
    LAVA = "lava"
    SAND = "sand"
    GRAVEL = "gravel"
    SNOW = "snow"
    ICE = "ice"
    COAL_ORE = "coal_ore"
    IRON_ORE = "iron_ore"
    GOLD_ORE = "gold_ore"
    DIAMOND_ORE = "diamond_ore"
    CRYSTAL = "crystal"
    METAL = "metal"
    GLASS = "glass"
    BRICK = "brick"
    PLANK = "plank"
    COBBLESTONE = "cobblestone"
    OBSIDIAN = "obsidian"
    BEDROCK = "bedrock"
    CLOUD = "cloud"
    SLIME = "slime"
    MAGMA = "magma"
    SOUL_SAND = "soul_sand"
    NETHERRACK = "netherrack"
    END_STONE = "end_stone"


class ChunkState(str, Enum):
    """Lifecycle state of a voxel chunk."""
    EMPTY = "empty"
    GENERATING = "generating"
    READY = "ready"
    DIRTY = "dirty"
    UNLOADING = "unloading"


class StructureType(str, Enum):
    """Categories of stampable voxel structures."""
    HOUSE = "house"
    TREE = "tree"
    CAVE = "cave"
    DUNGEON = "dungeon"
    TOWER = "tower"
    BRIDGE = "bridge"
    RUINS = "ruins"
    SHRINE = "shrine"
    CAMP = "camp"
    VILLAGE = "village"
    TEMPLE = "temple"
    MINE = "mine"


class BiomeType(str, Enum):
    """Biome categories driving terrain generation."""
    PLAINS = "plains"
    FOREST = "forest"
    DESERT = "desert"
    MOUNTAINS = "mountains"
    OCEAN = "ocean"
    TUNDRA = "tundra"
    SWAMP = "swamp"
    JUNGLE = "jungle"
    SAVANNA = "savanna"
    MESA = "mesa"
    NETHER = "nether"
    END = "end"
    SKY = "sky"


class ModificationType(str, Enum):
    """Kinds of reversible block modifications."""
    PLACE = "place"
    REMOVE = "remove"
    REPLACE = "replace"
    FILL = "fill"
    CLEAR = "clear"


class VoxelWorldEventKind(str, Enum):
    """Audit event types emitted by the voxel world system."""
    MATERIAL_REGISTERED = "material_registered"
    MATERIAL_REMOVED = "material_removed"
    BIOME_REGISTERED = "biome_registered"
    BIOME_REMOVED = "biome_removed"
    CHUNK_GENERATED = "chunk_generated"
    CHUNK_UNLOADED = "chunk_unloaded"
    BLOCK_SET = "block_set"
    BLOCK_REMOVED = "block_removed"
    AREA_FILLED = "area_filled"
    AREA_CLEARED = "area_cleared"
    STRUCTURE_REGISTERED = "structure_registered"
    STRUCTURE_REMOVED = "structure_removed"
    STRUCTURE_PLACED = "structure_placed"
    MODIFICATION_UNDONE = "modification_undone"
    FLUID_FLOWED = "fluid_flowed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class VoxelMaterial:
    """Definition of a voxel material and its physical properties."""
    material_id: str
    name: str
    material_type: str
    color: str = "#888888"
    hardness: float = 1.0
    transparency: float = 0.0
    light_emission: float = 0.0
    is_solid: bool = True
    is_fluid: bool = False
    is_breakable: bool = True
    tool_required: str = ""
    drop_item_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoxelBlock:
    """A single block instance placed in the world."""
    block_id: str
    chunk_id: str
    x: int
    y: int
    z: int
    material_type: str
    health: float = 1.0
    max_health: float = 1.0
    is_exposed: bool = False
    light_level: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoxelChunk:
    """A 3D grid slice of the world for efficient storage."""
    chunk_id: str
    chunk_x: int
    chunk_y: int
    chunk_z: int
    state: str = ChunkState.EMPTY.value
    blocks: Dict[str, VoxelBlock] = field(default_factory=dict)
    modified_blocks: Dict[str, Any] = field(default_factory=dict)
    biome_type: str = BiomeType.PLAINS.value
    is_generated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    def to_dict(self) -> Dict[str, Any]:
        result = _dataclass_to_dict(self)
        result["block_count"] = self.block_count
        return result


@dataclass
class VoxelStructure:
    """A pre-built structure that can be stamped into the world."""
    structure_id: str
    name: str
    structure_type: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    size_x: int = 1
    size_y: int = 1
    size_z: int = 1
    origin_x: int = 0
    origin_y: int = 0
    origin_z: int = 0
    biome_restriction: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    def to_dict(self) -> Dict[str, Any]:
        result = _dataclass_to_dict(self)
        result["block_count"] = self.block_count
        return result


@dataclass
class VoxelModification:
    """A tracked block change for undo/redo and persistence."""
    modification_id: str
    modification_type: str
    x: int
    y: int
    z: int
    old_material: str = ""
    new_material: str = ""
    player_id: str = ""
    timestamp: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_undone: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BiomeConfig:
    """Terrain generation parameters for a biome."""
    biome_id: str
    biome_type: str
    terrain_height_min: int = 0
    terrain_height_max: int = 64
    material_surface: str = "grass"
    material_underground: str = "dirt"
    material_deep: str = "stone"
    ore_chance: float = 0.05
    tree_chance: float = 0.1
    structure_chance: float = 0.02
    temperature: float = 0.5
    humidity: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoxelWorldConfig:
    """Global tuning parameters for the voxel world."""
    chunk_size_x: int = 16
    chunk_size_y: int = 16
    chunk_size_z: int = 16
    max_chunks: int = 4096
    max_structures: int = 1024
    world_seed: int = 1337
    gravity: float = 9.8
    fluid_flow_rate: float = 1.0
    light_propagation: bool = True
    enable_caves: bool = True
    enable_ores: bool = True
    enable_trees: bool = True
    enable_structures: bool = True
    render_distance: int = 8
    modification_history_limit: int = 1000
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoxelWorldStats:
    """Aggregate statistics for the voxel world."""
    total_chunks: int = 0
    total_blocks: int = 0
    total_structures: int = 0
    total_modifications: int = 0
    active_chunks: int = 0
    blocks_placed: int = 0
    blocks_removed: int = 0
    structures_built: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoxelWorldSnapshot:
    """Full state snapshot of the voxel world."""
    timestamp: float = field(default_factory=_now)
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    structures: List[Dict[str, Any]] = field(default_factory=list)
    biomes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoxelWorldEvent:
    """An audit event emitted by the voxel world system."""
    event_id: str
    kind: str
    timestamp: float
    chunk_id: str = ""
    block_id: str = ""
    player_id: str = ""
    structure_id: str = ""
    material_type: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Voxel World System
# ---------------------------------------------------------------------------

class VoxelWorldSystem:
    """Manages voxel materials, chunks, blocks, structures, and generation."""

    _instance: Optional["VoxelWorldSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._materials: Dict[str, VoxelMaterial] = {}
        self._biomes: Dict[str, BiomeConfig] = {}
        self._chunks: Dict[str, VoxelChunk] = {}
        self._blocks: Dict[str, VoxelBlock] = {}
        self._structures: Dict[str, VoxelStructure] = {}
        self._modifications: List[VoxelModification] = []
        self._modifications_by_id: Dict[str, VoxelModification] = {}
        self._events: List[VoxelWorldEvent] = []
        self._stats = VoxelWorldStats()
        self._config = VoxelWorldConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._block_counter: int = 0
        self._mod_counter: int = 0
        self._chunk_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "VoxelWorldSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            self._seed_materials()
            self._seed_biomes()
            self._seed_structures()
            self._seed_terrain_chunks()
            self._seed_modifications()

            self._update_stats()
            self._initialized = True

    def _seed_materials(self) -> None:
        # (id, name, type, color, hardness, transparency, light, solid, fluid, breakable, tool, drop)
        material_defs = [
            ("air", "Air", "air", "#000000", 0.0, 1.0, 0.0, False, False, False, "", ""),
            ("stone", "Stone", "stone", "#808080", 2.0, 0.0, 0.0, True, False, True, "pickaxe", "cobblestone"),
            ("dirt", "Dirt", "dirt", "#8B4513", 1.0, 0.0, 0.0, True, False, True, "shovel", "dirt"),
            ("grass", "Grass Block", "grass", "#4CAF50", 1.0, 0.0, 0.0, True, False, True, "shovel", "dirt"),
            ("wood", "Wood Log", "wood", "#6B4226", 2.0, 0.0, 0.0, True, False, True, "axe", "wood"),
            ("leaves", "Leaves", "leaves", "#3CB371", 0.5, 0.2, 0.0, True, False, True, "", "leaves"),
            ("water", "Water", "water", "#1E90FF", 100.0, 0.7, 0.0, False, True, False, "", ""),
            ("lava", "Lava", "lava", "#FF4500", 100.0, 0.3, 1.0, False, True, False, "", ""),
            ("sand", "Sand", "sand", "#F4E22A", 0.8, 0.0, 0.0, True, False, True, "shovel", "sand"),
            ("gravel", "Gravel", "gravel", "#8E8E8E", 0.9, 0.0, 0.0, True, False, True, "shovel", "gravel"),
            ("snow", "Snow", "snow", "#FFFAFA", 0.3, 0.0, 0.0, True, False, True, "shovel", "snow"),
            ("ice", "Ice", "ice", "#9ACDE3", 0.5, 0.4, 0.0, True, False, True, "pickaxe", "ice"),
            ("coal_ore", "Coal Ore", "coal_ore", "#3A3A3A", 3.0, 0.0, 0.0, True, False, True, "pickaxe", "coal"),
            ("iron_ore", "Iron Ore", "iron_ore", "#C9A77A", 3.5, 0.0, 0.0, True, False, True, "pickaxe", "iron_ingot"),
            ("gold_ore", "Gold Ore", "gold_ore", "#FDD663", 4.0, 0.0, 0.0, True, False, True, "pickaxe", "gold_ingot"),
            ("diamond_ore", "Diamond Ore", "diamond_ore", "#4FE0D8", 5.0, 0.0, 0.0, True, False, True, "pickaxe", "diamond"),
            ("crystal", "Crystal", "crystal", "#B388FF", 4.0, 0.3, 0.8, True, False, True, "pickaxe", "crystal"),
            ("metal", "Metal Block", "metal", "#B0B0B0", 5.0, 0.0, 0.0, True, False, True, "pickaxe", "metal_ingot"),
            ("glass", "Glass", "glass", "#C8E6F5", 0.5, 0.9, 0.0, True, False, True, "pickaxe", ""),
            ("brick", "Brick", "brick", "#A0522D", 2.5, 0.0, 0.0, True, False, True, "pickaxe", "brick"),
            ("plank", "Wood Plank", "plank", "#C19A6B", 1.5, 0.0, 0.0, True, False, True, "axe", "plank"),
            ("cobblestone", "Cobblestone", "cobblestone", "#6E6E6E", 2.5, 0.0, 0.0, True, False, True, "pickaxe", "cobblestone"),
            ("obsidian", "Obsidian", "obsidian", "#1B0F1B", 10.0, 0.0, 0.0, True, False, True, "pickaxe", "obsidian"),
            ("bedrock", "Bedrock", "bedrock", "#2F2F2F", 100.0, 0.0, 0.0, True, False, False, "", ""),
            ("cloud", "Cloud", "cloud", "#FFFFFF", 0.1, 0.5, 0.0, False, False, False, "", ""),
            ("slime", "Slime Block", "slime", "#7CFC00", 0.6, 0.3, 0.0, True, False, True, "", "slime"),
            ("magma", "Magma Block", "magma", "#FF6347", 3.0, 0.0, 0.6, True, False, True, "pickaxe", "magma"),
            ("soul_sand", "Soul Sand", "soul_sand", "#4A2F23", 1.0, 0.0, 0.0, True, False, True, "shovel", "soul_sand"),
            ("netherrack", "Netherrack", "netherrack", "#6E2A2A", 1.5, 0.0, 0.0, True, False, True, "pickaxe", "netherrack"),
            ("end_stone", "End Stone", "end_stone", "#DCD9A0", 3.5, 0.0, 0.0, True, False, True, "pickaxe", "end_stone"),
        ]
        for (mid, name, mtype, color, hardness, trans, light,
             solid, fluid, breakable, tool, drop) in material_defs:
            self._materials[mid] = VoxelMaterial(
                material_id=mid, name=name, material_type=mtype, color=color,
                hardness=hardness, transparency=trans, light_emission=light,
                is_solid=solid, is_fluid=fluid, is_breakable=breakable,
                tool_required=tool, drop_item_id=drop,
            )

    def _seed_biomes(self) -> None:
        biome_defs = [
            ("biome_plains", BiomeType.PLAINS.value, 2, 6, "grass", "dirt", "stone",
             0.04, 0.02, 0.03, 0.6, 0.5),
            ("biome_forest", BiomeType.FOREST.value, 3, 8, "grass", "dirt", "stone",
             0.05, 0.25, 0.02, 0.6, 0.7),
            ("biome_desert", BiomeType.DESERT.value, 1, 4, "sand", "sand", "stone",
             0.02, 0.0, 0.01, 0.9, 0.1),
            ("biome_mountains", BiomeType.MOUNTAINS.value, 5, 15, "stone", "stone", "stone",
             0.08, 0.05, 0.02, 0.3, 0.4),
            ("biome_ocean", BiomeType.OCEAN.value, 0, 3, "sand", "sand", "stone",
             0.03, 0.0, 0.01, 0.5, 1.0),
            ("biome_tundra", BiomeType.TUNDRA.value, 2, 7, "snow", "dirt", "stone",
             0.04, 0.05, 0.01, 0.1, 0.3),
        ]
        for (bid, btype, hmin, hmax, surf, under, deep,
             ore, tree, struct, temp, hum) in biome_defs:
            self._biomes[bid] = BiomeConfig(
                biome_id=bid, biome_type=btype,
                terrain_height_min=hmin, terrain_height_max=hmax,
                material_surface=surf, material_underground=under, material_deep=deep,
                ore_chance=ore, tree_chance=tree, structure_chance=struct,
                temperature=temp, humidity=hum,
            )

    def _seed_structures(self) -> None:
        # Small house: plank floor, wood walls, plank roof, door gap.
        house_blocks: List[Dict[str, Any]] = []
        for fx in range(0, 5):
            for fz in range(0, 5):
                house_blocks.append({"x": fx, "y": 0, "z": fz, "material_type": "plank"})
        for wx in range(0, 5):
            for wz in range(0, 5):
                if wx in (0, 4) or wz in (0, 4):
                    if wx == 2 and wz == 0:
                        continue  # leave a door gap
                    house_blocks.append({"x": wx, "y": 1, "z": wz, "material_type": "wood"})
                    house_blocks.append({"x": wx, "y": 2, "z": wz, "material_type": "wood"})
        for rx in range(0, 5):
            for rz in range(0, 5):
                house_blocks.append({"x": rx, "y": 3, "z": rz, "material_type": "plank"})
        self._structures["struct_small_house"] = VoxelStructure(
            structure_id="struct_small_house", name="Small House",
            structure_type=StructureType.HOUSE.value,
            blocks=house_blocks, size_x=5, size_y=4, size_z=5,
            metadata={"rooms": 1, "has_door": True},
        )

        # Oak tree: wood trunk plus a leaves canopy.
        tree_blocks: List[Dict[str, Any]] = []
        for ty in range(0, 4):
            tree_blocks.append({"x": 2, "y": ty, "z": 2, "material_type": "wood"})
        for ly in range(3, 6):
            for lx in range(1, 4):
                for lz in range(1, 4):
                    if lx == 2 and lz == 2 and ly < 5:
                        continue
                    tree_blocks.append({"x": lx, "y": ly, "z": lz, "material_type": "leaves"})
        self._structures["struct_oak_tree"] = VoxelStructure(
            structure_id="struct_oak_tree", name="Oak Tree",
            structure_type=StructureType.TREE.value,
            blocks=tree_blocks, size_x=5, size_y=6, size_z=5,
            metadata={"tree_kind": "oak"},
        )

        # Cave entrance: a cobblestone archway into the ground.
        cave_blocks: List[Dict[str, Any]] = []
        for cy in range(0, 4):
            cave_blocks.append({"x": 0, "y": cy, "z": 0, "material_type": "cobblestone"})
            cave_blocks.append({"x": 2, "y": cy, "z": 0, "material_type": "cobblestone"})
        cave_blocks.append({"x": 0, "y": 4, "z": 0, "material_type": "cobblestone"})
        cave_blocks.append({"x": 1, "y": 4, "z": 0, "material_type": "cobblestone"})
        cave_blocks.append({"x": 2, "y": 4, "z": 0, "material_type": "cobblestone"})
        for cy in range(1, 4):
            cave_blocks.append({"x": 1, "y": cy, "z": 0, "material_type": "air"})
        self._structures["struct_cave_entrance"] = VoxelStructure(
            structure_id="struct_cave_entrance", name="Cave Entrance",
            structure_type=StructureType.CAVE.value,
            blocks=cave_blocks, size_x=3, size_y=5, size_z=1,
            metadata={"depth": 4},
        )

        # Stone tower: hollow cobblestone walls several layers tall.
        tower_blocks: List[Dict[str, Any]] = []
        for ty in range(0, 6):
            for tx in range(0, 3):
                for tz in range(0, 3):
                    if tx in (0, 2) or tz in (0, 2):
                        tower_blocks.append({"x": tx, "y": ty, "z": tz, "material_type": "cobblestone"})
        tower_blocks.append({"x": 1, "y": 6, "z": 1, "material_type": "wood"})
        self._structures["struct_stone_tower"] = VoxelStructure(
            structure_id="struct_stone_tower", name="Stone Tower",
            structure_type=StructureType.TOWER.value,
            blocks=tower_blocks, size_x=3, size_y=7, size_z=3,
            metadata={"height": 7},
        )

        # Campfire: cobblestone ring with wood and a light source.
        camp_blocks: List[Dict[str, Any]] = [
            {"x": 0, "y": 0, "z": 0, "material_type": "cobblestone"},
            {"x": 2, "y": 0, "z": 0, "material_type": "cobblestone"},
            {"x": 0, "y": 0, "z": 2, "material_type": "cobblestone"},
            {"x": 2, "y": 0, "z": 2, "material_type": "cobblestone"},
            {"x": 1, "y": 0, "z": 1, "material_type": "wood"},
            {"x": 1, "y": 1, "z": 1, "material_type": "magma"},
        ]
        self._structures["struct_campfire"] = VoxelStructure(
            structure_id="struct_campfire", name="Campfire",
            structure_type=StructureType.CAMP.value,
            blocks=camp_blocks, size_x=3, size_y=2, size_z=3,
            metadata={"light_radius": 6},
        )

        # Wooden bridge: planks laid across a gap.
        bridge_blocks: List[Dict[str, Any]] = [
            {"x": bx, "y": 0, "z": 0, "material_type": "plank"} for bx in range(0, 6)
        ]
        bridge_blocks.append({"x": 0, "y": -1, "z": 0, "material_type": "wood"})
        bridge_blocks.append({"x": 5, "y": -1, "z": 0, "material_type": "wood"})
        self._structures["struct_wooden_bridge"] = VoxelStructure(
            structure_id="struct_wooden_bridge", name="Wooden Bridge",
            structure_type=StructureType.BRIDGE.value,
            blocks=bridge_blocks, size_x=6, size_y=2, size_z=1,
            metadata={"length": 6},
        )

    def _seed_terrain_chunks(self) -> None:
        # Three pre-generated chunks, one per biome type.
        self._generate_chunk_internal(0, 0, 0, "plains")
        self._generate_chunk_internal(1, 0, 0, "desert")
        self._generate_chunk_internal(0, 0, 1, "forest")

    def _seed_modifications(self) -> None:
        # A few historical modification records across the seeded chunks.
        mod_defs = [
            ("mod_000001", ModificationType.PLACE.value, 3, 5, 2, "air", "glass", "player_builder"),
            ("mod_000002", ModificationType.PLACE.value, 8, 6, 4, "air", "wood", "player_builder"),
            ("mod_000003", ModificationType.REMOVE.value, 20, 4, 5, "sand", "air", "player_miner"),
            ("mod_000004", ModificationType.REPLACE.value, 5, 7, 3, "grass", "plank", "player_builder"),
            ("mod_000005", ModificationType.FILL.value, 10, 4, 10, "air", "cobblestone", "player_builder"),
            ("mod_000006", ModificationType.PLACE.value, 12, 8, 2, "air", "crystal", "player_wizard"),
        ]
        ts = _now() - 600
        for mid, mtype, x, y, z, old_m, new_m, pid in mod_defs:
            mod = VoxelModification(
                modification_id=mid, modification_type=mtype,
                x=x, y=y, z=z, old_material=old_m, new_material=new_m,
                player_id=pid, timestamp=ts,
            )
            ts += 60
            self._modifications.append(mod)
            self._modifications_by_id[mid] = mod
        _evict_fifo_list(self._modifications, self._config.modification_history_limit)

    def _log_event(self, kind: str, details: Dict[str, Any],
                   chunk_id: str = "", block_id: str = "",
                   player_id: str = "", structure_id: str = "",
                   material_type: str = "",
                   description: str = "") -> None:
        self._event_counter += 1
        event = VoxelWorldEvent(
            event_id=f"vwevt_{self._event_counter:06d}",
            kind=kind, timestamp=_now(),
            chunk_id=chunk_id, block_id=block_id,
            player_id=player_id, structure_id=structure_id,
            material_type=material_type,
            description=description, details=details,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_stats(self) -> None:
        self._stats.total_chunks = len(self._chunks)
        self._stats.total_blocks = len(self._blocks)
        self._stats.total_structures = len(self._structures)
        self._stats.total_modifications = len(self._modifications)
        self._stats.active_chunks = sum(
            1 for c in self._chunks.values()
            if c.state in (ChunkState.READY.value, ChunkState.DIRTY.value)
        )
        self._stats.tick_count = self._tick_count

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _hash_noise(self, *coords: int) -> int:
        # Deterministic pseudo-random value derived from coordinates and seed.
        h = self._config.world_seed
        for c in coords:
            h = (h * 31 + int(c)) & 0xFFFFFFFF
        return h

    def _chunk_coords(self, x: int, y: int, z: int) -> Tuple[int, int, int]:
        cx = x // self._config.chunk_size_x
        cy = y // self._config.chunk_size_y
        cz = z // self._config.chunk_size_z
        return cx, cy, cz

    def _next_block_id(self) -> str:
        self._block_counter += 1
        return f"blk_{self._block_counter:08d}"

    def _next_mod_id(self) -> str:
        self._mod_counter += 1
        return f"mod_{self._mod_counter:08d}"

    def _next_chunk_id(self) -> str:
        self._chunk_counter += 1
        return f"chk_{self._chunk_counter:06d}"

    def _material_hardness(self, material_type: str) -> float:
        mat = self._materials.get(material_type)
        if mat is not None:
            return mat.hardness
        return 1.0

    def _place_block_internal(self, x: int, y: int, z: int,
                              material_type: str,
                              player_id: str = "",
                              mod_type: str = ModificationType.PLACE.value,
                              old_material: str = "",
                              record_mod: bool = True) -> Optional[VoxelBlock]:
        cx, cy, cz = self._chunk_coords(x, y, z)
        ck = _chunk_key(cx, cy, cz)
        chunk = self._chunks.get(ck)
        if chunk is None:
            return None
        bk = _block_key(x, y, z)
        existing = self._blocks.get(bk)
        prev_material = existing.material_type if existing else "air"

        if material_type == VoxelMaterialType.AIR.value:
            # Treat as removal.
            if existing is not None:
                chunk.blocks.pop(bk, None)
                chunk.modified_blocks[bk] = {"from": prev_material, "to": "air"}
                self._blocks.pop(bk, None)
                chunk.state = ChunkState.DIRTY.value
                if record_mod:
                    self._record_modification(
                        ModificationType.REMOVE.value, x, y, z,
                        prev_material, "air", player_id,
                    )
            return None

        hardness = self._material_hardness(material_type)
        block_id = existing.block_id if existing else self._next_block_id()
        block = VoxelBlock(
            block_id=block_id, chunk_id=ck,
            x=x, y=y, z=z, material_type=material_type,
            health=hardness, max_health=hardness,
            is_exposed=False, light_level=0.0,
        )
        chunk.blocks[bk] = block
        self._blocks[bk] = block
        chunk.modified_blocks[bk] = {"from": prev_material, "to": material_type}
        chunk.state = ChunkState.DIRTY.value

        if record_mod:
            actual_old = old_material or prev_material
            self._record_modification(mod_type, x, y, z, actual_old, material_type, player_id)
        return block

    def _record_modification(self, mod_type: str, x: int, y: int, z: int,
                             old_material: str, new_material: str,
                             player_id: str) -> VoxelModification:
        mod = VoxelModification(
            modification_id=self._next_mod_id(),
            modification_type=mod_type, x=x, y=y, z=z,
            old_material=old_material, new_material=new_material,
            player_id=player_id, timestamp=_now(),
        )
        self._modifications.append(mod)
        self._modifications_by_id[mod.modification_id] = mod
        _evict_fifo_list(self._modifications, self._config.modification_history_limit)
        if len(self._modifications_by_id) > self._config.modification_history_limit:
            stale = self._modifications_by_id
            keep = {m.modification_id for m in self._modifications}
            for k in list(stale.keys()):
                if k not in keep:
                    stale.pop(k, None)
        if new_material != VoxelMaterialType.AIR.value:
            self._stats.blocks_placed += 1
        else:
            self._stats.blocks_removed += 1
        return mod

    def _terrain_height(self, wx: int, wz: int, biome_cfg: BiomeConfig) -> int:
        base = (biome_cfg.terrain_height_min + biome_cfg.terrain_height_max) / 2.0
        span = max(1, biome_cfg.terrain_height_max - biome_cfg.terrain_height_min)
        amp = min(span / 2.0, (self._config.chunk_size_y - 1) / 2.0)
        wave = (math.sin(wx * 0.4 + self._config.world_seed * 0.13)
                + math.cos(wz * 0.4 + self._config.world_seed * 0.07)) / 2.0
        h = int(round(base + wave * amp))
        return max(0, min(self._config.chunk_size_y - 1, h))

    def _pick_ore(self, wx: int, wy: int, wz: int) -> str:
        r = self._hash_noise(wx, wy, wz, 7) % 1000
        if r < 400:
            return "coal_ore"
        if r < 700:
            return "iron_ore"
        if r < 880:
            return "gold_ore"
        return "diamond_ore"

    def _generate_chunk_internal(self, chunk_x: int, chunk_y: int, chunk_z: int,
                                 biome_type: str) -> Optional[VoxelChunk]:
        ck = _chunk_key(chunk_x, chunk_y, chunk_z)
        biome_cfg = None
        for b in self._biomes.values():
            if b.biome_type == biome_type:
                biome_cfg = b
                break
        if biome_cfg is None:
            biome_cfg = BiomeConfig(biome_id=f"biome_{biome_type}", biome_type=biome_type)

        chunk = self._chunks.get(ck)
        if chunk is None:
            chunk = VoxelChunk(
                chunk_id=self._next_chunk_id(),
                chunk_x=chunk_x, chunk_y=chunk_y, chunk_z=chunk_z,
                state=ChunkState.GENERATING.value,
                biome_type=biome_type,
            )
            self._chunks[ck] = chunk
        else:
            chunk.state = ChunkState.GENERATING.value
            chunk.biome_type = biome_type

        csx = self._config.chunk_size_x
        csy = self._config.chunk_size_y
        csz = self._config.chunk_size_z
        base_x = chunk_x * csx
        base_z = chunk_z * csz

        for lx in range(csx):
            for lz in range(csz):
                wx = base_x + lx
                wz = base_z + lz
                height = self._terrain_height(wx, wz, biome_cfg)
                for ly in range(0, height + 1):
                    wy = ly
                    if ly == height:
                        material = biome_cfg.material_surface
                        # Snow caps on tall mountain terrain.
                        if biome_cfg.biome_type == BiomeType.MOUNTAINS.value and height >= 12:
                            material = "snow"
                    elif ly >= height - 2:
                        material = biome_cfg.material_underground
                    else:
                        material = biome_cfg.material_deep
                    # Ore insertion in deep stone.
                    if (self._config.enable_ores and material == "stone"
                            and ly < height - 2):
                        if (self._hash_noise(wx, wy, wz, 3) % 1000) / 1000.0 < biome_cfg.ore_chance:
                            material = self._pick_ore(wx, wy, wz)
                    self._place_block_internal(
                        wx, wy, wz, material, record_mod=False,
                    )
                # Bedrock floor at the very bottom.
                self._place_block_internal(
                    wx, 0, wz, "bedrock", record_mod=False,
                )
                # Water fills above low ocean terrain.
                if biome_cfg.biome_type == BiomeType.OCEAN.value:
                    for wy in range(height + 1, min(csy, height + 4)):
                        self._place_block_internal(wx, wy, wz, "water", record_mod=False)
                # Trees in forested biomes.
                if (self._config.enable_trees
                        and biome_cfg.tree_chance > 0
                        and biome_cfg.biome_type in (
                            BiomeType.FOREST.value, BiomeType.PLAINS.value,
                            BiomeType.JUNGLE.value, BiomeType.SWAMP.value)):
                    if (self._hash_noise(wx, wz, 11) % 1000) / 1000.0 < biome_cfg.tree_chance:
                        self._spawn_tree(wx, height + 1, wz)

        chunk.is_generated = True
        chunk.state = ChunkState.READY.value
        return chunk

    def _spawn_tree(self, x: int, base_y: int, z: int) -> None:
        trunk = 3 + (self._hash_noise(x, z, 23) % 3)
        for ty in range(base_y, base_y + trunk):
            if ty < self._config.chunk_size_y:
                self._place_block_internal(x, ty, z, "wood", record_mod=False)
        top = base_y + trunk
        for ly in range(top - 1, top + 2):
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if dx == 0 and dz == 0 and ly < top:
                        continue
                    if abs(dx) == 2 and abs(dz) == 2:
                        continue
                    tx = x + dx
                    tz = z + dz
                    ty = ly
                    if 0 <= ty < self._config.chunk_size_y:
                        if self._blocks.get(_block_key(tx, ty, tz)) is None:
                            self._place_block_internal(tx, ty, tz, "leaves", record_mod=False)

    # ------------------------------------------------------------------
    # Material Management
    # ------------------------------------------------------------------

    def register_material(self, material_id: str, name: str,
                          material_type: str,
                          color: str = "#888888",
                          hardness: float = 1.0,
                          transparency: float = 0.0,
                          light_emission: float = 0.0,
                          is_solid: bool = True,
                          is_fluid: bool = False,
                          is_breakable: bool = True,
                          tool_required: str = "",
                          drop_item_id: str = "",
                          metadata: Optional[Dict[str, Any]] = None
                          ) -> Tuple[bool, str, Optional[VoxelMaterial]]:
        with _LOCK:
            if material_id in self._materials:
                return False, "already_exists", self._materials[material_id]
            if len(self._materials) >= _MAX_MATERIALS:
                return False, "capacity_reached", None
            mat = VoxelMaterial(
                material_id=material_id, name=name, material_type=material_type,
                color=color, hardness=hardness, transparency=transparency,
                light_emission=light_emission, is_solid=is_solid,
                is_fluid=is_fluid, is_breakable=is_breakable,
                tool_required=tool_required, drop_item_id=drop_item_id,
                metadata=dict(metadata) if metadata else {},
            )
            self._materials[material_id] = mat
            self._log_event(VoxelWorldEventKind.MATERIAL_REGISTERED.value,
                            {"name": name, "material_type": material_type},
                            material_type=material_type, description=material_id)
            self._update_stats()
            return True, "registered", mat

    def get_material(self, material_id: str) -> Optional[VoxelMaterial]:
        with _LOCK:
            return self._materials.get(material_id)

    def list_materials(self, material_type: str = "") -> List[VoxelMaterial]:
        with _LOCK:
            results = list(self._materials.values())
            if material_type:
                results = [m for m in results if m.material_type == material_type]
            return results

    def remove_material(self, material_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if material_id not in self._materials:
                return False, "not_found"
            del self._materials[material_id]
            self._log_event(VoxelWorldEventKind.MATERIAL_REMOVED.value,
                            {}, material_type=material_id, description=material_id)
            self._update_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Biome Management
    # ------------------------------------------------------------------

    def register_biome(self, biome_id: str, biome_type: str,
                       terrain_height_min: int = 0,
                       terrain_height_max: int = 64,
                       material_surface: str = "grass",
                       material_underground: str = "dirt",
                       material_deep: str = "stone",
                       ore_chance: float = 0.05,
                       tree_chance: float = 0.1,
                       structure_chance: float = 0.02,
                       temperature: float = 0.5,
                       humidity: float = 0.5,
                       metadata: Optional[Dict[str, Any]] = None
                       ) -> Tuple[bool, str, Optional[BiomeConfig]]:
        with _LOCK:
            if biome_id in self._biomes:
                return False, "already_exists", self._biomes[biome_id]
            if len(self._biomes) >= _MAX_BIOMES:
                return False, "capacity_reached", None
            biome = BiomeConfig(
                biome_id=biome_id, biome_type=biome_type,
                terrain_height_min=terrain_height_min,
                terrain_height_max=terrain_height_max,
                material_surface=material_surface,
                material_underground=material_underground,
                material_deep=material_deep,
                ore_chance=_clamp(ore_chance, 0.0, 1.0),
                tree_chance=_clamp(tree_chance, 0.0, 1.0),
                structure_chance=_clamp(structure_chance, 0.0, 1.0),
                temperature=_clamp(temperature, 0.0, 1.0),
                humidity=_clamp(humidity, 0.0, 1.0),
                metadata=dict(metadata) if metadata else {},
            )
            self._biomes[biome_id] = biome
            self._log_event(VoxelWorldEventKind.BIOME_REGISTERED.value,
                            {"biome_type": biome_type}, description=biome_id)
            self._update_stats()
            return True, "registered", biome

    def get_biome(self, biome_id: str) -> Optional[BiomeConfig]:
        with _LOCK:
            return self._biomes.get(biome_id)

    def list_biomes(self, biome_type: str = "") -> List[BiomeConfig]:
        with _LOCK:
            results = list(self._biomes.values())
            if biome_type:
                results = [b for b in results if b.biome_type == biome_type]
            return results

    def remove_biome(self, biome_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if biome_id not in self._biomes:
                return False, "not_found"
            del self._biomes[biome_id]
            self._log_event(VoxelWorldEventKind.BIOME_REMOVED.value,
                            {}, description=biome_id)
            self._update_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Chunk Management
    # ------------------------------------------------------------------

    def get_chunk(self, chunk_x: int, chunk_y: int, chunk_z: int) -> Optional[VoxelChunk]:
        with _LOCK:
            return self._chunks.get(_chunk_key(chunk_x, chunk_y, chunk_z))

    def list_chunks(self, state: str = "") -> List[VoxelChunk]:
        with _LOCK:
            results = list(self._chunks.values())
            if state:
                results = [c for c in results if c.state == state]
            return results

    def generate_chunk(self, chunk_x: int, chunk_y: int, chunk_z: int,
                       biome_type: str = "plains"
                       ) -> Tuple[bool, str, Optional[VoxelChunk]]:
        with _LOCK:
            ck = _chunk_key(chunk_x, chunk_y, chunk_z)
            if ck in self._chunks and self._chunks[ck].is_generated:
                return False, "already_exists", self._chunks[ck]
            if len(self._chunks) >= self._config.max_chunks:
                return False, "capacity_reached", None
            chunk = self._generate_chunk_internal(chunk_x, chunk_y, chunk_z, biome_type)
            if chunk is None:
                return False, "generation_failed", None
            self._log_event(VoxelWorldEventKind.CHUNK_GENERATED.value,
                            {"biome_type": biome_type,
                             "chunk_x": chunk_x, "chunk_y": chunk_y, "chunk_z": chunk_z},
                            chunk_id=chunk.chunk_id, description=ck)
            self._update_stats()
            return True, "generated", chunk

    def unload_chunk(self, chunk_x: int, chunk_y: int, chunk_z: int) -> Tuple[bool, str]:
        with _LOCK:
            ck = _chunk_key(chunk_x, chunk_y, chunk_z)
            chunk = self._chunks.get(ck)
            if chunk is None:
                return False, "not_found"
            # Drop block index entries that belonged to this chunk.
            stale_keys = [bk for bk, b in self._blocks.items() if b.chunk_id == ck]
            for bk in stale_keys:
                self._blocks.pop(bk, None)
            self._chunks.pop(ck, None)
            self._log_event(VoxelWorldEventKind.CHUNK_UNLOADED.value,
                            {"chunk_x": chunk_x, "chunk_y": chunk_y, "chunk_z": chunk_z},
                            chunk_id=chunk.chunk_id, description=ck)
            self._update_stats()
            return True, "unloaded"

    # ------------------------------------------------------------------
    # Block Management
    # ------------------------------------------------------------------

    def get_block(self, x: int, y: int, z: int) -> Optional[VoxelBlock]:
        with _LOCK:
            return self._blocks.get(_block_key(x, y, z))

    def set_block(self, x: int, y: int, z: int, material_type: str,
                  player_id: str = "",
                  metadata: Optional[Dict[str, Any]] = None
                  ) -> Tuple[bool, str, Optional[VoxelBlock]]:
        with _LOCK:
            cx, cy, cz = self._chunk_coords(x, y, z)
            ck = _chunk_key(cx, cy, cz)
            chunk = self._chunks.get(ck)
            if chunk is None:
                # Lazily generate an empty chunk to hold the block.
                if len(self._chunks) >= self._config.max_chunks:
                    return False, "capacity_reached", None
                chunk = VoxelChunk(
                    chunk_id=self._next_chunk_id(),
                    chunk_x=cx, chunk_y=cy, chunk_z=cz,
                    state=ChunkState.READY.value, is_generated=False,
                )
                self._chunks[ck] = chunk
            existing = self._blocks.get(_block_key(x, y, z))
            old_material = existing.material_type if existing else "air"
            mod_type = (ModificationType.REPLACE.value
                        if old_material != "air"
                        else ModificationType.PLACE.value)
            block = self._place_block_internal(
                x, y, z, material_type, player_id=player_id,
                mod_type=mod_type, old_material=old_material,
            )
            if block is not None and metadata:
                block.metadata.update(metadata)
            self._log_event(VoxelWorldEventKind.BLOCK_SET.value,
                            {"material_type": material_type,
                             "old_material": old_material},
                            chunk_id=ck, block_id=block.block_id if block else "",
                            player_id=player_id, material_type=material_type,
                            description=_block_key(x, y, z))
            self._update_stats()
            if material_type == VoxelMaterialType.AIR.value:
                return True, "removed", None
            return True, "placed", block

    def remove_block(self, x: int, y: int, z: int,
                     player_id: str = "") -> Tuple[bool, str]:
        with _LOCK:
            bk = _block_key(x, y, z)
            existing = self._blocks.get(bk)
            if existing is None:
                return False, "not_found"
            old_material = existing.material_type
            chunk = self._chunks.get(existing.chunk_id)
            if chunk is not None:
                chunk.blocks.pop(bk, None)
                chunk.modified_blocks[bk] = {"from": old_material, "to": "air"}
                chunk.state = ChunkState.DIRTY.value
            self._blocks.pop(bk, None)
            self._record_modification(
                ModificationType.REMOVE.value, x, y, z, old_material, "air", player_id,
            )
            self._log_event(VoxelWorldEventKind.BLOCK_REMOVED.value,
                            {"old_material": old_material},
                            chunk_id=existing.chunk_id, block_id=existing.block_id,
                            player_id=player_id, description=bk)
            self._update_stats()
            return True, "removed"

    def fill_area(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                  material_type: str, player_id: str = ""
                  ) -> Tuple[bool, str, int]:
        with _LOCK:
            if material_type not in self._materials and material_type != VoxelMaterialType.AIR.value:
                return False, "unknown_material", 0
            lx, hx = sorted((x1, x2))
            ly, hy = sorted((y1, y2))
            lz, hz = sorted((z1, z2))
            count = 0
            for x in range(lx, hx + 1):
                for y in range(ly, hy + 1):
                    for z in range(lz, hz + 1):
                        cx, cy, cz = self._chunk_coords(x, y, z)
                        ck = _chunk_key(cx, cy, cz)
                        chunk = self._chunks.get(ck)
                        if chunk is None:
                            if len(self._chunks) >= self._config.max_chunks:
                                continue
                            chunk = VoxelChunk(
                                chunk_id=self._next_chunk_id(),
                                chunk_x=cx, chunk_y=cy, chunk_z=cz,
                                state=ChunkState.READY.value, is_generated=False,
                            )
                            self._chunks[ck] = chunk
                        existing = self._blocks.get(_block_key(x, y, z))
                        old_material = existing.material_type if existing else "air"
                        block = self._place_block_internal(
                            x, y, z, material_type, player_id=player_id,
                            mod_type=ModificationType.FILL.value,
                            old_material=old_material,
                        )
                        if block is not None:
                            count += 1
            self._log_event(VoxelWorldEventKind.AREA_FILLED.value,
                            {"material_type": material_type, "count": count,
                             "from": [lx, ly, lz], "to": [hx, hy, hz]},
                            player_id=player_id, material_type=material_type)
            self._update_stats()
            return True, "filled", count

    def clear_area(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                   player_id: str = "") -> Tuple[bool, str, int]:
        with _LOCK:
            lx, hx = sorted((x1, x2))
            ly, hy = sorted((y1, y2))
            lz, hz = sorted((z1, z2))
            count = 0
            keys_to_clear: List[str] = []
            for bk, block in self._blocks.items():
                if lx <= block.x <= hx and ly <= block.y <= hy and lz <= block.z <= hz:
                    if block.material_type == VoxelMaterialType.AIR.value:
                        continue
                    keys_to_clear.append(bk)
            for bk in keys_to_clear:
                block = self._blocks.get(bk)
                if block is None:
                    continue
                old_material = block.material_type
                chunk = self._chunks.get(block.chunk_id)
                if chunk is not None:
                    chunk.blocks.pop(bk, None)
                    chunk.modified_blocks[bk] = {"from": old_material, "to": "air"}
                    chunk.state = ChunkState.DIRTY.value
                self._blocks.pop(bk, None)
                self._record_modification(
                    ModificationType.CLEAR.value, block.x, block.y, block.z,
                    old_material, "air", player_id,
                )
                count += 1
            self._log_event(VoxelWorldEventKind.AREA_CLEARED.value,
                            {"count": count,
                             "from": [lx, ly, lz], "to": [hx, hy, hz]},
                            player_id=player_id)
            self._update_stats()
            return True, "cleared", count

    # ------------------------------------------------------------------
    # Structure Management
    # ------------------------------------------------------------------

    def register_structure(self, structure_id: str, name: str,
                           structure_type: str,
                           blocks: Optional[List[Dict[str, Any]]] = None,
                           size_x: int = 1, size_y: int = 1, size_z: int = 1,
                           origin_x: int = 0, origin_y: int = 0, origin_z: int = 0,
                           biome_restriction: str = "",
                           metadata: Optional[Dict[str, Any]] = None
                           ) -> Tuple[bool, str, Optional[VoxelStructure]]:
        with _LOCK:
            if structure_id in self._structures:
                return False, "already_exists", self._structures[structure_id]
            if len(self._structures) >= _MAX_STRUCTURES:
                return False, "capacity_reached", None
            struct = VoxelStructure(
                structure_id=structure_id, name=name, structure_type=structure_type,
                blocks=list(blocks) if blocks else [],
                size_x=size_x, size_y=size_y, size_z=size_z,
                origin_x=origin_x, origin_y=origin_y, origin_z=origin_z,
                biome_restriction=biome_restriction,
                metadata=dict(metadata) if metadata else {},
            )
            self._structures[structure_id] = struct
            self._log_event(VoxelWorldEventKind.STRUCTURE_REGISTERED.value,
                            {"name": name, "structure_type": structure_type,
                             "block_count": len(struct.blocks)},
                            structure_id=structure_id, description=structure_id)
            self._update_stats()
            return True, "registered", struct

    def get_structure(self, structure_id: str) -> Optional[VoxelStructure]:
        with _LOCK:
            return self._structures.get(structure_id)

    def list_structures(self, structure_type: str = "") -> List[VoxelStructure]:
        with _LOCK:
            results = list(self._structures.values())
            if structure_type:
                results = [s for s in results if s.structure_type == structure_type]
            return results

    def place_structure(self, structure_id: str, origin_x: int, origin_y: int,
                        origin_z: int, player_id: str = ""
                        ) -> Tuple[bool, str, int]:
        with _LOCK:
            struct = self._structures.get(structure_id)
            if struct is None:
                return False, "not_found", 0
            placed = 0
            for tb in struct.blocks:
                wx = origin_x + int(tb.get("x", 0))
                wy = origin_y + int(tb.get("y", 0))
                wz = origin_z + int(tb.get("z", 0))
                material = tb.get("material_type", "air")
                if material == VoxelMaterialType.AIR.value:
                    existing = self._blocks.get(_block_key(wx, wy, wz))
                    if existing is not None:
                        chunk = self._chunks.get(existing.chunk_id)
                        if chunk is not None:
                            chunk.blocks.pop(_block_key(wx, wy, wz), None)
                            chunk.state = ChunkState.DIRTY.value
                        self._blocks.pop(_block_key(wx, wy, wz), None)
                        self._record_modification(
                            ModificationType.REMOVE.value, wx, wy, wz,
                            existing.material_type, "air", player_id,
                        )
                    continue
                cx, cy, cz = self._chunk_coords(wx, wy, wz)
                ck = _chunk_key(cx, cy, cz)
                chunk = self._chunks.get(ck)
                if chunk is None:
                    if len(self._chunks) >= self._config.max_chunks:
                        continue
                    chunk = VoxelChunk(
                        chunk_id=self._next_chunk_id(),
                        chunk_x=cx, chunk_y=cy, chunk_z=cz,
                        state=ChunkState.READY.value, is_generated=False,
                    )
                    self._chunks[ck] = chunk
                existing = self._blocks.get(_block_key(wx, wy, wz))
                old_material = existing.material_type if existing else "air"
                block = self._place_block_internal(
                    wx, wy, wz, material, player_id=player_id,
                    mod_type=ModificationType.PLACE.value,
                    old_material=old_material,
                )
                if block is not None:
                    placed += 1
            self._stats.structures_built += 1
            self._log_event(VoxelWorldEventKind.STRUCTURE_PLACED.value,
                            {"structure_id": structure_id, "placed": placed,
                             "origin": [origin_x, origin_y, origin_z]},
                            structure_id=structure_id, player_id=player_id)
            self._update_stats()
            return True, "placed", placed

    def remove_structure(self, structure_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if structure_id not in self._structures:
                return False, "not_found"
            del self._structures[structure_id]
            self._log_event(VoxelWorldEventKind.STRUCTURE_REMOVED.value,
                            {}, structure_id=structure_id, description=structure_id)
            self._update_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Modification Management
    # ------------------------------------------------------------------

    def get_modifications(self, limit: int = 100,
                          player_id: str = "") -> List[VoxelModification]:
        with _LOCK:
            results = list(self._modifications)
            if player_id:
                results = [m for m in results if m.player_id == player_id]
            if limit > 0:
                results = results[-limit:]
            return results

    def undo_modification(self, modification_id: str) -> Tuple[bool, str]:
        with _LOCK:
            mod = self._modifications_by_id.get(modification_id)
            if mod is None:
                return False, "not_found"
            if mod.is_undone:
                return False, "already_undone"
            target_material = mod.old_material
            if target_material == VoxelMaterialType.AIR.value:
                # Revert a place/fill by removing the block.
                existing = self._blocks.get(_block_key(mod.x, mod.y, mod.z))
                if existing is not None:
                    chunk = self._chunks.get(existing.chunk_id)
                    if chunk is not None:
                        chunk.blocks.pop(_block_key(mod.x, mod.y, mod.z), None)
                        chunk.state = ChunkState.DIRTY.value
                    self._blocks.pop(_block_key(mod.x, mod.y, mod.z), None)
            else:
                self._place_block_internal(
                    mod.x, mod.y, mod.z, target_material,
                    player_id=mod.player_id, record_mod=False,
                )
            mod.is_undone = True
            self._log_event(VoxelWorldEventKind.MODIFICATION_UNDONE.value,
                            {"modification_id": modification_id,
                             "reverted_to": target_material},
                            player_id=mod.player_id)
            self._update_stats()
            return True, "undone"

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_blocks_in_range(self, x1: int, y1: int, z1: int,
                            x2: int, y2: int, z2: int) -> List[VoxelBlock]:
        with _LOCK:
            lx, hx = sorted((x1, x2))
            ly, hy = sorted((y1, y2))
            lz, hz = sorted((z1, z2))
            results: List[VoxelBlock] = []
            for block in self._blocks.values():
                if (lx <= block.x <= hx and ly <= block.y <= hy
                        and lz <= block.z <= hz):
                    results.append(block)
            results.sort(key=lambda b: (b.y, b.x, b.z))
            return results

    def count_blocks_by_material(self, material_type: str = "") -> Dict[str, int]:
        with _LOCK:
            counts: Dict[str, int] = {}
            for block in self._blocks.values():
                mt = block.material_type
                counts[mt] = counts.get(mt, 0) + 1
            if material_type:
                return {material_type: counts.get(material_type, 0)}
            return counts

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def _tick_fluids(self) -> int:
        # Move fluid blocks downward into air when possible, bounded per tick.
        if not self._config.enable_caves and self._config.fluid_flow_rate <= 0:
            return 0
        moved = 0
        fluid_blocks = [
            b for b in self._blocks.values()
            if b.material_type in (VoxelMaterialType.WATER.value,
                                   VoxelMaterialType.LAVA.value)
        ]
        for block in fluid_blocks[:_FLUID_TICK_BUDGET]:
            below_key = _block_key(block.x, block.y - 1, block.z)
            if block.y - 1 < 0:
                continue
            if self._blocks.get(below_key) is None:
                material = block.material_type
                chunk = self._chunks.get(block.chunk_id)
                if chunk is not None:
                    chunk.blocks.pop(_block_key(block.x, block.y, block.z), None)
                    chunk.state = ChunkState.DIRTY.value
                self._blocks.pop(_block_key(block.x, block.y, block.z), None)
                self._place_block_internal(
                    block.x, block.y - 1, block.z, material,
                    record_mod=False,
                )
                moved += 1
        return moved

    def _tick_light(self) -> int:
        # Approximate light propagation: mark blocks near light sources.
        updated = 0
        light_sources = [
            b for b in self._blocks.values()
            if self._materials.get(b.material_type) is not None
            and self._materials[b.material_type].light_emission > 0
        ]
        for src in light_sources[:128]:
            for block in self._blocks.values():
                if abs(block.x - src.x) <= 4 and abs(block.y - src.y) <= 4 and abs(block.z - src.z) <= 4:
                    block.light_level = max(block.light_level, 0.5)
            updated += 1
        return updated

    def tick(self, dt: float = 0.1) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            fluids_moved = self._tick_fluids()
            light_sources = self._tick_light() if self._config.light_propagation else 0
            # Unload chunks marked for unloading.
            unloading_keys = [
                ck for ck, c in self._chunks.items()
                if c.state == ChunkState.UNLOADING.value
            ]
            for ck in unloading_keys:
                chunk = self._chunks.get(ck)
                if chunk is None:
                    continue
                stale = [bk for bk, b in self._blocks.items() if b.chunk_id == ck]
                for bk in stale:
                    self._blocks.pop(bk, None)
                self._chunks.pop(ck, None)
            if self._tick_count % 60 == 0:
                self._log_event(VoxelWorldEventKind.TICK.value,
                                {"tick": self._tick_count, "dt": dt,
                                 "fluids_moved": fluids_moved,
                                 "light_sources": light_sources,
                                 "unloaded": len(unloading_keys)})
            if fluids_moved > 0:
                self._log_event(VoxelWorldEventKind.FLUID_FLOWED.value,
                                {"moved": fluids_moved})
            self._update_stats()
            return {
                "tick_count": self._tick_count,
                "fluids_moved": fluids_moved,
                "light_sources_processed": light_sources,
                "chunks_unloaded": len(unloading_keys),
            }

    def set_config(self, updates: Dict[str, Any]) -> Tuple[bool, str, VoxelWorldConfig]:
        with _LOCK:
            if not updates:
                return True, "noop", self._config
            changed: List[str] = []
            for k, v in updates.items():
                if hasattr(self._config, k):
                    old_val = getattr(self._config, k)
                    setattr(self._config, k, v)
                    changed.append(f"{k}: {old_val}->{v}")
            if changed:
                self._log_event(VoxelWorldEventKind.CONFIG_UPDATED.value,
                                {"changes": changed})
            return True, "updated", self._config

    def get_config(self) -> VoxelWorldConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100,
                    event_type: str = "") -> List[Dict[str, Any]]:
        with _LOCK:
            results = list(self._events)
            if event_type:
                results = [e for e in results if e.kind == event_type]
            if limit > 0:
                results = results[-limit:]
            return [e.to_dict() for e in results]

    def get_stats(self) -> VoxelWorldStats:
        with _LOCK:
            self._update_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            ready_chunks = sum(
                1 for c in self._chunks.values()
                if c.state == ChunkState.READY.value
            )
            dirty_chunks = sum(
                1 for c in self._chunks.values()
                if c.state == ChunkState.DIRTY.value
            )
            return {
                "initialized": self._initialized,
                "total_materials": len(self._materials),
                "total_biomes": len(self._biomes),
                "total_chunks": len(self._chunks),
                "ready_chunks": ready_chunks,
                "dirty_chunks": dirty_chunks,
                "total_blocks": len(self._blocks),
                "total_structures": len(self._structures),
                "total_modifications": len(self._modifications),
                "blocks_placed": self._stats.blocks_placed,
                "blocks_removed": self._stats.blocks_removed,
                "structures_built": self._stats.structures_built,
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> VoxelWorldSnapshot:
        with _LOCK:
            self._update_stats()
            return VoxelWorldSnapshot(
                timestamp=_now(),
                config=self._config.to_dict(),
                stats=self._stats.to_dict(),
                chunks=[c.to_dict() for c in list(self._chunks.values())[:32]],
                structures=[s.to_dict() for s in list(self._structures.values())[:32]],
                biomes=[b.to_dict() for b in list(self._biomes.values())[:32]],
            )

    def reset(self) -> Tuple[bool, str]:
        with _LOCK:
            self._materials.clear()
            self._biomes.clear()
            self._chunks.clear()
            self._blocks.clear()
            self._structures.clear()
            self._modifications.clear()
            self._modifications_by_id.clear()
            self._events.clear()
            self._stats = VoxelWorldStats()
            self._config = VoxelWorldConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._block_counter = 0
            self._mod_counter = 0
            self._chunk_counter = 0
            self._initialized = False
            self._seed()
            self._log_event(VoxelWorldEventKind.RESET.value, {})
            return True, "reset"


def get_voxel_world_system() -> VoxelWorldSystem:
    """Factory that returns the singleton VoxelWorldSystem instance."""
    return VoxelWorldSystem.get_instance()
