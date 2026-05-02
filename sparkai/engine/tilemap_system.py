"""
SparkLabs Engine - Tilemap System

Grid-based tile map rendering and collision management for
AI-generated 2D levels. Supports multi-layer tilemaps with
per-tile properties, auto-tiling rules, and collision shape
generation from tile data.

Architecture:
  TilemapSystem
    |-- TilemapLayer (named layer with tile grid + visibility)
    |-- Tileset (collection of tile definitions with properties)
    |-- Tile (x/y position, tileset index, flip/rotate flags)
    |-- CollisionExtractor (generates AABB colliders from tile data)

Layer Types:
  - ground: walkable terrain tiles
  - wall: blocking collision tiles
  - decoration: visual-only overlay tiles
  - object: interactive entity placement tiles

Usage:
    tm = TilemapSystem(map_width=40, map_height=30, tile_size=32)
    tm.set_tile("ground", 10, 15, tile_id=3)  # grass tile
    tm.set_tile("wall", 20, 15, tile_id=12)    # stone wall
    blocks = tm.get_blocked_cells("wall")
    tm.render_layer("ground", camera_offset=(0, 0))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntFlag
from typing import Any, Dict, List, Optional, Set, Tuple


class TileFlipFlag(IntFlag):
    NONE = 0
    HORIZONTAL = 1
    VERTICAL = 2
    DIAGONAL = 4


@dataclass
class Tile:
    x: int = 0
    y: int = 0
    tile_id: int = -1
    tileset_id: str = ""
    flip: TileFlipFlag = TileFlipFlag.NONE
    rotation: int = 0
    opacity: float = 1.0
    color_mod: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TilesetDefinition:
    tileset_id: str = ""
    name: str = ""
    tile_width: int = 32
    tile_height: int = 32
    columns: int = 8
    tile_count: int = 0
    image_path: str = ""
    tile_properties: Dict[int, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TilemapLayer:
    name: str = ""
    visible: bool = True
    opacity: float = 1.0
    z_order: int = 0
    collision_enabled: bool = False
    tiles: List[List[Optional[Tile]]] = field(default_factory=list)
    parallax: Tuple[float, float] = (1.0, 1.0)
    offset: Tuple[float, float] = (0.0, 0.0)

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < len(self.tiles) and 0 <= y < len(self.tiles[0]):
            return self.tiles[x][y]
        return None


class TilemapSystem:
    """
    Tilemap engine for 2D grid-based levels.

    Manages multiple layers of tiles with per-tile properties,
    collision extraction, and render data generation. Supports
    tileset-based rendering with flip/rotate flags.

    Usage:
        tm = TilemapSystem(50, 40, 32)
        
        # Add a tileset
        ts = tm.add_tileset("dungeon", "dungeon_tiles.png", 32, 32, 8)
        
        # Paint tiles
        tm.set_tile("ground", 10, 15, tile_id=3)
        tm.set_tile("walls", 20, 10, tile_id=12)

        # Get collision data
        for cell in tm.get_layer_cells("walls"):
            if cell[2] is not None:
                add_collider(cell)
    """

    def __init__(
        self,
        map_width: int = 40,
        map_height: int = 30,
        tile_size: int = 32,
    ):
        self._width = map_width
        self._height = map_height
        self._tile_size = tile_size
        self._layers: Dict[str, TilemapLayer] = {}
        self._tilesets: Dict[str, TilesetDefinition] = {}
        self._dirty_cells: Set[Tuple[str, int, int]] = set()

    def add_tileset(
        self,
        tileset_id: str,
        name: str = "",
        image_path: str = "",
        tile_width: int = 32,
        tile_height: int = 32,
        columns: int = 8,
        tile_count: int = 0,
    ) -> TilesetDefinition:
        ts = TilesetDefinition(
            tileset_id=tileset_id,
            name=name or tileset_id,
            image_path=image_path,
            tile_width=tile_width,
            tile_height=tile_height,
            columns=columns,
            tile_count=tile_count or columns * 8,
        )
        self._tilesets[tileset_id] = ts
        return ts

    def remove_tileset(self, tileset_id: str) -> bool:
        return self._tilesets.pop(tileset_id, None) is not None

    def add_layer(
        self,
        name: str,
        z_order: int = 0,
        collision_enabled: bool = False,
        visible: bool = True,
    ) -> TilemapLayer:
        tiles = [[None] * self._height for _ in range(self._width)]
        layer = TilemapLayer(
            name=name,
            tiles=tiles,
            z_order=z_order,
            collision_enabled=collision_enabled,
            visible=visible,
        )
        self._layers[name] = layer
        return layer

    def get_layer(self, name: str) -> Optional[TilemapLayer]:
        return self._layers.get(name)

    def remove_layer(self, name: str) -> bool:
        return self._layers.pop(name, None) is not None

    def get_layer_names(self) -> List[str]:
        return sorted(
            self._layers.keys(),
            key=lambda n: self._layers[n].z_order,
        )

    def set_tile(
        self,
        layer_name: str,
        x: int,
        y: int,
        tile_id: int = -1,
        tileset_id: str = "",
        flip: TileFlipFlag = TileFlipFlag.NONE,
    ) -> bool:
        layer = self._layers.get(layer_name)
        if not layer:
            return False
        if not (0 <= x < self._width and 0 <= y < self._height):
            return False

        if tile_id < 0:
            layer.tiles[x][y] = None
        else:
            layer.tiles[x][y] = Tile(
                x=x, y=y,
                tile_id=tile_id,
                tileset_id=tileset_id,
                flip=flip,
            )
        self._dirty_cells.add((layer_name, x, y))
        return True

    def get_tile(self, layer_name: str, x: int, y: int) -> Optional[Tile]:
        layer = self._layers.get(layer_name)
        if not layer:
            return None
        return layer.get_tile(x, y)

    def fill_area(
        self,
        layer_name: str,
        x1: int, y1: int, x2: int, y2: int,
        tile_id: int,
        tileset_id: str = "",
    ) -> int:
        count = 0
        for x in range(max(0, x1), min(self._width, x2 + 1)):
            for y in range(max(0, y1), min(self._height, y2 + 1)):
                if self.set_tile(layer_name, x, y, tile_id, tileset_id):
                    count += 1
        return count

    def clear_layer(self, layer_name: str) -> int:
        layer = self._layers.get(layer_name)
        if not layer:
            return 0
        count = sum(
            1 for x in range(self._width) for y in range(self._height)
            if layer.tiles[x][y] is not None
        )
        layer.tiles = [[None] * self._height for _ in range(self._width)]
        return count

    def get_blocked_cells(self, layer_name: str) -> List[Tuple[int, int]]:
        layer = self._layers.get(layer_name)
        if not layer or not layer.collision_enabled:
            return []
        return [
            (x, y)
            for x in range(self._width)
            for y in range(self._height)
            if layer.tiles[x][y] is not None
        ]

    def get_layer_cells(
        self, layer_name: str,
    ) -> List[Tuple[int, int, Optional[Tile]]]:
        layer = self._layers.get(layer_name)
        if not layer:
            return []
        return [
            (x, y, layer.tiles[x][y])
            for x in range(self._width) for y in range(self._height)
            if layer.tiles[x][y] is not None
        ]

    def world_to_cell(self, wx: float, wy: float) -> Tuple[int, int]:
        return (int(wx // self._tile_size), int(wy // self._tile_size))

    def cell_to_world(self, cx: int, cy: int) -> Tuple[float, float]:
        return (
            cx * self._tile_size + self._tile_size / 2,
            cy * self._tile_size + self._tile_size / 2,
        )

    def set_tile_size(self, size: int) -> None:
        self._tile_size = max(1, size)

    def resize(self, new_width: int, new_height: int) -> None:
        for layer in self._layers.values():
            old_tiles = layer.tiles
            new_tiles: List[List[Optional[Tile]]] = [
                [None] * new_height for _ in range(new_width)
            ]
            for x in range(min(self._width, new_width)):
                for y in range(min(self._height, new_height)):
                    new_tiles[x][y] = old_tiles[x][y]
            layer.tiles = new_tiles
        self._width = new_width
        self._height = new_height

    def get_stats(self) -> dict:
        total_tiles = sum(
            sum(1 for x in range(self._width) for y in range(self._height)
                if layer.tiles[x][y] is not None)
            for layer in self._layers.values()
        )
        return {
            "map_size": f"{self._width}x{self._height}",
            "tile_size": self._tile_size,
            "layers": len(self._layers),
            "tilesets": len(self._tilesets),
            "total_tiles": total_tiles,
            "dirty_cells": len(self._dirty_cells),
        }

    def clear(self) -> None:
        for layer in self._layers.values():
            layer.tiles = [[None] * self._height for _ in range(self._width)]
        self._dirty_cells.clear()

    def clear_dirty(self) -> None:
        self._dirty_cells.clear()


_global_tilemap_system: Optional[TilemapSystem] = None


def get_tilemap_system() -> TilemapSystem:
    global _global_tilemap_system
    if _global_tilemap_system is None:
        _global_tilemap_system = TilemapSystem()
    return _global_tilemap_system
