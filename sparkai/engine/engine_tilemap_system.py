"""
SparkLabs Engine - Tilemap System

2D grid-based tilemap system with multi-layer support and collision data.
Provides tilemap creation, tileset management, tile painting, object
placement, coordinate conversion, and collision querying for grid-based
game worlds.
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TilemapOrientation(str, Enum):
    """Grid orientation for how tiles are arranged in space."""
    ORTHOGONAL = "orthogonal"
    ISOMETRIC = "isometric"
    STAGGERED = "staggered"
    HEXAGONAL = "hexagonal"


class LayerRenderOrder(str, Enum):
    """Draw order strategy for tiles within a layer."""
    RIGHT_DOWN = "right-down"
    RIGHT_UP = "right-up"
    LEFT_DOWN = "left-down"
    LEFT_UP = "left-up"


class CollisionShape(str, Enum):
    """Collision geometry assigned to a single tile cell."""
    NONE = "none"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    SLOPE_45_UP = "slope-45-up"
    SLOPE_45_DOWN = "slope-45-down"
    PLATFORM = "platform"


class TileFlags(str, Enum):
    """Transform flags applied to individual tile render operations."""
    FLIP_HORIZONTAL = "flip-h"
    FLIP_VERTICAL = "flip-v"
    FLIP_DIAGONAL = "flip-d"
    ROTATE_90 = "rotate-90"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class TilesetTile:
    """Definition of a single tile within a tileset.

    Stores the texture region, collision shape, animation frames,
    and custom properties for one tile index.
    """

    tile_id: int = 0
    tileset_name: str = ""
    texture_rect: Tuple[int, int, int, int] = (0, 0, 32, 32)
    collision_shape: CollisionShape = CollisionShape.NONE
    animation_frames: List[int] = field(default_factory=list)
    animation_duration: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tile_id": self.tile_id,
            "tileset_name": self.tileset_name,
            "texture_rect": list(self.texture_rect),
            "collision_shape": self.collision_shape.value,
            "animation_frames": list(self.animation_frames),
            "animation_duration": self.animation_duration,
            "properties": dict(self.properties),
        }


@dataclass
class Tileset:
    """A collection of tiles extracted from a source texture.

    Defines the grid layout of tiles within a texture atlas along
    with per-tile definitions for collision and animation.
    """

    tileset_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "tileset"
    tile_width: int = 32
    tile_height: int = 32
    image_width: int = 256
    image_height: int = 256
    tile_count: int = 0
    columns: int = 0
    margin: int = 0
    spacing: int = 0
    tiles: Dict[int, TilesetTile] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tileset_id": self.tileset_id,
            "name": self.name,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "tile_count": self.tile_count,
            "columns": self.columns,
            "margin": self.margin,
            "spacing": self.spacing,
            "tiles": {str(k): v.to_dict() for k, v in self.tiles.items()},
        }


@dataclass
class TileCell:
    """A single tile placed on a layer at a grid position.

    References a tileset and local tile ID, with optional transform
    flags and opacity for rendering.
    """

    global_tile_id: int = 0
    tileset_id: str = ""
    local_tile_id: int = 0
    flags: List[TileFlags] = field(default_factory=list)
    opacity: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "global_tile_id": self.global_tile_id,
            "tileset_id": self.tileset_id,
            "local_tile_id": self.local_tile_id,
            "flags": [f.value for f in self.flags],
            "opacity": self.opacity,
        }


@dataclass
class TileLayer:
    """A grid plane within a tilemap holding tile cell data.

    Supports visibility toggling, opacity, z-order depth sorting,
    parallax scrolling factors, and per-layer locking for editing.
    """

    layer_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "layer"
    width: int = 0
    height: int = 0
    visible: bool = True
    opacity: float = 1.0
    z_order: int = 0
    parallax_x: float = 1.0
    parallax_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    locked: bool = False
    cells: Dict[int, Dict[int, TileCell]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        cell_dict: Dict[str, Any] = {}
        for x, col in self.cells.items():
            for y, cell in col.items():
                key = f"{x},{y}"
                cell_dict[key] = cell.to_dict()
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "visible": self.visible,
            "opacity": self.opacity,
            "z_order": self.z_order,
            "parallax_x": self.parallax_x,
            "parallax_y": self.parallax_y,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "locked": self.locked,
            "cells": cell_dict,
        }


@dataclass
class TilemapObject:
    """An object placed on an object layer within a tilemap.

    Supports rectangular, elliptical, polygonal, polyline, point,
    and text object types with transform and visibility properties.
    """

    object_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "object"
    obj_type: str = "rectangle"
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0
    visible: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "obj_type": self.obj_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "visible": self.visible,
            "properties": dict(self.properties),
        }


@dataclass
class ObjectLayer:
    """A layer holding free-form objects placed within a tilemap.

    Objects are not constrained to the tile grid and may have
    arbitrary positions, sizes, and shapes.
    """

    layer_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "objects"
    visible: bool = True
    opacity: float = 1.0
    z_order: int = 10
    objects: List[TilemapObject] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "z_order": self.z_order,
            "objects": [o.to_dict() for o in self.objects],
        }


@dataclass
class Tilemap:
    """A complete tilemap composed of tile layers and object layers.

    Represents a full grid-based game world with configurable
    orientation, render order, tile dimensions, and background color.
    """

    tilemap_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "tilemap"
    orientation: TilemapOrientation = TilemapOrientation.ORTHOGONAL
    render_order: LayerRenderOrder = LayerRenderOrder.RIGHT_DOWN
    width: int = 0
    height: int = 0
    tile_width: int = 32
    tile_height: int = 32
    infinite: bool = False
    background_color: Tuple[int, int, int, int] = (0, 0, 0, 0)
    layers: List[TileLayer] = field(default_factory=list)
    object_layers: List[ObjectLayer] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tilemap_id": self.tilemap_id,
            "name": self.name,
            "orientation": self.orientation.value,
            "render_order": self.render_order.value,
            "width": self.width,
            "height": self.height,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "infinite": self.infinite,
            "background_color": list(self.background_color),
            "layers": [layer.to_dict() for layer in self.layers],
            "object_layers": [ol.to_dict() for ol in self.object_layers],
        }


# ---------------------------------------------------------------------------
# EngineTilemapSystem — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class EngineTilemapSystem:
    """2D grid-based tilemap system with multi-layer support and collision data.

    Manages tilemap creation, tileset registration, tile painting, object
    placement, coordinate conversion, and collision querying. All tilemap
    data is stored in-memory and accessible through the singleton instance.

    Usage:
        system = get_tilemap_system()
        tilemap = system.create_tilemap("overworld", 64, 48)
        tileset = system.create_tileset("terrain", 32, 32, 256, 256)
        system.set_tile(tilemap.tilemap_id, tilemap.layers[0].layer_id,
                        10, 10, 1, tileset.tileset_id)
        pos = system.tile_to_world(tilemap.tilemap_id, 10, 10)
    """

    _instance: Optional["EngineTilemapSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineTilemapSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineTilemapSystem":
        return cls()

    def _initialize(self) -> None:
        self._tilemaps: Dict[str, Tilemap] = {}
        self._tilesets: Dict[str, Tileset] = {}
        self._creation_counter: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_map(self, tilemap_id: str) -> Tilemap:
        _time_module.sleep(0.001)
        if tilemap_id not in self._tilemaps:
            raise KeyError(f"Tilemap '{tilemap_id}' does not exist")
        return self._tilemaps[tilemap_id]

    def _get_tile_layer(
        self, tilemap_id: str, layer_id: str
    ) -> TileLayer:
        _time_module.sleep(0.001)
        tilemap = self._get_map(tilemap_id)
        for layer in tilemap.layers:
            if layer.layer_id == layer_id:
                return layer
        raise KeyError(
            f"Tile layer '{layer_id}' not found in tilemap '{tilemap_id}'"
        )

    def _get_object_layer(
        self, tilemap_id: str, object_layer_id: str
    ) -> ObjectLayer:
        _time_module.sleep(0.001)
        tilemap = self._get_map(tilemap_id)
        for layer in tilemap.object_layers:
            if layer.layer_id == object_layer_id:
                return layer
        raise KeyError(
            f"Object layer '{object_layer_id}' not found in tilemap '{tilemap_id}'"
        )

    def _is_tile_in_bounds(self, layer: TileLayer, x: int, y: int) -> bool:
        _time_module.sleep(0.001)
        return 0 <= x < layer.width and 0 <= y < layer.height

    def _ensure_tileset(
        self, tileset_id: str
    ) -> Tileset:
        _time_module.sleep(0.001)
        if tileset_id not in self._tilesets:
            raise KeyError(f"Tileset '{tileset_id}' does not exist")
        return self._tilesets[tileset_id]

    # ------------------------------------------------------------------
    # Tilemap management
    # ------------------------------------------------------------------

    def create_tilemap(
        self,
        name: str,
        width: int,
        height: int,
        tile_width: int = 32,
        tile_height: int = 32,
        orientation: TilemapOrientation = TilemapOrientation.ORTHOGONAL,
    ) -> Tilemap:
        _time_module.sleep(0.001)
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        if tile_width <= 0 or tile_height <= 0:
            raise ValueError("tile_width and tile_height must be positive")

        self._creation_counter += 1

        tilemap = Tilemap(
            name=name,
            orientation=orientation,
            width=width,
            height=height,
            tile_width=tile_width,
            tile_height=tile_height,
        )

        # Initialize with one empty tile layer
        default_tile_layer = TileLayer(
            name=f"{name}_tiles",
            width=width,
            height=height,
            z_order=0,
        )
        tilemap.layers.append(default_tile_layer)

        # Initialize with one empty object layer
        default_object_layer = ObjectLayer(
            name=f"{name}_objects",
            z_order=10,
        )
        tilemap.object_layers.append(default_object_layer)

        self._tilemaps[tilemap.tilemap_id] = tilemap
        return tilemap

    # ------------------------------------------------------------------
    # Tileset management
    # ------------------------------------------------------------------

    def create_tileset(
        self,
        name: str,
        tile_width: int,
        tile_height: int,
        image_width: int,
        image_height: int,
        margin: int = 0,
        spacing: int = 0,
    ) -> Tileset:
        _time_module.sleep(0.001)
        if tile_width <= 0 or tile_height <= 0:
            raise ValueError("tile_width and tile_height must be positive")
        if image_width <= 0 or image_height <= 0:
            raise ValueError("image_width and image_height must be positive")

        columns = (image_width - 2 * margin + spacing) // (tile_width + spacing)
        if columns <= 0:
            columns = 1
        rows = (image_height - 2 * margin + spacing) // (tile_height + spacing)
        if rows <= 0:
            rows = 1
        tile_count = columns * rows

        tileset = Tileset(
            name=name,
            tile_width=tile_width,
            tile_height=tile_height,
            image_width=image_width,
            image_height=image_height,
            tile_count=tile_count,
            columns=columns,
            margin=margin,
            spacing=spacing,
        )
        self._tilesets[tileset.tileset_id] = tileset
        return tileset

    def add_tile_to_tileset(
        self,
        tileset_id: str,
        tile_id: int,
        tileset_name: str,
        texture_rect: Optional[Tuple[int, int, int, int]] = None,
        collision_shape: CollisionShape = CollisionShape.NONE,
    ) -> bool:
        _time_module.sleep(0.001)
        tileset = self._tilesets.get(tileset_id)
        if tileset is None:
            return False

        if tile_id < 0:
            return False

        if texture_rect is None:
            col = tile_id % max(tileset.columns, 1)
            row = tile_id // max(tileset.columns, 1)
            x = tileset.margin + col * (tileset.tile_width + tileset.spacing)
            y = tileset.margin + row * (tileset.tile_height + tileset.spacing)
            texture_rect = (x, y, tileset.tile_width, tileset.tile_height)

        tile = TilesetTile(
            tile_id=tile_id,
            tileset_name=tileset_name,
            texture_rect=texture_rect,
            collision_shape=collision_shape,
        )
        tileset.tiles[tile_id] = tile

        if tile_id >= tileset.tile_count:
            tileset.tile_count = tile_id + 1

        return True

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def add_layer(
        self,
        tilemap_id: str,
        name: str,
        z_order: Optional[int] = None,
    ) -> Optional[TileLayer]:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return None

        if z_order is None:
            z_order = len(tilemap.layers)

        layer = TileLayer(
            name=name,
            width=tilemap.width,
            height=tilemap.height,
            z_order=z_order,
        )
        tilemap.layers.append(layer)
        return layer

    def add_object_layer(
        self,
        tilemap_id: str,
        name: str,
        z_order: Optional[int] = None,
    ) -> Optional[ObjectLayer]:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return None

        if z_order is None:
            z_order = len(tilemap.object_layers) + 10

        object_layer = ObjectLayer(
            name=name,
            z_order=z_order,
        )
        tilemap.object_layers.append(object_layer)
        return object_layer

    # ------------------------------------------------------------------
    # Tile operations
    # ------------------------------------------------------------------

    def set_tile(
        self,
        tilemap_id: str,
        layer_id: str,
        x: int,
        y: int,
        global_tile_id: int,
        tileset_id: str = "",
        flags: Optional[List[TileFlags]] = None,
    ) -> bool:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return False

        layer = None
        for l in tilemap.layers:
            if l.layer_id == layer_id:
                layer = l
                break

        if layer is None:
            return False

        if not self._is_tile_in_bounds(layer, x, y):
            return False

        if global_tile_id == 0:
            # Clear the tile
            if x in layer.cells and y in layer.cells[x]:
                del layer.cells[x][y]
                if not layer.cells[x]:
                    del layer.cells[x]
            return True

        local_tile_id = global_tile_id - 1

        cell = TileCell(
            global_tile_id=global_tile_id,
            tileset_id=tileset_id,
            local_tile_id=local_tile_id,
            flags=flags if flags is not None else [],
            opacity=1.0,
        )

        if x not in layer.cells:
            layer.cells[x] = {}
        layer.cells[x][y] = cell
        return True

    def get_tile(
        self,
        tilemap_id: str,
        layer_id: str,
        x: int,
        y: int,
    ) -> Optional[TileCell]:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return None

        for layer in tilemap.layers:
            if layer.layer_id == layer_id:
                if x in layer.cells and y in layer.cells[x]:
                    return layer.cells[x][y]
                return None
        return None

    def fill_rect(
        self,
        tilemap_id: str,
        layer_id: str,
        x: int,
        y: int,
        w: int,
        h: int,
        global_tile_id: int,
        tileset_id: str = "",
    ) -> int:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return 0

        layer = None
        for l in tilemap.layers:
            if l.layer_id == layer_id:
                layer = l
                break

        if layer is None:
            return 0

        count = 0
        for dy in range(h):
            for dx in range(w):
                gx, gy = x + dx, y + dy
                if self.set_tile(
                    tilemap_id, layer_id, gx, gy,
                    global_tile_id, tileset_id,
                ):
                    count += 1

        return count

    def clear_layer(
        self,
        tilemap_id: str,
        layer_id: str,
    ) -> int:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return 0

        for layer in tilemap.layers:
            if layer.layer_id == layer_id:
                cleared = sum(
                    len(col) for col in layer.cells.values()
                )
                layer.cells.clear()
                return cleared
        return 0

    # ------------------------------------------------------------------
    # Object operations
    # ------------------------------------------------------------------

    def add_tilemap_object(
        self,
        tilemap_id: str,
        object_layer_id: str,
        name: str,
        obj_type: str,
        x: float,
        y: float,
        width: float = 0.0,
        height: float = 0.0,
    ) -> Optional[TilemapObject]:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return None

        for layer in tilemap.object_layers:
            if layer.layer_id == object_layer_id:
                tilemap_obj = TilemapObject(
                    name=name,
                    obj_type=obj_type,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                )
                layer.objects.append(tilemap_obj)
                return tilemap_obj
        return None

    # ------------------------------------------------------------------
    # Collision querying
    # ------------------------------------------------------------------

    def get_collision_tiles(
        self,
        tilemap_id: str,
        layer_id: str,
    ) -> List[Tuple[int, int, CollisionShape]]:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return []

        result: List[Tuple[int, int, CollisionShape]] = []

        for layer in tilemap.layers:
            if layer.layer_id != layer_id:
                continue
            for x, col in layer.cells.items():
                for y, cell in col.items():
                    if not cell.tileset_id:
                        continue
                    tileset = self._tilesets.get(cell.tileset_id)
                    if tileset is None:
                        continue
                    tile_def = tileset.tiles.get(cell.local_tile_id)
                    if tile_def is None:
                        continue
                    if tile_def.collision_shape != CollisionShape.NONE:
                        result.append((x, y, tile_def.collision_shape))

        return result

    def check_collision_at(
        self,
        tilemap_id: str,
        layer_id: str,
        x: int,
        y: int,
    ) -> Optional[CollisionShape]:
        _time_module.sleep(0.001)
        cell = self.get_tile(tilemap_id, layer_id, x, y)
        if cell is None or not cell.tileset_id:
            return None

        tileset = self._tilesets.get(cell.tileset_id)
        if tileset is None:
            return None

        tile_def = tileset.tiles.get(cell.local_tile_id)
        if tile_def is None:
            return None

        if tile_def.collision_shape == CollisionShape.NONE:
            return None

        return tile_def.collision_shape

    # ------------------------------------------------------------------
    # Coordinate conversion
    # ------------------------------------------------------------------

    def world_to_tile(
        self,
        tilemap_id: str,
        world_x: float,
        world_y: float,
    ) -> Tuple[int, int]:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None or tilemap.tile_width <= 0 or tilemap.tile_height <= 0:
            return (0, 0)

        tile_x = int(math.floor(world_x / tilemap.tile_width))
        tile_y = int(math.floor(world_y / tilemap.tile_height))
        return (tile_x, tile_y)

    def tile_to_world(
        self,
        tilemap_id: str,
        tile_x: int,
        tile_y: int,
    ) -> Tuple[float, float]:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return (0.0, 0.0)

        world_x = (tile_x + 0.5) * tilemap.tile_width
        world_y = (tile_y + 0.5) * tilemap.tile_height
        return (world_x, world_y)

    # ------------------------------------------------------------------
    # Tilemap modification
    # ------------------------------------------------------------------

    def resize_tilemap(
        self,
        tilemap_id: str,
        new_width: int,
        new_height: int,
    ) -> bool:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return False

        if new_width <= 0 or new_height <= 0:
            return False

        tilemap.width = new_width
        tilemap.height = new_height

        for layer in tilemap.layers:
            layer.width = new_width
            layer.height = new_height
            # Remove cells that are now out of bounds
            cols_to_remove: List[int] = []
            for x, col in layer.cells.items():
                if x >= new_width:
                    cols_to_remove.append(x)
                else:
                    rows_to_remove: List[int] = []
                    for y in col.keys():
                        if y >= new_height:
                            rows_to_remove.append(y)
                    for y in rows_to_remove:
                        del col[y]
            for x in cols_to_remove:
                del layer.cells[x]

        return True

    def set_layer_visibility(
        self,
        tilemap_id: str,
        layer_id: str,
        visible: bool,
    ) -> bool:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return False

        for layer in tilemap.layers:
            if layer.layer_id == layer_id:
                layer.visible = visible
                return True

        for layer in tilemap.object_layers:
            if layer.layer_id == layer_id:
                layer.visible = visible
                return True

        return False

    def set_layer_opacity(
        self,
        tilemap_id: str,
        layer_id: str,
        opacity: float,
    ) -> bool:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return False

        clamped = max(0.0, min(1.0, opacity))

        for layer in tilemap.layers:
            if layer.layer_id == layer_id:
                layer.opacity = clamped
                return True

        for layer in tilemap.object_layers:
            if layer.layer_id == layer_id:
                layer.opacity = clamped
                return True

        return False

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_tilemap_stats(
        self,
        tilemap_id: str,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        tilemap = self._tilemaps.get(tilemap_id)
        if tilemap is None:
            return {
                "error": f"Tilemap '{tilemap_id}' not found",
                "total_tiles_set": 0,
                "layer_count": 0,
                "object_count": 0,
                "collision_tiles": 0,
                "memory_estimate_kb": 0,
            }

        total_tiles_set = 0
        collision_tiles = 0
        for layer in tilemap.layers:
            for col in layer.cells.values():
                total_tiles_set += len(col)
                for cell in col.values():
                    if not cell.tileset_id:
                        continue
                    ts = self._tilesets.get(cell.tileset_id)
                    if ts is not None:
                        td = ts.tiles.get(cell.local_tile_id)
                        if td is not None and td.collision_shape != CollisionShape.NONE:
                            collision_tiles += 1

        object_count = sum(
            len(ol.objects) for ol in tilemap.object_layers
        )
        layer_count = len(tilemap.layers)
        object_layer_count = len(tilemap.object_layers)

        # Rough memory estimate: 256 bytes per cell, 128 bytes per object
        cell_memory = total_tiles_set * 256
        object_memory = object_count * 128
        struct_memory = (
            layer_count * 512
            + object_layer_count * 256
            + 1024
        )
        memory_estimate_kb = (cell_memory + object_memory + struct_memory) // 1024

        return {
            "total_tiles_set": total_tiles_set,
            "layer_count": layer_count,
            "object_count": object_count,
            "collision_tiles": collision_tiles,
            "memory_estimate_kb": memory_estimate_kb,
        }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_tilemap_system() -> EngineTilemapSystem:
    """Return the global EngineTilemapSystem singleton instance."""
    return EngineTilemapSystem.get_instance()