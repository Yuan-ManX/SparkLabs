"""
SparkLabs Engine - TileMap Runtime System

Comprehensive 2D tilemap rendering and management system for grid-based
game worlds. Provides tile definitions, tileset loading, multi-layer
tilemap composition, brush-based painting with presets, auto-tiling
with 8-neighbor rule matching, collision detection, and export/serialization
utilities. Manages the full lifecycle of tile-based world data.

Architecture:
  EngineTileMapRuntime (Singleton)
    |-- TileDefinition        — individual tile properties and collision
    |-- Tileset               — source image and tile layout metadata
    |-- TileLayer             — single grid plane with opacity and parallax
    |-- TileMap               — aggregate of layers and tilesets
    |-- TileBrush             — shape-based painting tool with presets
    |-- AutoTileConfig        — 8-neighbor matching rules for auto-tiling
    |-- TileLayerType (enum)  — semantic layer classification
    |-- TileCollisionShape    — collision geometry per tile
    |-- TileAnimationMode     — per-tile animation behavior
    |-- RenderOrder           — draw order strategy for overlapping tiles

Collision Presets:
  Predefined tile collider configurations for common 2D platformer and
  top-down game scenarios including full blocks, slopes, half-blocks,
  and one-way platforms.

Brush Presets:
  Ready-to-use brush configurations for terrain painting, decoration
  placement, and pattern stamping with SINGLE, RECTANGLE, CIRCLE, and
  PATTERN brush types.

AutoTiling Rules:
  Built-in 8-neighbor rule sets for terrain blending, edge matching,
  and transition tile generation using bitmask-based matching.
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


class TileLayerType(Enum):
    """Semantic classification of tilemap layers for rendering and physics.

    TERRAIN:     Base ground tiles forming the world geometry.
    DECORATION:  Visual detail tiles placed on top of terrain.
    COLLISION:   Invisible tiles defining solid collision boundaries.
    OVERLAY:     Foreground tiles rendered above all gameplay elements.
    WATER:       Animated water tiles with surface effects.
    SHADOW:      Shadow-casting information for lighting systems.
    LIGHTING:    Light source placement and intensity data.
    TRIGGER:     Trigger zone tiles for event activation.
    NAVIGATION:  Pathfinding walkability and cost data.
    """

    TERRAIN = "terrain"
    DECORATION = "decoration"
    COLLISION = "collision"
    OVERLAY = "overlay"
    WATER = "water"
    SHADOW = "shadow"
    LIGHTING = "lighting"
    TRIGGER = "trigger"
    NAVIGATION = "navigation"


class TileCollisionShape(Enum):
    """Collision geometry shape assigned to a single tile cell.

    NONE:         No collision, fully passable.
    FULL:         Solid square occupying the entire tile.
    SLOPE_NE:     Diagonal slope from bottom-left to top-right.
    SLOPE_NW:     Diagonal slope from bottom-right to top-left.
    SLOPE_SE:     Diagonal slope from top-left to bottom-right.
    SLOPE_SW:     Diagonal slope from top-right to bottom-left.
    HALF_TOP:     Solid upper half of the tile.
    HALF_BOTTOM:  Solid lower half of the tile.
    """

    NONE = "none"
    FULL = "full"
    SLOPE_NE = "slope_ne"
    SLOPE_NW = "slope_nw"
    SLOPE_SE = "slope_se"
    SLOPE_SW = "slope_sw"
    HALF_TOP = "half_top"
    HALF_BOTTOM = "half_bottom"


class TileAnimationMode(Enum):
    """Animation playback behavior for animated tiles.

    NONE:          Static tile with no animation.
    LOOP:          Cycles through frames continuously.
    PING_PONG:     Reverses direction at frame boundaries.
    ONCE:          Plays once and stops at the final frame.
    RANDOM_FRAME:  Picks a random frame each cycle.
    """

    NONE = "none"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    ONCE = "once"
    RANDOM_FRAME = "random_frame"


class RenderOrder(Enum):
    """Draw order for tiles within a layer to resolve depth ambiguity.

    RIGHT_DOWN:  Renders right-to-left, top-to-bottom (default).
    RIGHT_UP:    Renders right-to-left, bottom-to-top.
    LEFT_DOWN:   Renders left-to-right, top-to-bottom.
    LEFT_UP:     Renders left-to-right, bottom-to-top.
    """

    RIGHT_DOWN = "right_down"
    RIGHT_UP = "right_up"
    LEFT_DOWN = "left_down"
    LEFT_UP = "left_up"


# ------------------------------------------------------------------
# Pre-defined tile collider lookup tables
# ------------------------------------------------------------------

_PREDEFINED_COLLIDERS: Dict[str, Dict[str, Any]] = {
    "empty": {
        "collision_shape": TileCollisionShape.NONE,
        "is_solid": False,
        "description": "Fully passable empty tile",
    },
    "solid_full": {
        "collision_shape": TileCollisionShape.FULL,
        "is_solid": True,
        "description": "Solid square block",
    },
    "slope_45_ne": {
        "collision_shape": TileCollisionShape.SLOPE_NE,
        "is_solid": True,
        "description": "45-degree slope bottom-left to top-right",
    },
    "slope_45_nw": {
        "collision_shape": TileCollisionShape.SLOPE_NW,
        "is_solid": True,
        "description": "45-degree slope bottom-right to top-left",
    },
    "slope_45_se": {
        "collision_shape": TileCollisionShape.SLOPE_SE,
        "is_solid": True,
        "description": "45-degree slope top-left to bottom-right",
    },
    "slope_45_sw": {
        "collision_shape": TileCollisionShape.SLOPE_SW,
        "is_solid": True,
        "description": "45-degree slope top-right to bottom-left",
    },
    "half_top": {
        "collision_shape": TileCollisionShape.HALF_TOP,
        "is_solid": True,
        "description": "Solid only in the upper half of the tile",
    },
    "half_bottom": {
        "collision_shape": TileCollisionShape.HALF_BOTTOM,
        "is_solid": True,
        "description": "Solid only in the lower half of the tile",
    },
    "platform_one_way": {
        "collision_shape": TileCollisionShape.HALF_TOP,
        "is_solid": True,
        "description": "One-way platform passable from below",
    },
    "water_passable": {
        "collision_shape": TileCollisionShape.NONE,
        "is_solid": False,
        "description": "Water tile with no collision but slow movement",
    },
    "ladder": {
        "collision_shape": TileCollisionShape.NONE,
        "is_solid": False,
        "description": "Climbable ladder tile",
    },
    "spike": {
        "collision_shape": TileCollisionShape.FULL,
        "is_solid": True,
        "description": "Damage-dealing spike tile",
    },
    "ice": {
        "collision_shape": TileCollisionShape.FULL,
        "is_solid": True,
        "description": "Slippery ice surface tile",
    },
    "conveyor_left": {
        "collision_shape": TileCollisionShape.FULL,
        "is_solid": True,
        "description": "Conveyor belt pushing entities left",
    },
    "conveyor_right": {
        "collision_shape": TileCollisionShape.FULL,
        "is_solid": True,
        "description": "Conveyor belt pushing entities right",
    },
}

# ------------------------------------------------------------------
# Pre-defined brush presets
# ------------------------------------------------------------------

_BRUSH_PRESETS: Dict[str, Dict[str, Any]] = {
    "single_tile": {
        "name": "Single Tile",
        "brush_type": "SINGLE",
        "size": 1,
        "randomized": False,
        "description": "Places a single tile at the cursor position",
    },
    "square_3x3": {
        "name": "3x3 Square",
        "brush_type": "RECTANGLE",
        "size": 3,
        "randomized": False,
        "description": "Fills a 3x3 square region",
    },
    "square_5x5": {
        "name": "5x5 Square",
        "brush_type": "RECTANGLE",
        "size": 5,
        "randomized": False,
        "description": "Fills a 5x5 square region",
    },
    "circle_radius_2": {
        "name": "Circle R2",
        "brush_type": "CIRCLE",
        "size": 2,
        "randomized": False,
        "description": "Fills a circular area with radius 2",
    },
    "circle_radius_4": {
        "name": "Circle R4",
        "brush_type": "CIRCLE",
        "size": 4,
        "randomized": False,
        "description": "Fills a circular area with radius 4",
    },
    "scatter_3x3": {
        "name": "Scatter 3x3",
        "brush_type": "RECTANGLE",
        "size": 3,
        "randomized": True,
        "description": "Randomly scatters tiles within a 3x3 area",
    },
    "scatter_5x5": {
        "name": "Scatter 5x5",
        "brush_type": "RECTANGLE",
        "size": 5,
        "randomized": True,
        "description": "Randomly scatters tiles within a 5x5 area",
    },
    "grass_pattern": {
        "name": "Grass Pattern",
        "brush_type": "PATTERN",
        "size": 3,
        "randomized": True,
        "description": "Pattern brush for natural grass placement",
    },
    "rock_pattern": {
        "name": "Rock Pattern",
        "brush_type": "PATTERN",
        "size": 2,
        "randomized": True,
        "description": "Pattern brush for scattered rock placement",
    },
    "line_horizontal": {
        "name": "Horizontal Line",
        "brush_type": "RECTANGLE",
        "size": 1,
        "randomized": False,
        "description": "Draws a horizontal line of tiles",
    },
}

# ------------------------------------------------------------------
# Pre-defined auto-tiling rule sets
# ------------------------------------------------------------------

_AUTOTILE_RULE_SETS: Dict[str, Dict[str, Any]] = {
    "terrain_edge": {
        "name": "Terrain Edge Matching",
        "description": "Standard 8-way terrain edge auto-tiling",
        "rule_masks": {
            "center": 0,
            "north": 1,
            "south": 2,
            "east": 4,
            "west": 8,
            "northeast": 16,
            "northwest": 32,
            "southeast": 64,
            "southwest": 128,
        },
        "transition_tiles": [
            (0, "center_isolated"),
            (1, "edge_north"),
            (2, "edge_south"),
            (3, "edge_north_south"),
            (4, "edge_east"),
            (5, "edge_north_east"),
            (6, "edge_south_east"),
            (7, "edge_north_south_east"),
            (8, "edge_west"),
            (9, "edge_north_west"),
            (10, "edge_south_west"),
            (11, "edge_north_south_west"),
            (12, "edge_east_west"),
            (13, "edge_north_east_west"),
            (14, "edge_south_east_west"),
            (15, "center_filled"),
        ],
        "corner_tiles": [
            (16, "inner_corner_ne"),
            (17, "inner_corner_nw"),
            (18, "inner_corner_se"),
            (19, "inner_corner_sw"),
        ],
    },
    "water_edge": {
        "name": "Water Edge Blending",
        "description": "Smooth water-to-land transition auto-tiling",
        "rule_masks": {
            "center": 0,
            "north": 1,
            "south": 2,
            "east": 4,
            "west": 8,
            "northeast": 16,
            "northwest": 32,
            "southeast": 64,
            "southwest": 128,
        },
        "transition_tiles": [
            (0, "deep_water"),
            (1, "shore_north"),
            (2, "shore_south"),
            (4, "shore_east"),
            (8, "shore_west"),
            (15, "shallow_water_fill"),
        ],
        "corner_tiles": [
            (16, "shore_corner_ne"),
            (17, "shore_corner_nw"),
            (18, "shore_corner_se"),
            (19, "shore_corner_sw"),
        ],
    },
    "wall_auto_tile": {
        "name": "Wall Auto-Tiling",
        "description": "Top-down wall bordering with 4-way adjacency",
        "rule_masks": {
            "center": 0,
            "north": 1,
            "south": 2,
            "east": 4,
            "west": 8,
        },
        "transition_tiles": [
            (0, "wall_pillar"),
            (1, "wall_top"),
            (2, "wall_bottom"),
            (3, "wall_vertical"),
            (4, "wall_right"),
            (5, "wall_corner_tr"),
            (6, "wall_corner_br"),
            (7, "wall_t_bottom"),
            (8, "wall_left"),
            (9, "wall_corner_tl"),
            (10, "wall_corner_bl"),
            (11, "wall_t_bottom_mirror"),
            (12, "wall_horizontal"),
            (13, "wall_t_right"),
            (14, "wall_t_left"),
            (15, "wall_filled"),
        ],
        "corner_tiles": [],
    },
    "path_auto_tile": {
        "name": "Path Auto-Tiling",
        "description": "Dirt path blending into grass terrain",
        "rule_masks": {
            "center": 0,
            "north": 1,
            "south": 2,
            "east": 4,
            "west": 8,
            "northeast": 16,
            "northwest": 32,
            "southeast": 64,
            "southwest": 128,
        },
        "transition_tiles": [
            (0, "path_center"),
            (1, "path_end_north"),
            (2, "path_end_south"),
            (3, "path_straight_vertical"),
            (4, "path_end_east"),
            (5, "path_corner_ne"),
            (6, "path_corner_se"),
            (7, "path_t_north"),
            (8, "path_end_west"),
            (9, "path_corner_nw"),
            (10, "path_corner_sw"),
            (11, "path_t_south"),
            (12, "path_straight_horizontal"),
            (13, "path_t_east"),
            (14, "path_t_west"),
            (15, "path_cross"),
        ],
        "corner_tiles": [],
    },
}


@dataclass
class TileDefinition:
    """Properties of a single tile within a tileset.

    Defines collision behavior, animation parameters, and custom
    metadata for one tile index in the source tileset.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tileset_id: str = ""
    tile_index: int = 0
    collision_shape: TileCollisionShape = TileCollisionShape.NONE
    animation_mode: TileAnimationMode = TileAnimationMode.NONE
    animation_frames: List[int] = field(default_factory=list)
    animation_speed_ms: float = 100.0
    properties: Dict[str, Any] = field(default_factory=dict)
    is_solid: bool = False
    tile_type: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tileset_id": self.tileset_id,
            "tile_index": self.tile_index,
            "collision_shape": self.collision_shape.value,
            "animation_mode": self.animation_mode.value,
            "animation_frames": list(self.animation_frames),
            "animation_speed_ms": self.animation_speed_ms,
            "properties": dict(self.properties),
            "is_solid": self.is_solid,
            "tile_type": self.tile_type,
            "created_at": self.created_at,
        }


@dataclass
class Tileset:
    """A collection of tiles extracted from a single source image.

    Tilesets define the grid layout of tiles within a texture atlas
    and store per-tile definitions for collision, animation, and
    custom properties.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    image_key: str = ""
    tile_width: int = 32
    tile_height: int = 32
    tile_count: int = 0
    columns: int = 0
    margin: int = 0
    spacing: int = 0
    first_gid: int = 1
    tile_definitions: List[TileDefinition] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "image_key": self.image_key,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "tile_count": self.tile_count,
            "columns": self.columns,
            "margin": self.margin,
            "spacing": self.spacing,
            "first_gid": self.first_gid,
            "tile_definitions": [td.to_dict() for td in self.tile_definitions],
            "created_at": self.created_at,
        }


@dataclass
class TileLayer:
    """A single grid plane within a tilemap holding tile index data.

    Each layer stores a 2D grid of tile indices along with rendering
    properties such as opacity, visibility, parallax scrolling factor,
    and z-order for depth sorting.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    layer_type: TileLayerType = TileLayerType.TERRAIN
    width: int = 0
    height: int = 0
    tile_data: List[List[int]] = field(default_factory=list)
    opacity: float = 1.0
    visible: bool = True
    parallax_factor: Tuple[float, float] = (1.0, 1.0)
    z_order: int = 0
    render_order: RenderOrder = RenderOrder.RIGHT_DOWN
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "layer_type": self.layer_type.value,
            "width": self.width,
            "height": self.height,
            "tile_data": [list(row) for row in self.tile_data],
            "opacity": self.opacity,
            "visible": self.visible,
            "parallax_factor": list(self.parallax_factor),
            "z_order": self.z_order,
            "render_order": self.render_order.value,
            "tile_count": sum(1 for row in self.tile_data for t in row if t >= 0),
            "created_at": self.created_at,
        }


@dataclass
class TileMap:
    """A complete tilemap composed of multiple layers and tilesets.

    Represents a full grid-based game world with all its rendering
    layers, source tilesets, and global configuration such as world
    position offset and render order.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    layers: List[TileLayer] = field(default_factory=list)
    tilesets: List[Tileset] = field(default_factory=list)
    map_width: int = 0
    map_height: int = 0
    tile_width: int = 32
    tile_height: int = 32
    world_position: Tuple[int, int] = (0, 0)
    render_order: RenderOrder = RenderOrder.RIGHT_DOWN
    total_layers: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "layers": [layer.to_dict() for layer in self.layers],
            "tilesets": [ts.to_dict() for ts in self.tilesets],
            "map_width": self.map_width,
            "map_height": self.map_height,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "world_position": list(self.world_position),
            "render_order": self.render_order.value,
            "total_layers": len(self.layers),
            "created_at": self.created_at,
        }


@dataclass
class TileBrush:
    """A painting tool for applying tile patterns to tilemap layers.

    Brushes support SINGLE, RECTANGLE, CIRCLE, and PATTERN placement
    modes with configurable sizes and randomization for natural-looking
    results.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tiles: List[Tuple[int, int, int]] = field(default_factory=list)
    brush_type: str = "SINGLE"
    size: int = 1
    randomized: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tiles": [list(t) for t in self.tiles],
            "brush_type": self.brush_type,
            "size": self.size,
            "randomized": self.randomized,
            "tile_count": len(self.tiles),
            "created_at": self.created_at,
        }


@dataclass
class AutoTileConfig:
    """Configuration for automated tile placement based on neighbor rules.

    Uses 8-neighbor bitmask matching to select the correct tile index
    for seamless terrain transitions, water edges, wall borders, and
    path blending.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    source_tileset: str = ""
    rule_masks: Dict[str, int] = field(default_factory=dict)
    transition_tiles: List[Tuple[int, str]] = field(default_factory=list)
    corner_tiles: List[Tuple[int, str]] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source_tileset": self.source_tileset,
            "rule_masks": dict(self.rule_masks),
            "transition_tiles": [list(t) for t in self.transition_tiles],
            "corner_tiles": [list(c) for c in self.corner_tiles],
            "created_at": self.created_at,
        }


class EngineTileMapRuntime:
    """Comprehensive 2D tilemap rendering and management system.

    Manages tilemap creation, multi-layer composition, tileset loading,
    brush-based painting, auto-tiling, and data export. Provides
    collision detection presets, brush presets, and built-in auto-tiling
    rule sets for rapid world-building workflows.

    Usage:
        runtime = get_tilemap_runtime()
        map_id = runtime.create_tilemap("overworld", 64, 48, 32, 32)
        layer_id = runtime.add_layer(map_id, "terrain", "terrain", 64, 48)
        runtime.set_tile(map_id, layer_id, 10, 10, 5)
        preset = runtime.create_brush_from_preset("square_3x3")
        runtime.paint_brush(map_id, layer_id, preset, 20, 15)
    """

    _instance: Optional["EngineTileMapRuntime"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_TILEMAPS: int = 256
    MAX_LAYERS_PER_MAP: int = 64
    MAX_TILESETS_PER_MAP: int = 32
    MAX_TILE_DEFINITIONS_PER_SET: int = 4096

    def __new__(cls) -> "EngineTileMapRuntime":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._tilemaps: Dict[str, TileMap] = {}
        self._tilesets: Dict[str, Tileset] = {}
        self._brushes: Dict[str, TileBrush] = {}
        self._autotile_configs: Dict[str, AutoTileConfig] = {}
        self._collider_presets: Dict[str, Dict[str, Any]] = dict(_PREDEFINED_COLLIDERS)
        self._brush_presets: Dict[str, Dict[str, Any]] = dict(_BRUSH_PRESETS)
        self._autotile_rule_sets: Dict[str, Dict[str, Any]] = dict(_AUTOTILE_RULE_SETS)
        self._total_tiles_set: int = 0
        self._total_brush_paints: int = 0
        self._total_autotile_applications: int = 0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EngineTileMapRuntime":
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_map(self, map_id: str) -> TileMap:
        _time_module.sleep(0.001)
        if map_id not in self._tilemaps:
            raise KeyError(f"TileMap '{map_id}' does not exist")
        return self._tilemaps[map_id]

    def _get_layer(self, map_id: str, layer_id: str) -> TileLayer:
        _time_module.sleep(0.001)
        tilemap = self._get_map(map_id)
        for layer in tilemap.layers:
            if layer.id == layer_id:
                return layer
        raise KeyError(f"Layer '{layer_id}' not found in map '{map_id}'")

    def _is_in_bounds(self, layer: TileLayer, x: int, y: int) -> bool:
        _time_module.sleep(0.001)
        return 0 <= x < layer.width and 0 <= y < layer.height

    def _ensure_tile_data(self, layer: TileLayer) -> None:
        _time_module.sleep(0.001)
        if not layer.tile_data or len(layer.tile_data) != layer.height:
            layer.tile_data = [
                [-1] * layer.width for _ in range(layer.height)
            ]

    def _build_neighbor_mask(
        self, layer: TileLayer, x: int, y: int, target_index: int
    ) -> int:
        _time_module.sleep(0.001)
        mask = 0
        neighbor_checks: List[Tuple[int, int, int]] = [
            (0, -1, 1), (1, -1, 16), (1, 0, 4),
            (1, 1, 64), (0, 1, 2), (-1, 1, 128),
            (-1, 0, 8), (-1, -1, 32),
        ]
        for dx, dy, bit in neighbor_checks:
            nx, ny = x + dx, y + dy
            if self._is_in_bounds(layer, nx, ny):
                if layer.tile_data[ny][nx] == target_index:
                    mask |= bit
        return mask

    def _compute_brush_positions(
        self, brush: TileBrush, center_x: int, center_y: int
    ) -> List[Tuple[int, int, int]]:
        _time_module.sleep(0.001)
        positions: List[Tuple[int, int, int]] = []
        if brush.brush_type == "SINGLE":
            if brush.tiles:
                for tile_index, dx, dy in brush.tiles:
                    positions.append((tile_index, center_x + dx, center_y + dy))
            else:
                positions.append((0, center_x, center_y))
        elif brush.brush_type == "RECTANGLE":
            half = brush.size // 2
            for dy in range(-half, half + 1):
                for dx in range(-half, half + 1):
                    if brush.randomized and random.random() < 0.5:
                        continue
                    tile_index = (
                        random.choice(brush.tiles)[0]
                        if brush.tiles and brush.randomized
                        else (brush.tiles[0][0] if brush.tiles else 0)
                    )
                    positions.append((tile_index, center_x + dx, center_y + dy))
        elif brush.brush_type == "CIRCLE":
            r_sq = brush.size * brush.size
            for dy in range(-brush.size, brush.size + 1):
                for dx in range(-brush.size, brush.size + 1):
                    if dx * dx + dy * dy > r_sq:
                        continue
                    if brush.randomized and random.random() < 0.5:
                        continue
                    tile_index = (
                        random.choice(brush.tiles)[0]
                        if brush.tiles and brush.randomized
                        else (brush.tiles[0][0] if brush.tiles else 0)
                    )
                    positions.append((tile_index, center_x + dx, center_y + dy))
        elif brush.brush_type == "PATTERN":
            if brush.tiles:
                for tile_index, dx, dy in brush.tiles:
                    positions.append((tile_index, center_x + dx, center_y + dy))
            else:
                positions.append((0, center_x, center_y))
        return positions

    # ------------------------------------------------------------------
    # TileMap management
    # ------------------------------------------------------------------

    def create_tilemap(
        self,
        name: str,
        width: int,
        height: int,
        tile_width: int,
        tile_height: int,
    ) -> str:
        _time_module.sleep(0.001)
        if len(self._tilemaps) >= self.MAX_TILEMAPS:
            raise RuntimeError(
                f"TileMap limit reached ({self.MAX_TILEMAPS})"
            )
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        if tile_width <= 0 or tile_height <= 0:
            raise ValueError("tile_width and tile_height must be positive")

        tilemap = TileMap(
            name=name,
            map_width=width,
            map_height=height,
            tile_width=tile_width,
            tile_height=tile_height,
        )
        self._tilemaps[tilemap.id] = tilemap
        return tilemap.id

    def add_layer(
        self,
        map_id: str,
        name: str,
        layer_type: str,
        width: int,
        height: int,
    ) -> str:
        _time_module.sleep(0.001)
        tilemap = self._get_map(map_id)
        if len(tilemap.layers) >= self.MAX_LAYERS_PER_MAP:
            raise RuntimeError(
                f"Layer limit reached ({self.MAX_LAYERS_PER_MAP}) for map '{map_id}'"
            )

        try:
            lt = TileLayerType(layer_type.lower())
        except ValueError:
            lt = TileLayerType.TERRAIN

        layer = TileLayer(
            name=name,
            layer_type=lt,
            width=width,
            height=height,
            z_order=len(tilemap.layers),
        )
        self._ensure_tile_data(layer)
        tilemap.layers.append(layer)
        return layer.id

    def get_tile_at(
        self,
        map_id: str,
        layer_id: str,
        x: int,
        y: int,
    ) -> Optional[int]:
        _time_module.sleep(0.001)
        layer = self._get_layer(map_id, layer_id)
        if not self._is_in_bounds(layer, x, y):
            return None
        if not layer.tile_data or y >= len(layer.tile_data):
            return None
        row = layer.tile_data[y]
        if x >= len(row):
            return None
        return row[x]

    def set_tile(
        self,
        map_id: str,
        layer_id: str,
        x: int,
        y: int,
        tile_index: int,
    ) -> bool:
        _time_module.sleep(0.001)
        layer = self._get_layer(map_id, layer_id)
        if not self._is_in_bounds(layer, x, y):
            return False
        self._ensure_tile_data(layer)
        previous = layer.tile_data[y][x]
        layer.tile_data[y][x] = tile_index
        if previous < 0 and tile_index >= 0:
            self._total_tiles_set += 1
        elif previous >= 0 and tile_index < 0:
            self._total_tiles_set = max(0, self._total_tiles_set - 1)
        return True

    def fill_region(
        self,
        map_id: str,
        layer_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_index: int,
    ) -> int:
        _time_module.sleep(0.001)
        layer = self._get_layer(map_id, layer_id)
        self._ensure_tile_data(layer)
        count = 0
        for dy in range(height):
            for dx in range(width):
                gx, gy = x + dx, y + dy
                if self._is_in_bounds(layer, gx, gy):
                    previous = layer.tile_data[gy][gx]
                    layer.tile_data[gy][gx] = tile_index
                    if previous < 0 and tile_index >= 0:
                        self._total_tiles_set += 1
                    elif previous >= 0 and tile_index < 0:
                        self._total_tiles_set = max(0, self._total_tiles_set - 1)
                    count += 1
        return count

    def set_layer_opacity(
        self,
        map_id: str,
        layer_id: str,
        opacity: float,
    ) -> bool:
        _time_module.sleep(0.001)
        layer = self._get_layer(map_id, layer_id)
        layer.opacity = max(0.0, min(1.0, opacity))
        return True

    # ------------------------------------------------------------------
    # Tileset management
    # ------------------------------------------------------------------

    def load_tileset(
        self,
        name: str,
        image_key: str,
        tile_width: int,
        tile_height: int,
        columns: int,
    ) -> str:
        _time_module.sleep(0.001)
        if len(self._tilesets) >= self.MAX_TILESETS_PER_MAP:
            raise RuntimeError(
                f"Tileset limit reached ({self.MAX_TILESETS_PER_MAP})"
            )

        tile_count = 0
        rows = 0
        if columns > 0:
            rows = max(1, tile_count // columns) if tile_count > 0 else 1

        tileset = Tileset(
            name=name,
            image_key=image_key,
            tile_width=tile_width,
            tile_height=tile_height,
            tile_count=tile_count,
            columns=columns,
            first_gid=len(self._tilesets) + 1,
        )
        self._tilesets[tileset.id] = tileset
        return tileset.id

    def add_tile_definition(
        self,
        tileset_id: str,
        tile_index: int,
        collision_shape: str = "none",
        animation_mode: str = "none",
        is_solid: bool = False,
    ) -> Optional[str]:
        _time_module.sleep(0.001)
        tileset = self._tilesets.get(tileset_id)
        if tileset is None:
            return None
        if len(tileset.tile_definitions) >= self.MAX_TILE_DEFINITIONS_PER_SET:
            return None

        try:
            cs = TileCollisionShape(collision_shape.lower())
        except ValueError:
            cs = TileCollisionShape.NONE
        try:
            am = TileAnimationMode(animation_mode.lower())
        except ValueError:
            am = TileAnimationMode.NONE

        tile_def = TileDefinition(
            tileset_id=tileset_id,
            tile_index=tile_index,
            collision_shape=cs,
            animation_mode=am,
            is_solid=is_solid,
        )
        tileset.tile_definitions.append(tile_def)
        if tileset.tile_count <= tile_index:
            tileset.tile_count = tile_index + 1
        return tile_def.id

    def apply_collider_preset(
        self,
        tileset_id: str,
        tile_index: int,
        preset_name: str,
    ) -> Optional[str]:
        _time_module.sleep(0.001)
        preset = self._collider_presets.get(preset_name)
        if preset is None:
            return None
        return self.add_tile_definition(
            tileset_id=tileset_id,
            tile_index=tile_index,
            collision_shape=preset["collision_shape"].value,
            is_solid=preset["is_solid"],
        )

    # ------------------------------------------------------------------
    # Brush management
    # ------------------------------------------------------------------

    def create_brush(
        self,
        name: str,
        tiles: List[Tuple[int, int, int]],
        brush_type: str = "SINGLE",
        size: int = 1,
        randomized: bool = False,
    ) -> str:
        _time_module.sleep(0.001)
        valid_types = {"SINGLE", "RECTANGLE", "CIRCLE", "PATTERN"}
        if brush_type not in valid_types:
            brush_type = "SINGLE"

        brush = TileBrush(
            name=name,
            tiles=tiles,
            brush_type=brush_type,
            size=size,
            randomized=randomized,
        )
        self._brushes[brush.id] = brush
        return brush.id

    def create_brush_from_preset(self, preset_name: str) -> Optional[str]:
        _time_module.sleep(0.001)
        preset = self._brush_presets.get(preset_name)
        if preset is None:
            return None
        return self.create_brush(
            name=preset["name"],
            tiles=[],
            brush_type=preset["brush_type"],
            size=preset["size"],
            randomized=preset["randomized"],
        )

    def paint_brush(
        self,
        map_id: str,
        layer_id: str,
        brush: TileBrush,
        center_x: int,
        center_y: int,
    ) -> int:
        _time_module.sleep(0.001)
        layer = self._get_layer(map_id, layer_id)
        self._ensure_tile_data(layer)
        positions = self._compute_brush_positions(brush, center_x, center_y)
        count = 0
        for tile_index, gx, gy in positions:
            if self._is_in_bounds(layer, gx, gy):
                previous = layer.tile_data[gy][gx]
                layer.tile_data[gy][gx] = tile_index
                if previous < 0 and tile_index >= 0:
                    self._total_tiles_set += 1
                elif previous >= 0 and tile_index < 0:
                    self._total_tiles_set = max(0, self._total_tiles_set - 1)
                count += 1
        self._total_brush_paints += 1
        return count

    def paint_brush_with_preset(
        self,
        map_id: str,
        layer_id: str,
        preset_name: str,
        center_x: int,
        center_y: int,
        tile_index: int = 0,
    ) -> int:
        _time_module.sleep(0.001)
        brush_id = self.create_brush_from_preset(preset_name)
        if brush_id is None:
            return 0
        brush = self._brushes[brush_id]
        if not brush.tiles:
            brush.tiles = [(tile_index, 0, 0)]
        return self.paint_brush(map_id, layer_id, brush, center_x, center_y)

    def get_brush(self, brush_id: str) -> Optional[TileBrush]:
        _time_module.sleep(0.001)
        return self._brushes.get(brush_id)

    def list_brush_presets(self) -> List[str]:
        _time_module.sleep(0.001)
        return sorted(self._brush_presets.keys())

    # ------------------------------------------------------------------
    # Auto-tiling
    # ------------------------------------------------------------------

    def create_autotile_config(
        self,
        name: str,
        source_tileset: str,
        rule_masks: Dict[str, int],
        transition_tiles: List[Tuple[int, str]],
        corner_tiles: Optional[List[Tuple[int, str]]] = None,
    ) -> str:
        _time_module.sleep(0.001)
        config = AutoTileConfig(
            name=name,
            source_tileset=source_tileset,
            rule_masks=rule_masks,
            transition_tiles=transition_tiles,
            corner_tiles=corner_tiles or [],
        )
        self._autotile_configs[config.id] = config
        return config.id

    def create_autotile_from_ruleset(
        self, ruleset_name: str, source_tileset: str = ""
    ) -> Optional[str]:
        _time_module.sleep(0.001)
        ruleset = self._autotile_rule_sets.get(ruleset_name)
        if ruleset is None:
            return None
        return self.create_autotile_config(
            name=ruleset["name"],
            source_tileset=source_tileset,
            rule_masks=ruleset["rule_masks"],
            transition_tiles=ruleset["transition_tiles"],
            corner_tiles=ruleset.get("corner_tiles", []),
        )

    def apply_auto_tiling(
        self,
        map_id: str,
        layer_id: str,
        config: AutoTileConfig,
    ) -> int:
        _time_module.sleep(0.001)
        layer = self._get_layer(map_id, layer_id)
        self._ensure_tile_data(layer)

        mask_to_tile: Dict[int, int] = {}
        for mask_val, _name in config.transition_tiles:
            mask_to_tile[mask_val] = mask_val
        for mask_val, _name in config.corner_tiles:
            mask_to_tile[mask_val] = mask_val

        if not mask_to_tile:
            return 0

        modifications = 0
        for y in range(layer.height):
            for x in range(layer.width):
                current_tile = layer.tile_data[y][x]
                if current_tile < 0:
                    continue
                mask = self._build_neighbor_mask(layer, x, y, current_tile)
                if mask in mask_to_tile:
                    new_tile = mask_to_tile[mask]
                    if new_tile != current_tile:
                        layer.tile_data[y][x] = new_tile
                        modifications += 1

        self._total_autotile_applications += 1
        return modifications

    def apply_auto_tiling_by_ruleset(
        self,
        map_id: str,
        layer_id: str,
        ruleset_name: str,
    ) -> int:
        _time_module.sleep(0.001)
        config_id = self.create_autotile_from_ruleset(ruleset_name)
        if config_id is None:
            return 0
        config = self._autotile_configs[config_id]
        return self.apply_auto_tiling(map_id, layer_id, config)

    def list_autotile_rulesets(self) -> List[str]:
        _time_module.sleep(0.001)
        return sorted(self._autotile_rule_sets.keys())

    # ------------------------------------------------------------------
    # Validation and export
    # ------------------------------------------------------------------

    def validate_tilemap(self, map_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        errors: List[str] = []
        warnings: List[str] = []

        tilemap = self._tilemaps.get(map_id)
        if tilemap is None:
            return {"valid": False, "errors": ["TileMap not found"], "warnings": []}

        if tilemap.map_width <= 0:
            errors.append("map_width is not positive")
        if tilemap.map_height <= 0:
            errors.append("map_height is not positive")
        if tilemap.tile_width <= 0:
            errors.append("tile_width is not positive")
        if tilemap.tile_height <= 0:
            errors.append("tile_height is not positive")

        if not tilemap.layers:
            warnings.append("TileMap has no layers")

        for layer in tilemap.layers:
            if layer.width != tilemap.map_width:
                warnings.append(
                    f"Layer '{layer.name}' width ({layer.width}) "
                    f"differs from map width ({tilemap.map_width})"
                )
            if layer.height != tilemap.map_height:
                warnings.append(
                    f"Layer '{layer.name}' height ({layer.height}) "
                    f"differs from map height ({tilemap.map_height})"
                )
            if not layer.tile_data:
                warnings.append(f"Layer '{layer.name}' has no tile data")
            else:
                if len(layer.tile_data) != layer.height:
                    errors.append(
                        f"Layer '{layer.name}' tile_data row count "
                        f"({len(layer.tile_data)}) != height ({layer.height})"
                    )
                for row_idx, row in enumerate(layer.tile_data):
                    if len(row) != layer.width:
                        errors.append(
                            f"Layer '{layer.name}' row {row_idx} has "
                            f"{len(row)} columns, expected {layer.width}"
                        )
                        break

        if not tilemap.tilesets:
            warnings.append("TileMap has no tilesets assigned")

        tile_count = 0
        for layer in tilemap.layers:
            if layer.tile_data:
                for row in layer.tile_data:
                    tile_count += sum(1 for t in row if t >= 0)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_layers": len(tilemap.layers),
            "total_tilesets": len(tilemap.tilesets),
            "total_tiles_placed": tile_count,
            "map_id": map_id,
        }

    def export_tilemap_data(self, map_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        tilemap = self._get_map(map_id)
        return {
            "version": "1.0.0",
            "tilemap": tilemap.to_dict(),
            "exported_at": _time_module.time(),
            "export_id": uuid.uuid4().hex,
        }

    def export_tilemap_compact(self, map_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        tilemap = self._get_map(map_id)
        layer_data = []
        for layer in tilemap.layers:
            flat_tiles: List[int] = []
            if layer.tile_data:
                for row in layer.tile_data:
                    flat_tiles.extend(row)
            layer_data.append({
                "id": layer.id,
                "name": layer.name,
                "type": layer.layer_type.value,
                "width": layer.width,
                "height": layer.height,
                "tiles": flat_tiles,
                "opacity": layer.opacity,
                "visible": layer.visible,
            })
        return {
            "id": tilemap.id,
            "name": tilemap.name,
            "width": tilemap.map_width,
            "height": tilemap.map_height,
            "tile_width": tilemap.tile_width,
            "tile_height": tilemap.tile_height,
            "layers": layer_data,
            "tilesets": [ts.to_dict() for ts in tilemap.tilesets],
            "exported_at": _time_module.time(),
        }

    # ------------------------------------------------------------------
    # Statistics and lifecycle
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        total_layers = sum(len(tm.layers) for tm in self._tilemaps.values())
        total_tiles_placed = 0
        for tm in self._tilemaps.values():
            for layer in tm.layers:
                if layer.tile_data:
                    for row in layer.tile_data:
                        total_tiles_placed += sum(1 for t in row if t >= 0)

        layer_type_counts: Dict[str, int] = {}
        for tm in self._tilemaps.values():
            for layer in tm.layers:
                lt = layer.layer_type.value
                layer_type_counts[lt] = layer_type_counts.get(lt, 0) + 1

        return {
            "total_tilemaps": len(self._tilemaps),
            "total_layers": total_layers,
            "total_tilesets": len(self._tilesets),
            "total_tiles_set": self._total_tiles_set,
            "total_tiles_placed": total_tiles_placed,
            "total_brushes": len(self._brushes),
            "total_brush_paints": self._total_brush_paints,
            "total_autotile_configs": len(self._autotile_configs),
            "total_autotile_applications": self._total_autotile_applications,
            "collider_presets": len(self._collider_presets),
            "brush_presets": len(self._brush_presets),
            "autotile_rulesets": len(self._autotile_rule_sets),
            "layer_type_distribution": layer_type_counts,
            "max_tilemaps": self.MAX_TILEMAPS,
            "max_layers_per_map": self.MAX_LAYERS_PER_MAP,
        }

    def get_tilemap(self, map_id: str) -> Optional[TileMap]:
        _time_module.sleep(0.001)
        return self._tilemaps.get(map_id)

    def list_tilemaps(self) -> List[TileMap]:
        _time_module.sleep(0.001)
        return list(self._tilemaps.values())

    def remove_tilemap(self, map_id: str) -> bool:
        _time_module.sleep(0.001)
        if map_id in self._tilemaps:
            del self._tilemaps[map_id]
            return True
        return False

    def remove_layer(self, map_id: str, layer_id: str) -> bool:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(map_id)
        if tilemap is None:
            return False
        for i, layer in enumerate(tilemap.layers):
            if layer.id == layer_id:
                tilemap.layers.pop(i)
                return True
        return False

    def reset(self) -> None:
        _time_module.sleep(0.001)
        with self._lock:
            self._tilemaps.clear()
            self._tilesets.clear()
            self._brushes.clear()
            self._autotile_configs.clear()
            self._total_tiles_set = 0
            self._total_brush_paints = 0
            self._total_autotile_applications = 0


def get_tilemap_runtime() -> EngineTileMapRuntime:
    """Return the global EngineTileMapRuntime singleton instance."""
    return EngineTileMapRuntime.get_instance()