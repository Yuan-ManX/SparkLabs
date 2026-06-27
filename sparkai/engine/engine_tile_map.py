"""
SparkLabs Engine - Tile Map System

Comprehensive tile map system for creating grid-based 2D game worlds.
Provides layered tile maps with AI-driven auto-tiling, procedural generation,
and runtime editing capabilities. Integrates with the agent layer for
intelligent level design and procedural content generation.

Architecture:
  TileMapEngine (Singleton)
    |-- TileMap (complete tile-based world with layers)
    |-- TileLayer (individual layer with tiles and properties)
    |-- TileSet (collection of tile definitions with rules)
    |-- TileBrush (painting tool for tile placement)
    |-- TileRule (auto-tiling and adjacency rules)
    |-- TileGenerator (procedural tile map generation)

Tile Features:
  - Multi-layer tile maps with independent rendering
  - Auto-tiling with adjacency rules and bitmask patterns
  - Tile animation with frame-based animation support
  - Collision shapes per tile for physics integration
  - Tile properties for custom data and game logic
  - Procedural generation with noise and rule-based algorithms

Usage:
    tm = get_tile_map_engine()
    tm.initialize()

    # Create a tile map
    tilemap = tm.create_map("level_1", 100, 50, tile_size=32)

    # Add a layer
    tm.add_layer("level_1", "ground", layer_type=TileLayerType.TILE)

    # Paint tiles
    tm.paint_tiles("level_1", "ground", [(10, 5, "grass"), (11, 5, "grass")])

    # Generate procedural map
    tm.generate_map("level_1", algorithm="perlin", config={"seed": 42})
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class TileLayerType(Enum):
    """Types of tile layers."""
    TILE = "tile"              # Standard tile layer
    OBJECT = "object"          # Object placement layer
    COLLISION = "collision"    # Collision-only layer
    DECORATION = "decoration"  # Decoration overlay layer
    BACKGROUND = "background"  # Parallax background layer
    FOREGROUND = "foreground"  # Foreground overlay layer


class TileRenderOrder(Enum):
    """Render order for tile layers."""
    RIGHT_DOWN = "right_down"    # Left to right, top to bottom
    RIGHT_UP = "right_up"        # Left to right, bottom to top
    LEFT_DOWN = "left_down"      # Right to left, top to bottom
    LEFT_UP = "left_up"          # Right to left, bottom to top


class TileCollisionShape(Enum):
    """Collision shapes for tiles."""
    NONE = "none"
    FULL = "full"          # Full tile collision
    TOP_HALF = "top_half"
    BOTTOM_HALF = "bottom_half"
    LEFT_HALF = "left_half"
    RIGHT_HALF = "right_half"
    SLOPE_LEFT = "slope_left"
    SLOPE_RIGHT = "slope_right"
    CUSTOM = "custom"


class TileAnimationMode(Enum):
    """Animation modes for tiles."""
    NONE = "none"
    LOOP = "loop"          # Continuous loop
    PING_PONG = "ping_pong"  # Forward then reverse
    ONCE = "once"          # Play once and stop
    RANDOM = "random"      # Random frame selection


class AutoTileRule(Enum):
    """Auto-tiling adjacency rules."""
    NONE = "none"
    BITMASK_4 = "bitmask_4"    # 4-direction adjacency
    BITMASK_8 = "bitmask_8"    # 8-direction adjacency
    CORNER = "corner"           # Corner-based adjacency
    EDGE = "edge"               # Edge-based adjacency


class GenerationAlgorithm(Enum):
    """Algorithms for procedural tile map generation."""
    PERLIN = "perlin"           # Perlin noise based
    CELLULAR = "cellular"       # Cellular automata
    BSP = "bsp"                 # Binary space partition
    DRUNKARD_WALK = "drunkard"  # Random walk
    WAVE_FUNCTION = "wave"      # Wave function collapse
    TEMPLATE = "template"       # Template-based generation


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TileDefinition:
    """Definition of a single tile type."""
    tile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    texture_id: str = ""
    collision_shape: TileCollisionShape = TileCollisionShape.NONE
    animation_mode: TileAnimationMode = TileAnimationMode.NONE
    animation_frames: List[str] = field(default_factory=list)
    animation_speed: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    auto_tile_rule: AutoTileRule = AutoTileRule.NONE
    auto_tile_bitmask: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tile_id": self.tile_id,
            "name": self.name,
            "texture_id": self.texture_id,
            "collision_shape": self.collision_shape.value,
            "animation_mode": self.animation_mode.value,
            "animation_frames": self.animation_frames,
            "animation_speed": self.animation_speed,
            "properties": self.properties,
            "auto_tile_rule": self.auto_tile_rule.value,
            "tags": self.tags,
        }


@dataclass
class TileCell:
    """A single tile cell in a layer."""
    x: int = 0
    y: int = 0
    tile_id: str = ""
    flip_x: bool = False
    flip_y: bool = False
    rotation: int = 0  # 0, 90, 180, 270
    opacity: float = 1.0
    tint: Tuple[int, int, int, int] = (255, 255, 255, 255)
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "tile_id": self.tile_id,
            "flip_x": self.flip_x,
            "flip_y": self.flip_y,
            "rotation": self.rotation,
            "opacity": self.opacity,
            "tint": list(self.tint),
            "properties": self.properties,
        }


@dataclass
class TileLayer:
    """A layer within a tile map."""
    layer_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    layer_type: TileLayerType = TileLayerType.TILE
    width: int = 0
    height: int = 0
    tiles: Dict[Tuple[int, int], TileCell] = field(default_factory=dict)
    visible: bool = True
    opacity: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    parallax_factor: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    z_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "layer_type": self.layer_type.value,
            "width": self.width,
            "height": self.height,
            "tile_count": len(self.tiles),
            "visible": self.visible,
            "opacity": self.opacity,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "parallax_factor": self.parallax_factor,
            "properties": self.properties,
            "z_index": self.z_index,
        }

    def get_tile(self, x: int, y: int) -> Optional[TileCell]:
        """Get the tile at the specified position."""
        return self.tiles.get((x, y))

    def set_tile(self, x: int, y: int, tile_id: str) -> None:
        """Set a tile at the specified position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[(x, y)] = TileCell(x=x, y=y, tile_id=tile_id)

    def remove_tile(self, x: int, y: int) -> None:
        """Remove a tile at the specified position."""
        self.tiles.pop((x, y), None)


@dataclass
class TileSet:
    """Collection of tile definitions."""
    tileset_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    tile_size: int = 32
    tile_definitions: Dict[str, TileDefinition] = field(default_factory=dict)
    texture_path: str = ""
    columns: int = 0
    rows: int = 0
    margin: int = 0
    spacing: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tileset_id": self.tileset_id,
            "name": self.name,
            "tile_size": self.tile_size,
            "tile_count": len(self.tile_definitions),
            "texture_path": self.texture_path,
            "columns": self.columns,
            "rows": self.rows,
            "properties": self.properties,
        }


@dataclass
class TileMap:
    """Complete tile-based game world."""
    map_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    width: int = 0
    height: int = 0
    tile_size: int = 32
    layers: Dict[str, TileLayer] = field(default_factory=dict)
    tilesets: Dict[str, TileSet] = field(default_factory=dict)
    render_order: TileRenderOrder = TileRenderOrder.RIGHT_DOWN
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "map_id": self.map_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tile_size": self.tile_size,
            "layer_count": len(self.layers),
            "layer_names": list(self.layers.keys()),
            "tileset_count": len(self.tilesets),
            "render_order": self.render_order.value,
            "properties": self.properties,
            "created_at": self.created_at,
        }


@dataclass
class TileBrush:
    """A painting tool for tile placement."""
    brush_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    tiles: List[Tuple[int, int, str]] = field(default_factory=list)
    size: int = 1
    random_mode: bool = False
    auto_tile: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brush_id": self.brush_id,
            "name": self.name,
            "tile_count": len(self.tiles),
            "size": self.size,
            "random_mode": self.random_mode,
            "auto_tile": self.auto_tile,
        }


# =============================================================================
# TileMapEngine (Singleton)
# =============================================================================


class TileMapEngine:
    """Comprehensive tile map system for grid-based 2D game worlds.

    Provides layered tile maps with AI-driven auto-tiling, procedural
    generation, and runtime editing. Integrates with the agent layer
    for intelligent level design.

    Usage:
        tm = TileMapEngine.get_instance()
        tm.initialize()

        tilemap = tm.create_map("level_1", 100, 50, 32)
        tm.add_layer("level_1", "ground", TileLayerType.TILE)
        tm.paint_tiles("level_1", "ground", [(10, 5, "grass")])
    """

    _instance: Optional["TileMapEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if TileMapEngine._instance is not None:
            raise RuntimeError("Use TileMapEngine.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()
        self._maps: Dict[str, TileMap] = {}
        self._tilesets: Dict[str, TileSet] = {}
        self._brushes: Dict[str, TileBrush] = {}
        self._generation_history: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "TileMapEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            self._register_default_tilesets()
            self._register_default_brushes()
            self._initialized = True

            return {
                "status": "initialized",
                "success": True,
                "tilesets": len(self._tilesets),
                "brushes": len(self._brushes),
            }

    def shutdown(self) -> Dict[str, Any]:
        with self._lock:
            self._initialized = False
            return {"success": True, "maps_cleared": len(self._maps)}

    def _register_default_tilesets(self) -> None:
        """Register default tilesets."""
        default = TileSet(
            name="default",
            tile_size=32,
            columns=16,
            rows=16,
        )

        # Add default tile definitions
        default_tiles = {
            "empty": TileDefinition(name="empty"),
            "grass": TileDefinition(name="grass", collision_shape=TileCollisionShape.NONE,
                                    tags=["terrain", "walkable"]),
            "dirt": TileDefinition(name="dirt", collision_shape=TileCollisionShape.NONE,
                                   tags=["terrain", "walkable"]),
            "stone": TileDefinition(name="stone", collision_shape=TileCollisionShape.FULL,
                                    tags=["terrain", "solid"]),
            "water": TileDefinition(name="water", collision_shape=TileCollisionShape.FULL,
                                    tags=["terrain", "liquid"]),
            "sand": TileDefinition(name="sand", collision_shape=TileCollisionShape.NONE,
                                   tags=["terrain", "walkable"]),
            "wall_top": TileDefinition(name="wall_top", collision_shape=TileCollisionShape.FULL,
                                       tags=["structure", "solid"]),
            "wall_side": TileDefinition(name="wall_side", collision_shape=TileCollisionShape.FULL,
                                        tags=["structure", "solid"]),
            "platform": TileDefinition(name="platform", collision_shape=TileCollisionShape.TOP_HALF,
                                       tags=["structure", "platform"]),
            "ladder": TileDefinition(name="ladder", collision_shape=TileCollisionShape.NONE,
                                     tags=["structure", "climbable"]),
            "spike": TileDefinition(name="spike", collision_shape=TileCollisionShape.FULL,
                                    tags=["hazard", "damage"]),
        }

        for tid, tdef in default_tiles.items():
            default.tile_definitions[tid] = tdef

        self._tilesets["default"] = default

    def _register_default_brushes(self) -> None:
        """Register default painting brushes."""
        self._brushes["single"] = TileBrush(name="single", size=1)
        self._brushes["3x3"] = TileBrush(name="3x3", size=3)
        self._brushes["5x5"] = TileBrush(name="5x5", size=5)

    # -------------------------------------------------------------------------
    # Map Management
    # -------------------------------------------------------------------------

    def create_map(self, name: str, width: int, height: int,
                   tile_size: int = 32) -> Dict[str, Any]:
        """Create a new tile map."""
        with self._lock:
            tilemap = TileMap(
                name=name,
                width=width,
                height=height,
                tile_size=tile_size,
            )
            self._maps[name] = tilemap
            return {"success": True, "map": tilemap.to_dict()}

    def get_map(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tile map by name."""
        tilemap = self._maps.get(name)
        return tilemap.to_dict() if tilemap else None

    def list_maps(self) -> List[Dict[str, Any]]:
        """List all tile maps."""
        return [m.to_dict() for m in self._maps.values()]

    def delete_map(self, name: str) -> Dict[str, Any]:
        """Delete a tile map."""
        with self._lock:
            if name not in self._maps:
                return {"success": False, "error": f"Map '{name}' not found"}
            del self._maps[name]
            return {"success": True, "name": name}

    # -------------------------------------------------------------------------
    # Layer Management
    # -------------------------------------------------------------------------

    def add_layer(self, map_name: str, layer_name: str,
                  layer_type: TileLayerType = TileLayerType.TILE,
                  z_index: Optional[int] = None) -> Dict[str, Any]:
        """Add a layer to a tile map."""
        with self._lock:
            tilemap = self._maps.get(map_name)
            if not tilemap:
                return {"success": False, "error": f"Map '{map_name}' not found"}

            if layer_name in tilemap.layers:
                return {"success": False, "error": f"Layer '{layer_name}' already exists"}

            zi = z_index if z_index is not None else len(tilemap.layers)
            layer = TileLayer(
                name=layer_name,
                layer_type=layer_type,
                width=tilemap.width,
                height=tilemap.height,
                z_index=zi,
            )
            tilemap.layers[layer_name] = layer
            return {"success": True, "layer": layer.to_dict()}

    def get_layer(self, map_name: str, layer_name: str) -> Optional[Dict[str, Any]]:
        """Get a layer by name."""
        tilemap = self._maps.get(map_name)
        if tilemap:
            layer = tilemap.layers.get(layer_name)
            return layer.to_dict() if layer else None
        return None

    def remove_layer(self, map_name: str, layer_name: str) -> Dict[str, Any]:
        """Remove a layer from a tile map."""
        with self._lock:
            tilemap = self._maps.get(map_name)
            if not tilemap:
                return {"success": False, "error": f"Map '{map_name}' not found"}

            if layer_name not in tilemap.layers:
                return {"success": False, "error": f"Layer '{layer_name}' not found"}

            del tilemap.layers[layer_name]
            return {"success": True, "map_name": map_name, "layer_name": layer_name}

    # -------------------------------------------------------------------------
    # Tile Painting
    # -------------------------------------------------------------------------

    def paint_tiles(self, map_name: str, layer_name: str,
                    tiles: List[Tuple[int, int, str]]) -> Dict[str, Any]:
        """Paint tiles onto a layer."""
        with self._lock:
            tilemap = self._maps.get(map_name)
            if not tilemap:
                return {"success": False, "error": f"Map '{map_name}' not found"}

            layer = tilemap.layers.get(layer_name)
            if not layer:
                return {"success": False, "error": f"Layer '{layer_name}' not found"}

            painted = 0
            for x, y, tile_id in tiles:
                if 0 <= x < layer.width and 0 <= y < layer.height:
                    layer.set_tile(x, y, tile_id)
                    painted += 1

            return {"success": True, "painted": painted, "total": len(tiles)}

    def paint_region(self, map_name: str, layer_name: str,
                     x: int, y: int, width: int, height: int,
                     tile_id: str) -> Dict[str, Any]:
        """Fill a rectangular region with tiles."""
        tiles = []
        for dx in range(width):
            for dy in range(height):
                tiles.append((x + dx, y + dy, tile_id))
        return self.paint_tiles(map_name, layer_name, tiles)

    def erase_tiles(self, map_name: str, layer_name: str,
                    positions: List[Tuple[int, int]]) -> Dict[str, Any]:
        """Erase tiles from a layer."""
        with self._lock:
            tilemap = self._maps.get(map_name)
            if not tilemap:
                return {"success": False, "error": f"Map '{map_name}' not found"}

            layer = tilemap.layers.get(layer_name)
            if not layer:
                return {"success": False, "error": f"Layer '{layer_name}' not found"}

            erased = 0
            for x, y in positions:
                if (x, y) in layer.tiles:
                    layer.remove_tile(x, y)
                    erased += 1

            return {"success": True, "erased": erased, "total": len(positions)}

    def get_tiles_in_region(self, map_name: str, layer_name: str,
                            x: int, y: int, width: int, height: int) -> Dict[str, Any]:
        """Get all tiles in a rectangular region."""
        tilemap = self._maps.get(map_name)
        if not tilemap:
            return {"success": False, "error": f"Map '{map_name}' not found"}

        layer = tilemap.layers.get(layer_name)
        if not layer:
            return {"success": False, "error": f"Layer '{layer_name}' not found"}

        tiles = []
        for dx in range(width):
            for dy in range(height):
                tile = layer.get_tile(x + dx, y + dy)
                if tile:
                    tiles.append(tile.to_dict())

        return {"success": True, "tiles": tiles, "count": len(tiles)}

    # -------------------------------------------------------------------------
    # Tileset Management
    # -------------------------------------------------------------------------

    def register_tileset(self, tileset: TileSet) -> Dict[str, Any]:
        """Register a tileset."""
        with self._lock:
            if tileset.name in self._tilesets:
                return {"success": False, "error": f"Tileset '{tileset.name}' already exists"}
            self._tilesets[tileset.name] = tileset
            return {"success": True, "tileset": tileset.to_dict()}

    def get_tileset(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tileset by name."""
        ts = self._tilesets.get(name)
        return ts.to_dict() if ts else None

    def list_tilesets(self) -> List[Dict[str, Any]]:
        """List all registered tilesets."""
        return [ts.to_dict() for ts in self._tilesets.values()]

    # -------------------------------------------------------------------------
    # Brush Management
    # -------------------------------------------------------------------------

    def create_brush(self, name: str, size: int = 1,
                     tiles: Optional[List[Tuple[int, int, str]]] = None) -> Dict[str, Any]:
        """Create a custom tile brush."""
        with self._lock:
            brush = TileBrush(
                name=name,
                size=size,
                tiles=tiles or [],
            )
            self._brushes[name] = brush
            return {"success": True, "brush": brush.to_dict()}

    # -------------------------------------------------------------------------
    # Procedural Generation
    # -------------------------------------------------------------------------

    def generate_map(self, map_name: str,
                     algorithm: GenerationAlgorithm = GenerationAlgorithm.PERLIN,
                     config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a tile map procedurally."""
        tilemap = self._maps.get(map_name)
        if not tilemap:
            return {"success": False, "error": f"Map '{map_name}' not found"}

        cfg = config or {}
        seed = cfg.get("seed", random.randint(0, 1000000))
        random.seed(seed)

        # Ensure a ground layer exists
        if "ground" not in tilemap.layers:
            self.add_layer(map_name, "ground", TileLayerType.TILE, 0)

        layer = tilemap.layers["ground"]

        generators = {
            GenerationAlgorithm.PERLIN: self._generate_perlin,
            GenerationAlgorithm.CELLULAR: self._generate_cellular,
            GenerationAlgorithm.DRUNKARD_WALK: self._generate_drunkard_walk,
        }

        generator = generators.get(algorithm, self._generate_perlin)
        tiles = generator(tilemap.width, tilemap.height, cfg)

        # Paint generated tiles
        self.paint_tiles(map_name, "ground", tiles)

        record = {
            "map_name": map_name,
            "algorithm": algorithm.value,
            "seed": seed,
            "tiles_generated": len(tiles),
            "timestamp": time.time(),
        }
        self._generation_history.append(record)

        return {"success": True, "generation": record}

    def _generate_perlin(self, width: int, height: int,
                         config: Dict[str, Any]) -> List[Tuple[int, int, str]]:
        """Generate tile map using Perlin-like noise."""
        scale = config.get("scale", 0.1)
        tiles = []

        for x in range(width):
            for y in range(height):
                # Simple noise approximation using sine waves
                noise = (
                    math.sin(x * scale) * math.cos(y * scale) +
                    math.sin(x * scale * 2.5) * math.cos(y * scale * 2.5) * 0.5 +
                    math.sin(x * scale * 5.0 + y * scale * 3.0) * 0.25
                )
                noise = (noise + 1.5) / 3.0  # Normalize to 0-1

                if noise < 0.3:
                    tile_id = "water"
                elif noise < 0.4:
                    tile_id = "sand"
                elif noise < 0.7:
                    tile_id = "grass"
                elif noise < 0.85:
                    tile_id = "dirt"
                else:
                    tile_id = "stone"

                tiles.append((x, y, tile_id))

        return tiles

    def _generate_cellular(self, width: int, height: int,
                           config: Dict[str, Any]) -> List[Tuple[int, int, str]]:
        """Generate tile map using cellular automata."""
        density = config.get("density", 0.45)
        iterations = config.get("iterations", 4)

        # Initialize random grid
        grid = [[random.random() < density for _ in range(width)] for _ in range(height)]

        # Run cellular automata
        for _ in range(iterations):
            new_grid = [[False for _ in range(width)] for _ in range(height)]
            for x in range(width):
                for y in range(height):
                    neighbors = sum(
                        1 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if (dx, dy) != (0, 0) and
                        0 <= x + dx < width and 0 <= y + dy < height and
                        grid[y + dy][x + dx]
                    )
                    new_grid[y][x] = neighbors > 4 or (grid[y][x] and neighbors >= 4)
            grid = new_grid

        # Convert to tiles
        tiles = []
        for x in range(width):
            for y in range(height):
                tile_id = "stone" if grid[y][x] else "grass"
                tiles.append((x, y, tile_id))

        return tiles

    def _generate_drunkard_walk(self, width: int, height: int,
                                 config: Dict[str, Any]) -> List[Tuple[int, int, str]]:
        """Generate tile map using drunkard's walk algorithm."""
        steps = config.get("steps", width * height // 3)
        start_x = width // 2
        start_y = height // 2

        # Initialize with walls
        grid = [["stone" for _ in range(width)] for _ in range(height)]

        x, y = start_x, start_y
        for _ in range(steps):
            grid[y][x] = "grass"  # Carve path
            # Also carve a small area around
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        grid[ny][nx] = "grass"

            # Random walk
            direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
            x = max(0, min(width - 1, x + direction[0]))
            y = max(0, min(height - 1, y + direction[1]))

        # Convert to tile list
        tiles = []
        for cy in range(height):
            for cx in range(width):
                if grid[cy][cx] != "stone":
                    tiles.append((cx, cy, grid[cy][cx]))

        return tiles

    # -------------------------------------------------------------------------
    # Auto-Tiling
    # -------------------------------------------------------------------------

    def auto_tile(self, map_name: str, layer_name: str) -> Dict[str, Any]:
        """Apply auto-tiling rules to a layer."""
        tilemap = self._maps.get(map_name)
        if not tilemap:
            return {"success": False, "error": f"Map '{map_name}' not found"}

        layer = tilemap.layers.get(layer_name)
        if not layer:
            return {"success": False, "error": f"Layer '{layer_name}' not found"}

        updated = 0
        for (x, y), cell in list(layer.tiles.items()):
            # Simple 4-direction adjacency check
            neighbors = 0
            if layer.get_tile(x, y - 1): neighbors |= 1  # Top
            if layer.get_tile(x + 1, y): neighbors |= 2  # Right
            if layer.get_tile(x, y + 1): neighbors |= 4  # Bottom
            if layer.get_tile(x - 1, y): neighbors |= 8  # Left

            # Store bitmask for rendering
            cell.properties["auto_tile_bitmask"] = neighbors
            updated += 1

        return {"success": True, "tiles_updated": updated}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        with self._lock:
            total_tiles = sum(
                sum(len(layer.tiles) for layer in tilemap.layers.values())
                for tilemap in self._maps.values()
            )
            return {
                "initialized": self._initialized,
                "maps": len(self._maps),
                "tilesets": len(self._tilesets),
                "brushes": len(self._brushes),
                "total_tiles": total_tiles,
                "generations": len(self._generation_history),
            }

    def get_generation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get procedural generation history."""
        return self._generation_history[-limit:]


# ── Module Accessor ──

def get_tile_map_engine() -> TileMapEngine:
    """Get the singleton tile map engine instance."""
    return TileMapEngine.get_instance()