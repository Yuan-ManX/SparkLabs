import json
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TileCollisionShape(Enum):
    NONE = "none"
    SQUARE = "square"
    CIRCLE = "circle"
    SLOPE_LEFT = "slope_left"
    SLOPE_RIGHT = "slope_right"
    TRIANGLE = "triangle"
    POLYGON = "polygon"


class TileNavigation(Enum):
    WALKABLE = "walkable"
    OBSTACLE = "obstacle"
    WATER = "water"
    JUMP = "jump"
    CLIMB = "climb"


class TileAnimationMode(Enum):
    NONE = "none"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    RANDOM = "random"


@dataclass
class TileDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    index: int = 0
    name: str = ""
    texture_region: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 0, "h": 0})
    collision: TileCollisionShape = TileCollisionShape.NONE
    navigation: TileNavigation = TileNavigation.WALKABLE
    animation_mode: TileAnimationMode = TileAnimationMode.NONE
    animation_frames: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "index": self.index,
            "name": self.name,
            "texture_region": self.texture_region,
            "collision": self.collision.value,
            "navigation": self.navigation.value,
            "animation_mode": self.animation_mode.value,
            "animation_frames": self.animation_frames,
            "metadata": self.metadata,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TileDefinition":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            index=data.get("index", 0),
            name=data.get("name", ""),
            texture_region=data.get("texture_region", {"x": 0, "y": 0, "w": 0, "h": 0}),
            collision=TileCollisionShape(data.get("collision", "none")),
            navigation=TileNavigation(data.get("navigation", "walkable")),
            animation_mode=TileAnimationMode(data.get("animation_mode", "none")),
            animation_frames=data.get("animation_frames", []),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
        )


@dataclass
class TileSetDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tile_size: int = 32
    texture_path: str = ""
    columns: int = 0
    rows: int = 0
    tiles: Dict[int, TileDefinition] = field(default_factory=dict)
    default_collision: TileCollisionShape = TileCollisionShape.SQUARE
    default_navigation: TileNavigation = TileNavigation.WALKABLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tile_size": self.tile_size,
            "texture_path": self.texture_path,
            "columns": self.columns,
            "rows": self.rows,
            "tiles": {str(k): v.to_dict() for k, v in self.tiles.items()},
            "default_collision": self.default_collision.value,
            "default_navigation": self.default_navigation.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TileSetDefinition":
        tiles_raw = data.get("tiles", {})
        tiles = {}
        for k, v in tiles_raw.items():
            tiles[int(k)] = TileDefinition.from_dict(v)
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", ""),
            tile_size=data.get("tile_size", 32),
            texture_path=data.get("texture_path", ""),
            columns=data.get("columns", 0),
            rows=data.get("rows", 0),
            tiles=tiles,
            default_collision=TileCollisionShape(data.get("default_collision", "square")),
            default_navigation=TileNavigation(data.get("default_navigation", "walkable")),
        )


class TileSetSystem:
    _instance: Optional["TileSetSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._tilesets: Dict[str, TileSetDefinition] = {}
        self._tag_index: Dict[str, Dict[str, Set[int]]] = {}
        self._tileset_count: int = 0
        self._tile_count: int = 0

    @classmethod
    def get_instance(cls) -> "TileSetSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_tileset(
        self,
        name: str,
        tile_size: int = 32,
        texture_path: str = "",
        columns: int = 0,
        rows: int = 0,
        default_collision: TileCollisionShape = TileCollisionShape.SQUARE,
        default_navigation: TileNavigation = TileNavigation.WALKABLE,
    ) -> TileSetDefinition:
        tileset = TileSetDefinition(
            name=name,
            tile_size=tile_size,
            texture_path=texture_path,
            columns=columns,
            rows=rows,
            default_collision=default_collision,
            default_navigation=default_navigation,
        )
        with self._lock:
            self._tilesets[tileset.id] = tileset
            self._tag_index[tileset.id] = {}
            self._tileset_count += 1
        return tileset

    def add_tile(self, tileset_id: str, tile_def: TileDefinition) -> Optional[TileDefinition]:
        with self._lock:
            tileset = self._tilesets.get(tileset_id)
            if tileset is None:
                return None
            region = tile_def.texture_region
            if tile_def.index == 0:
                tile_def.index = self._auto_index(tileset)
            tileset.tiles[tile_def.index] = tile_def
            self._tile_count += 1
            self._index_tags(tileset_id, tile_def)
        return tile_def

    def remove_tile(self, tileset_id: str, tile_index: int) -> bool:
        with self._lock:
            tileset = self._tilesets.get(tileset_id)
            if tileset is None or tile_index not in tileset.tiles:
                return False
            tile = tileset.tiles.pop(tile_index)
            self._tile_count -= 1
            for tag in tile.tags:
                tag_map = self._tag_index.get(tileset_id)
                if tag_map and tag in tag_map:
                    tag_map[tag].discard(tile_index)
            return True

    def get_tile(self, tileset_id: str, tile_index: int) -> Optional[TileDefinition]:
        with self._lock:
            tileset = self._tilesets.get(tileset_id)
            if tileset is None:
                return None
            return tileset.tiles.get(tile_index)

    def get_tileset(self, tileset_id: str) -> Optional[TileSetDefinition]:
        with self._lock:
            return self._tilesets.get(tileset_id)

    def set_tile_collision(
        self, tileset_id: str, tile_index: int, collision: TileCollisionShape
    ) -> bool:
        with self._lock:
            tileset = self._tilesets.get(tileset_id)
            if tileset is None or tile_index not in tileset.tiles:
                return False
            tileset.tiles[tile_index].collision = collision
            return True

    def set_tile_navigation(
        self, tileset_id: str, tile_index: int, navigation: TileNavigation
    ) -> bool:
        with self._lock:
            tileset = self._tilesets.get(tileset_id)
            if tileset is None or tile_index not in tileset.tiles:
                return False
            tileset.tiles[tile_index].navigation = navigation
            return True

    def import_from_spritesheet(
        self,
        name: str,
        texture_path: str,
        tile_size: int,
        columns: int,
        rows: int,
        auto_detect: bool = False,
    ) -> TileSetDefinition:
        tileset = self.create_tileset(
            name=name,
            tile_size=tile_size,
            texture_path=texture_path,
            columns=columns,
            rows=rows,
        )
        total_tiles = columns * rows
        for idx in range(total_tiles):
            col = idx % columns
            row = idx // columns
            tile_def = TileDefinition(
                index=idx,
                name=f"tile_{idx}",
                texture_region={
                    "x": col * tile_size,
                    "y": row * tile_size,
                    "w": tile_size,
                    "h": tile_size,
                },
                collision=tileset.default_collision,
                navigation=tileset.default_navigation,
            )
            self.add_tile(tileset.id, tile_def)

        if auto_detect:
            self.auto_detect_collisions(tileset.id)

        return tileset

    def export_to_json(self, tileset_id: str, filepath: Optional[str] = None) -> Optional[str]:
        with self._lock:
            tileset = self._tilesets.get(tileset_id)
            if tileset is None:
                return None
        json_str = json.dumps(tileset.to_dict(), indent=2, ensure_ascii=False)
        if filepath is not None:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    def get_tiles_by_tag(self, tileset_id: str, tag: str) -> List[TileDefinition]:
        with self._lock:
            tileset = self._tilesets.get(tileset_id)
            if tileset is None:
                return []
            result = []
            for tile in tileset.tiles.values():
                if tag in tile.tags:
                    result.append(tile)
            return result

    def auto_detect_collisions(self, tileset_id: str) -> int:
        with self._lock:
            tileset = self._tilesets.get(tileset_id)
            if tileset is None:
                return 0
            changed = 0
            for tile in tileset.tiles.values():
                if self._is_border_tile(tile, tileset):
                    if tile.collision == TileCollisionShape.NONE:
                        tile.collision = TileCollisionShape.SQUARE
                        changed += 1
                if self._is_empty_tile_name(tile):
                    if tile.collision != TileCollisionShape.NONE:
                        tile.collision = TileCollisionShape.NONE
                        changed += 1
            return changed

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            tileset_names = {tid: ts.name for tid, ts in self._tilesets.items()}
            return {
                "tilesets": self._tileset_count,
                "total_tiles": self._tile_count,
                "tilesets_map": tileset_names,
            }

    def remove_tileset(self, tileset_id: str) -> bool:
        with self._lock:
            if tileset_id not in self._tilesets:
                return False
            tileset = self._tilesets.pop(tileset_id)
            self._tile_count -= len(tileset.tiles)
            self._tileset_count -= 1
            self._tag_index.pop(tileset_id, None)
            return True

    def list_tilesets(self) -> List[TileSetDefinition]:
        with self._lock:
            return list(self._tilesets.values())

    def reset(self) -> None:
        with self._lock:
            self._tilesets.clear()
            self._tag_index.clear()
            self._tileset_count = 0
            self._tile_count = 0

    def _auto_index(self, tileset: TileSetDefinition) -> int:
        if not tileset.tiles:
            return 0
        return max(tileset.tiles.keys()) + 1

    def _index_tags(self, tileset_id: str, tile_def: TileDefinition) -> None:
        tag_map = self._tag_index.setdefault(tileset_id, {})
        for tag in tile_def.tags:
            if tag not in tag_map:
                tag_map[tag] = set()
            tag_map[tag].add(tile_def.index)

    @staticmethod
    def _is_border_tile(tile: TileDefinition, tileset: TileSetDefinition) -> bool:
        col = tile.texture_region.get("x", 0) // tileset.tile_size
        row = tile.texture_region.get("y", 0) // tileset.tile_size
        return col == 0 or row == 0 or col == tileset.columns - 1 or row == tileset.rows - 1

    @staticmethod
    def _is_empty_tile_name(tile: TileDefinition) -> bool:
        empty_patterns = {"empty", "blank", "void", "null", "air", "transparent", "none"}
        name_lower = tile.name.lower().strip()
        return name_lower in empty_patterns


def get_tileset_system() -> TileSetSystem:
    return TileSetSystem.get_instance()