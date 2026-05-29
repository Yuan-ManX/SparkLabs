"""
TileBrush - Singleton system for intelligent tile painting with auto-bordering,
terrain blending, and tile rule matching.

Computes edge tiles based on neighbor analysis for seamless tilemap
transitions in the SparkLabs game engine.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

_time_module = time


class BrushShape(Enum):
    """Tile placement patterns for brush painting operations.

    Determines how tiles are distributed around the brush center position.
    """

    SQUARE = 1
    CIRCLE = 2
    DIAMOND = 3
    LINE = 4
    FLOOD_FILL = 5
    RANDOM_SCATTER = 6


class TileRule(Enum):
    """Rule types for automated tile selection during painting.

    AUTO_BORDER analyzes neighbor tiles and picks the correct edge tile.
    RANDOM_VARIATION picks a random tile from a set for natural variety.
    TERRAIN_BLEND blends between two terrain types at their boundary.
    ELEVATION_MATCH selects tiles based on heightmap comparisons.
    NONE applies no automated rule, using the raw tile index directly.
    """

    AUTO_BORDER = 1
    RANDOM_VARIATION = 2
    TERRAIN_BLEND = 3
    ELEVATION_MATCH = 4
    NONE = 5


class NeighborMode(Enum):
    """Neighbor sampling modes for tile adjacency analysis.

    FOUR_WAY samples cardinal neighbors (N, S, E, W).
    EIGHT_WAY samples cardinal and diagonal neighbors.
    CORNERS_ONLY samples only diagonal neighbors.
    FULL_ADJACENT samples all eight surrounding tiles and their properties.
    """

    FOUR_WAY = 1
    EIGHT_WAY = 2
    CORNERS_ONLY = 3
    FULL_ADJACENT = 4

    def neighbor_offsets(self) -> List[Tuple[int, int]]:
        """Returns the (dx, dy) offset pairs for this neighbor mode."""
        if self == NeighborMode.FOUR_WAY:
            return [(0, -1), (0, 1), (-1, 0), (1, 0)]
        elif self == NeighborMode.EIGHT_WAY:
            return [
                (-1, -1), (0, -1), (1, -1),
                (-1, 0),           (1, 0),
                (-1, 1),  (0, 1),  (1, 1),
            ]
        elif self == NeighborMode.CORNERS_ONLY:
            return [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        elif self == NeighborMode.FULL_ADJACENT:
            return [
                (-1, -1), (0, -1), (1, -1),
                (-1, 0),           (1, 0),
                (-1, 1),  (0, 1),  (1, 1),
            ]
        return []


class BlendMode(Enum):
    """Edge blending strategies for transitions between dissimilar tiles.

    HARD_EDGE places border tiles with no visual blending.
    SMOOTH_BLEND interpolates tile properties at shared edges.
    DITHERED uses a noise pattern to scatter transition tiles.
    GRADIENT computes a gradual blend across multiple tile positions.
    """

    HARD_EDGE = 1
    SMOOTH_BLEND = 2
    DITHERED = 3
    GRADIENT = 4


@dataclass
class TilePlacement:
    """A single tile placed on a tilemap grid.

    Records the exact grid position, tileset reference, layer assignment,
    and optional rule information used to select this tile.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tileset_id: str = ""
    tile_index: int = 0
    grid_x: int = 0
    grid_y: int = 0
    layer: int = 0
    rule_applied: Optional[str] = None
    blend_mode: str = ""
    created_at: float = field(default_factory=_time_module.time)

    @property
    def position(self) -> Tuple[int, int]:
        """Returns the (x, y) grid position of this placement."""
        return (self.grid_x, self.grid_y)

    def to_dict(self) -> dict:
        """Serializes the tile placement to a dictionary."""
        return {
            "id": self.id,
            "tileset_id": self.tileset_id,
            "tile_index": self.tile_index,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "layer": self.layer,
            "rule_applied": self.rule_applied,
            "blend_mode": self.blend_mode,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"TilePlacement(id={self.id[:8]}..., "
            f"pos=({self.grid_x},{self.grid_y}), "
            f"tile={self.tile_index}, layer={self.layer})"
        )


@dataclass
class BrushStroke:
    """A recorded brush operation containing all tiles placed in a single stroke.

    Tracks the brush shape, center position, radius, and all resulting
    tile placements for undo/redo and replay support.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    placements: List[TilePlacement] = field(default_factory=list)
    shape: BrushShape = BrushShape.SQUARE
    center_x: int = 0
    center_y: int = 0
    radius: int = 1
    tilemap_id: str = ""
    layer: int = 0
    created_at: float = field(default_factory=_time_module.time)

    @property
    def tile_count(self) -> int:
        """Number of tiles placed by this brush stroke."""
        return len(self.placements)

    @property
    def bounding_box(self) -> Tuple[int, int, int, int]:
        """Returns (min_x, min_y, max_x, max_y) of all placements in this stroke."""
        if not self.placements:
            return (self.center_x, self.center_y, self.center_x, self.center_y)

        min_x = min(p.grid_x for p in self.placements)
        min_y = min(p.grid_y for p in self.placements)
        max_x = max(p.grid_x for p in self.placements)
        max_y = max(p.grid_y for p in self.placements)
        return (min_x, min_y, max_x, max_y)

    def add_placement(self, placement: TilePlacement) -> None:
        """Appends a tile placement to this brush stroke."""
        self.placements.append(placement)

    def to_dict(self) -> dict:
        """Serializes the brush stroke to a dictionary."""
        return {
            "id": self.id,
            "placements": [p.to_dict() for p in self.placements],
            "shape": self.shape.name,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "radius": self.radius,
            "tilemap_id": self.tilemap_id,
            "layer": self.layer,
            "tile_count": self.tile_count,
            "bounding_box": list(self.bounding_box),
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"BrushStroke(id={self.id[:8]}..., "
            f"shape={self.shape.name}, "
            f"center=({self.center_x},{self.center_y}), "
            f"tiles={self.tile_count})"
        )


@dataclass
class TileRuleConfig:
    """Configuration for an automated tile selection rule.

    Defines a matching pattern based on neighbor tile values, the output
    tile to place when the pattern matches, and a priority for resolving
    conflicting rules at the same position.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ruleset_name: str = ""
    matching_pattern: List[List[int]] = field(default_factory=lambda: [[0, 0, 0], [0, 0, 0], [0, 0, 0]])
    output_tile: int = 0
    priority: int = 0
    rule_type: TileRule = TileRule.AUTO_BORDER
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates the matching pattern dimensions."""
        if not self.matching_pattern:
            raise ValueError("matching_pattern must not be empty")
        pattern_width = len(self.matching_pattern[0]) if self.matching_pattern else 0
        for row in self.matching_pattern:
            if len(row) != pattern_width:
                raise ValueError("matching_pattern rows must have uniform width")
        if not self.ruleset_name:
            self.ruleset_name = f"rule_{self.id[:8]}"

    def matches(self, neighbor_matrix: List[List[int]]) -> bool:
        """Tests whether a 3x3 neighbor matrix matches this rule's pattern.

        A match occurs when every non-zero pattern cell equals the
        corresponding cell in the neighbor matrix. Zero cells in the
        pattern act as wildcards that match any value.
        """
        if len(neighbor_matrix) != 3 or any(len(row) != 3 for row in neighbor_matrix):
            return False

        for py in range(3):
            for px in range(3):
                pattern_val = self.matching_pattern[py][px]
                if pattern_val == 0:
                    continue
                if pattern_val != neighbor_matrix[py][px]:
                    return False
        return True

    def to_dict(self) -> dict:
        """Serializes the tile rule config to a dictionary."""
        return {
            "id": self.id,
            "ruleset_name": self.ruleset_name,
            "matching_pattern": [list(row) for row in self.matching_pattern],
            "output_tile": self.output_tile,
            "priority": self.priority,
            "rule_type": self.rule_type.name,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"TileRuleConfig(id={self.id[:8]}..., "
            f"name={self.ruleset_name}, "
            f"output={self.output_tile}, pri={self.priority})"
        )


class TileBrush:
    """Singleton manager for intelligent tile painting with auto-bordering.

    Maintains tilemap grids, records brush strokes for undo/redo, manages
    tile rule configurations for automated edge matching, and supports
    multiple brush shapes including flood fill.

    Thread-safe via a reentrant lock. Use get_tile_brush() or
    TileBrush.get_instance() to obtain the singleton instance.
    """

    _instance: Optional["TileBrush"] = None
    _lock: threading.RLock = threading.RLock()

    # Default auto-border lookup: encodes which edges are set.
    # Bits: N=1, S=2, E=4, W=8, NE=16, NW=32, SE=64, SW=128
    _BORDER_NORTH: int = 1
    _BORDER_SOUTH: int = 2
    _BORDER_EAST: int = 4
    _BORDER_WEST: int = 8
    _BORDER_NORTHEAST: int = 16
    _BORDER_NORTHWEST: int = 32
    _BORDER_SOUTHEAST: int = 64
    _BORDER_SOUTHWEST: int = 128

    def __new__(cls) -> "TileBrush":
        """Thread-safe singleton construction with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initializes internal state on first construction only."""
        if getattr(self, "_initialized", False):
            return
        self._tilemaps: Dict[str, Dict[Tuple[int, int], TilePlacement]] = {}
        self._tilemap_metadata: Dict[str, dict] = {}
        self._brush_strokes: List[BrushStroke] = []
        self._rule_configs: Dict[str, TileRuleConfig] = {}
        self._stats: Dict[str, int] = {
            "total_placements": 0,
            "total_strokes": 0,
            "total_rules": 0,
            "total_tilemaps": 0,
            "total_auto_borders": 0,
            "total_flood_fills": 0,
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "TileBrush":
        """Returns the singleton TileBrush instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_tilemap_grid(self, tilemap_id: str) -> Dict[Tuple[int, int], TilePlacement]:
        """Retrieves the placement grid for a tilemap, raising if not found.

        Raises:
            KeyError: If no tilemap exists with the given ID.
        """
        if tilemap_id not in self._tilemaps:
            raise KeyError(f"Tilemap '{tilemap_id}' does not exist")
        return self._tilemaps[tilemap_id]

    def _get_tile_at(self, tilemap_id: str, x: int, y: int) -> Optional[TilePlacement]:
        """Returns the tile placement at the given position, or None if empty."""
        grid = self._tilemap_grid(tilemap_id)
        return grid.get((x, y))

    def _tilemap_grid(self, tilemap_id: str) -> Dict[Tuple[int, int], TilePlacement]:
        """Retrieves the placement grid without raising, creating if absent."""
        if tilemap_id not in self._tilemaps:
            self._tilemaps[tilemap_id] = {}
        return self._tilemaps[tilemap_id]

    def _tilemap_meta(self, tilemap_id: str) -> dict:
        """Retrieves tilemap metadata, returning defaults if not set."""
        if tilemap_id not in self._tilemap_metadata:
            self._tilemap_metadata[tilemap_id] = {
                "width": 0,
                "height": 0,
                "tile_size": 32,
            }
        return self._tilemap_metadata[tilemap_id]

    def _is_in_bounds(self, tilemap_id: str, x: int, y: int) -> bool:
        """Checks whether a grid position is within the tilemap boundaries."""
        meta = self._tilemap_meta(tilemap_id)
        width = meta.get("width", 0)
        height = meta.get("height", 0)
        if width <= 0 or height <= 0:
            return False
        return 0 <= x < width and 0 <= y < height

    def _sample_neighbors(
        self,
        tilemap_id: str,
        x: int,
        y: int,
        mode: NeighborMode,
    ) -> Dict[Tuple[int, int], Optional[TilePlacement]]:
        """Samples neighboring tile placements around a center position.

        Returns a dict mapping (dx, dy) offset to the TilePlacement at that
        position, or None if the position is out of bounds or unoccupied.
        """
        grid = self._tilemap_grid(tilemap_id)
        offsets = mode.neighbor_offsets()
        result: Dict[Tuple[int, int], Optional[TilePlacement]] = {}

        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if self._is_in_bounds(tilemap_id, nx, ny):
                result[(dx, dy)] = grid.get((nx, ny))
            else:
                result[(dx, dy)] = None

        return result

    def _build_neighbor_matrix(
        self,
        tilemap_id: str,
        x: int,
        y: int,
    ) -> List[List[int]]:
        """Builds a 3x3 integer matrix from the tile indices surrounding (x, y).

        Each cell contains the tile_index at that neighbor position, or -1
        if the position is empty or out of bounds. The matrix is indexed as
        [row][col] where (0,0) is the top-left neighbor.
        """
        grid = self._tilemap_grid(tilemap_id)
        matrix: List[List[int]] = []

        for dy in (-1, 0, 1):
            row: List[int] = []
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if not self._is_in_bounds(tilemap_id, nx, ny):
                    row.append(-1)
                else:
                    placement = grid.get((nx, ny))
                    row.append(placement.tile_index if placement else -1)
            matrix.append(row)
        return matrix

    def _compute_border_flags(
        self,
        tilemap_id: str,
        x: int,
        y: int,
        tileset_id: str,
    ) -> int:
        """Computes a bitmask indicating which neighbors share the same tileset.

        Only neighbors with the same tileset_id and a nonzero tile_index are
        considered matching. Each matching cardinal or diagonal neighbor
        sets a corresponding bit flag.
        """
        grid = self._tilemap_grid(tilemap_id)
        flags = 0

        neighbor_checks = [
            (0, -1, self._BORDER_NORTH),
            (0, 1, self._BORDER_SOUTH),
            (1, 0, self._BORDER_EAST),
            (-1, 0, self._BORDER_WEST),
            (1, -1, self._BORDER_NORTHEAST),
            (-1, -1, self._BORDER_NORTHWEST),
            (1, 1, self._BORDER_SOUTHEAST),
            (-1, 1, self._BORDER_SOUTHWEST),
        ]

        for dx, dy, flag in neighbor_checks:
            nx, ny = x + dx, y + dy
            if not self._is_in_bounds(tilemap_id, nx, ny):
                continue
            neighbor = grid.get((nx, ny))
            if neighbor and neighbor.tileset_id == tileset_id and neighbor.tile_index > 0:
                flags |= flag

        return flags

    def _resolve_border_tile(self, border_flags: int) -> int:
        """Resolves a border tile index from the neighbor bitmask.

        Maps the bitmask of matching neighbors to a specific tile index
        representing the correct edge piece. The mapping follows a standard
        auto-tiling convention where each unique neighbor configuration
        yields a unique tile index.
        """
        north = bool(border_flags & self._BORDER_NORTH)
        south = bool(border_flags & self._BORDER_SOUTH)
        east = bool(border_flags & self._BORDER_EAST)
        west = bool(border_flags & self._BORDER_WEST)
        ne = bool(border_flags & self._BORDER_NORTHEAST)
        nw = bool(border_flags & self._BORDER_NORTHWEST)
        se = bool(border_flags & self._BORDER_SOUTHEAST)
        sw = bool(border_flags & self._BORDER_SOUTHWEST)

        inner_corner_count = 0
        if north and east and not ne:
            inner_corner_count += 1
        if north and west and not nw:
            inner_corner_count += 1
        if south and east and not se:
            inner_corner_count += 1
        if south and west and not sw:
            inner_corner_count += 1

        neighbor_sum = sum([north, south, east, west])
        if neighbor_sum == 0:
            return 0
        elif neighbor_sum == 4:
            if inner_corner_count == 0:
                return 14
            else:
                return 14 + inner_corner_count
        elif neighbor_sum == 1:
            if north:
                return 8
            elif south:
                return 2
            elif east:
                return 6
            elif west:
                return 4
        elif neighbor_sum == 2:
            if north and south:
                return 5
            elif east and west:
                return 9
            elif north and east:
                return 11
            elif north and west:
                return 10
            elif south and east:
                return 12
            elif south and west:
                return 13
        elif neighbor_sum == 3:
            if not north:
                return 3
            elif not south:
                return 1
            elif not east:
                return 7
            elif not west:
                return 15

        return 0

    def _apply_square_fill(
        self,
        tilemap_id: str,
        center_x: int,
        center_y: int,
        tile_index: int,
        tileset_id: str,
        radius: int,
        layer: int,
    ) -> List[TilePlacement]:
        """Fills a square area centered at (center_x, center_y) with tiles."""
        placements: List[TilePlacement] = []
        meta = self._tilemap_meta(tilemap_id)
        width = meta.get("width", 0)
        height = meta.get("height", 0)

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                gx, gy = center_x + dx, center_y + dy
                if 0 <= gx < width and 0 <= gy < height:
                    placement = self.paint_tile(
                        tilemap_id, gx, gy, tile_index, layer, tileset_id
                    )
                    placements.append(placement)

        return placements

    def _apply_circle_fill(
        self,
        tilemap_id: str,
        center_x: int,
        center_y: int,
        tile_index: int,
        tileset_id: str,
        radius: int,
        layer: int,
    ) -> List[TilePlacement]:
        """Fills a circular area centered at (center_x, center_y) with tiles."""
        placements: List[TilePlacement] = []
        meta = self._tilemap_meta(tilemap_id)
        width = meta.get("width", 0)
        height = meta.get("height", 0)
        r_sq = radius * radius

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy > r_sq:
                    continue
                gx, gy = center_x + dx, center_y + dy
                if 0 <= gx < width and 0 <= gy < height:
                    placement = self.paint_tile(
                        tilemap_id, gx, gy, tile_index, layer, tileset_id
                    )
                    placements.append(placement)

        return placements

    def _apply_diamond_fill(
        self,
        tilemap_id: str,
        center_x: int,
        center_y: int,
        tile_index: int,
        tileset_id: str,
        radius: int,
        layer: int,
    ) -> List[TilePlacement]:
        """Fills a diamond-shaped area centered at (center_x, center_y)."""
        placements: List[TilePlacement] = []
        meta = self._tilemap_meta(tilemap_id)
        width = meta.get("width", 0)
        height = meta.get("height", 0)

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if abs(dx) + abs(dy) > radius:
                    continue
                gx, gy = center_x + dx, center_y + dy
                if 0 <= gx < width and 0 <= gy < height:
                    placement = self.paint_tile(
                        tilemap_id, gx, gy, tile_index, layer, tileset_id
                    )
                    placements.append(placement)

        return placements

    def _apply_line_fill(
        self,
        tilemap_id: str,
        center_x: int,
        center_y: int,
        tile_index: int,
        tileset_id: str,
        radius: int,
        layer: int,
    ) -> List[TilePlacement]:
        """Fills tiles along a horizontal line centered at (center_x, center_y)."""
        placements: List[TilePlacement] = []
        meta = self._tilemap_meta(tilemap_id)
        width = meta.get("width", 0)
        height = meta.get("height", 0)

        for dx in range(-radius, radius + 1):
            gx, gy = center_x + dx, center_y
            if 0 <= gx < width and 0 <= gy < height:
                placement = self.paint_tile(
                    tilemap_id, gx, gy, tile_index, layer, tileset_id
                )
                placements.append(placement)

        return placements

    def _apply_random_scatter(
        self,
        tilemap_id: str,
        center_x: int,
        center_y: int,
        tile_index: int,
        tileset_id: str,
        radius: int,
        layer: int,
    ) -> List[TilePlacement]:
        """Scatters a random subset of tiles within the brush radius."""
        import random

        placements: List[TilePlacement] = []
        meta = self._tilemap_meta(tilemap_id)
        width = meta.get("width", 0)
        height = meta.get("height", 0)
        total_cells = (radius * 2 + 1) * (radius * 2 + 1)

        target_count = max(1, total_cells // 3)

        candidates: List[Tuple[int, int]] = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                gx, gy = center_x + dx, center_y + dy
                if 0 <= gx < width and 0 <= gy < height:
                    candidates.append((gx, gy))

        selected = random.sample(
            candidates, min(target_count, len(candidates))
        )

        for gx, gy in selected:
            placement = self.paint_tile(
                tilemap_id, gx, gy, tile_index, layer, tileset_id
            )
            placements.append(placement)

        return placements

    # ------------------------------------------------------------------
    # Public API: Tilemap management
    # ------------------------------------------------------------------

    def create_tilemap(
        self,
        scene_id: str,
        width: int,
        height: int,
        tile_size: int = 32,
    ) -> str:
        """Creates a new tilemap and returns its unique ID.

        The tilemap is an empty grid of the given dimensions. All tile
        coordinates are zero-indexed grid positions.

        Args:
            scene_id: The scene this tilemap belongs to.
            width: Number of tile columns.
            height: Number of tile rows.
            tile_size: Pixel size of each tile.

        Returns:
            The unique tilemap ID string.

        Raises:
            ValueError: If width or height is not positive.
        """
        if width <= 0:
            raise ValueError("width must be greater than zero")
        if height <= 0:
            raise ValueError("height must be greater than zero")
        if tile_size <= 0:
            raise ValueError("tile_size must be greater than zero")

        tilemap_id = uuid.uuid4().hex

        with self._lock:
            self._tilemaps[tilemap_id] = {}
            self._tilemap_metadata[tilemap_id] = {
                "scene_id": scene_id,
                "width": width,
                "height": height,
                "tile_size": tile_size,
            }
            self._stats["total_tilemaps"] += 1

        return tilemap_id

    def get_tilemap_metadata(self, tilemap_id: str) -> dict:
        """Returns metadata for the given tilemap.

        Args:
            tilemap_id: The tilemap to query.

        Returns:
            A dict with width, height, tile_size, and scene_id.

        Raises:
            KeyError: If the tilemap does not exist.
        """
        with self._lock:
            if tilemap_id not in self._tilemaps:
                raise KeyError(f"Tilemap '{tilemap_id}' does not exist")
            return dict(self._tilemap_meta(tilemap_id))

    def remove_tilemap(self, tilemap_id: str) -> bool:
        """Removes a tilemap and all its tile placements.

        Args:
            tilemap_id: The tilemap to remove.

        Returns:
            True if the tilemap was found and removed, False otherwise.
        """
        with self._lock:
            if tilemap_id in self._tilemaps:
                del self._tilemaps[tilemap_id]
                self._tilemap_metadata.pop(tilemap_id, None)
                self._stats["total_tilemaps"] = max(0, self._stats["total_tilemaps"] - 1)
                return True
            return False

    # ------------------------------------------------------------------
    # Public API: Tile painting
    # ------------------------------------------------------------------

    def paint_tile(
        self,
        tilemap_id: str,
        x: int,
        y: int,
        tile_index: int,
        layer: int = 0,
        tileset_id: str = "",
    ) -> TilePlacement:
        """Places a single tile at the specified grid position.

        Overwrites any existing tile at the same position and layer.

        Args:
            tilemap_id: The target tilemap ID.
            x: Grid column index.
            y: Grid row index.
            tile_index: The tile index within its tileset.
            layer: Rendering layer for depth ordering.
            tileset_id: Identifier for the source tileset.

        Returns:
            The created TilePlacement instance.

        Raises:
            KeyError: If the tilemap does not exist.
            ValueError: If the position is out of bounds.
        """
        tilemap_grid = self._get_tilemap_grid(tilemap_id)

        if not self._is_in_bounds(tilemap_id, x, y):
            meta = self._tilemap_meta(tilemap_id)
            raise ValueError(
                f"Position ({x},{y}) is out of bounds "
                f"[0..{meta.get('width', 0)-1}, 0..{meta.get('height', 0)-1}]"
            )

        placement = TilePlacement(
            tileset_id=tileset_id,
            tile_index=tile_index,
            grid_x=x,
            grid_y=y,
            layer=layer,
        )

        with self._lock:
            tilemap_grid[(x, y)] = placement
            self._stats["total_placements"] += 1

        return placement

    def erase_tile(
        self,
        tilemap_id: str,
        x: int,
        y: int,
    ) -> bool:
        """Erases the tile at the specified grid position.

        Args:
            tilemap_id: The target tilemap ID.
            x: Grid column index.
            y: Grid row index.

        Returns:
            True if a tile was erased, False if the position was already empty.
        """
        tilemap_grid = self._get_tilemap_grid(tilemap_id)

        with self._lock:
            if (x, y) in tilemap_grid:
                del tilemap_grid[(x, y)]
                self._stats["total_placements"] = max(
                    0, self._stats["total_placements"] - 1
                )
                return True
            return False

    def get_tile_at(
        self,
        tilemap_id: str,
        x: int,
        y: int,
    ) -> Optional[TilePlacement]:
        """Returns the tile at the given position, or None.

        Args:
            tilemap_id: The tilemap to query.
            x: Grid column index.
            y: Grid row index.

        Returns:
            The TilePlacement if present, None otherwise.
        """
        with self._lock:
            grid = self._tilemap_grid(tilemap_id)
            return grid.get((x, y))

    # ------------------------------------------------------------------
    # Public API: Brush application
    # ------------------------------------------------------------------

    def apply_brush(
        self,
        tilemap_id: str,
        center_x: int,
        center_y: int,
        shape: BrushShape,
        tile_index: int,
        tileset_id: str = "",
        radius: int = 1,
        layer: int = 0,
    ) -> BrushStroke:
        """Applies a shaped brush stroke to the tilemap.

        Places tiles in the pattern defined by the brush shape, centered
        at the given grid position and extending outward by the radius.

        Args:
            tilemap_id: The target tilemap ID.
            center_x: Center grid column of the brush.
            center_y: Center grid row of the brush.
            shape: The BrushShape pattern to use.
            tile_index: Tile index to place at each position.
            tileset_id: Source tileset identifier.
            radius: Brush extent from center in tile units.
            layer: Rendering layer for all placed tiles.

        Returns:
            A BrushStroke recording all tiles placed.
        """
        # Ensure tilemap exists.
        self._get_tilemap_grid(tilemap_id)

        stroke = BrushStroke(
            shape=shape,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            tilemap_id=tilemap_id,
            layer=layer,
        )

        if shape == BrushShape.FLOOD_FILL:
            # Flood fill is handled separately via flood_fill().
            result = self.flood_fill(tilemap_id, center_x, center_y, tile_index, tileset_id, layer)
            return result

        with self._lock:
            if shape == BrushShape.SQUARE:
                placements = self._apply_square_fill(
                    tilemap_id, center_x, center_y, tile_index,
                    tileset_id, radius, layer,
                )
            elif shape == BrushShape.CIRCLE:
                placements = self._apply_circle_fill(
                    tilemap_id, center_x, center_y, tile_index,
                    tileset_id, radius, layer,
                )
            elif shape == BrushShape.DIAMOND:
                placements = self._apply_diamond_fill(
                    tilemap_id, center_x, center_y, tile_index,
                    tileset_id, radius, layer,
                )
            elif shape == BrushShape.LINE:
                placements = self._apply_line_fill(
                    tilemap_id, center_x, center_y, tile_index,
                    tileset_id, radius, layer,
                )
            elif shape == BrushShape.RANDOM_SCATTER:
                placements = self._apply_random_scatter(
                    tilemap_id, center_x, center_y, tile_index,
                    tileset_id, radius, layer,
                )
            else:
                placements = self._apply_square_fill(
                    tilemap_id, center_x, center_y, tile_index,
                    tileset_id, radius, layer,
                )

            for p in placements:
                stroke.add_placement(p)

            self._brush_strokes.append(stroke)
            self._stats["total_strokes"] += 1

        return stroke

    # ------------------------------------------------------------------
    # Public API: Auto-border
    # ------------------------------------------------------------------

    def auto_border(
        self,
        tilemap_id: str,
        x: int,
        y: int,
        tileset_id: str = "",
        layer: int = 0,
    ) -> TilePlacement:
        """Analyzes neighbors and picks the correct edge tile for the position.

        Computes a border bitmask from surrounding tiles of the same tileset,
        resolves it to an appropriate tile index using the border lookup table,
        and places the resulting tile.

        Args:
            tilemap_id: The target tilemap ID.
            x: Grid column to border-correct.
            y: Grid row to border-correct.
            tileset_id: Filter neighbors by this tileset. If empty, uses the
                tileset of any existing tile at this position.
            layer: Rendering layer for the placement.

        Returns:
            The corrected TilePlacement with the resolved border tile index.

        Raises:
            KeyError: If the tilemap does not exist.
            ValueError: If the position is out of bounds.
        """
        tilemap_grid = self._get_tilemap_grid(tilemap_id)

        if not self._is_in_bounds(tilemap_id, x, y):
            meta = self._tilemap_meta(tilemap_id)
            raise ValueError(
                f"Position ({x},{y}) is out of bounds "
                f"[0..{meta.get('width', 0)-1}, 0..{meta.get('height', 0)-1}]"
            )

        # Infer tileset_id from existing tile if not provided.
        resolved_tileset = tileset_id
        if not resolved_tileset:
            existing = tilemap_grid.get((x, y))
            if existing and existing.tileset_id:
                resolved_tileset = existing.tileset_id

        with self._lock:
            border_flags = self._compute_border_flags(
                tilemap_id, x, y, resolved_tileset
            )
            resolved_index = self._resolve_border_tile(border_flags)

            placement = TilePlacement(
                tileset_id=resolved_tileset,
                tile_index=resolved_index,
                grid_x=x,
                grid_y=y,
                layer=layer,
                rule_applied=TileRule.AUTO_BORDER.name,
            )

            tilemap_grid[(x, y)] = placement
            self._stats["total_placements"] += 1
            self._stats["total_auto_borders"] += 1

        return placement

    def auto_border_region(
        self,
        tilemap_id: str,
        min_x: int,
        min_y: int,
        max_x: int,
        max_y: int,
        tileset_id: str = "",
        layer: int = 0,
    ) -> List[TilePlacement]:
        """Applies auto-border to every tile within a rectangular region.

        Args:
            tilemap_id: The target tilemap ID.
            min_x: Leftmost grid column (inclusive).
            min_y: Topmost grid row (inclusive).
            max_x: Rightmost grid column (inclusive).
            max_y: Bottommost grid row (inclusive).
            tileset_id: Filter neighbors by this tileset.
            layer: Rendering layer for all placements.

        Returns:
            A list of corrected TilePlacement objects.
        """
        results: List[TilePlacement] = []

        for gy in range(min_y, max_y + 1):
            for gx in range(min_x, max_x + 1):
                try:
                    placement = self.auto_border(
                        tilemap_id, gx, gy, tileset_id, layer
                    )
                    results.append(placement)
                except ValueError:
                    continue

        return results

    # ------------------------------------------------------------------
    # Public API: Flood fill
    # ------------------------------------------------------------------

    def flood_fill(
        self,
        tilemap_id: str,
        start_x: int,
        start_y: int,
        tile_index: int,
        tileset_id: str = "",
        layer: int = 0,
    ) -> BrushStroke:
        """Performs a flood fill starting from the given position.

        Replaces all connected tiles matching the start tile with the
        target tile_index. Uses an iterative stack-based algorithm to
        avoid recursion depth limits on large regions.

        Args:
            tilemap_id: The target tilemap ID.
            start_x: Starting grid column.
            start_y: Starting grid row.
            tile_index: Tile index to fill with.
            tileset_id: Source tileset for placed tiles.
            layer: Rendering layer for all placements.

        Returns:
            A BrushStroke recording all filled positions.

        Raises:
            KeyError: If the tilemap does not exist.
            ValueError: If the start position is out of bounds.
        """
        tilemap_grid = self._get_tilemap_grid(tilemap_id)

        if not self._is_in_bounds(tilemap_id, start_x, start_y):
            meta = self._tilemap_meta(tilemap_id)
            raise ValueError(
                f"Start position ({start_x},{start_y}) is out of bounds "
                f"[0..{meta.get('width', 0)-1}, 0..{meta.get('height', 0)-1}]"
            )

        stroke = BrushStroke(
            shape=BrushShape.FLOOD_FILL,
            center_x=start_x,
            center_y=start_y,
            radius=0,
            tilemap_id=tilemap_id,
            layer=layer,
        )

        meta = self._tilemap_meta(tilemap_id)
        width = meta.get("width", 0)
        height = meta.get("height", 0)

        with self._lock:
            start_tile = tilemap_grid.get((start_x, start_y))
            target_index = start_tile.tile_index if start_tile else -1

            # If start tile is already the fill tile, nothing to do.
            if target_index == tile_index and start_tile and start_tile.tileset_id == tileset_id:
                self._brush_strokes.append(stroke)
                self._stats["total_strokes"] += 1
                self._stats["total_flood_fills"] += 1
                return stroke

            stack: List[Tuple[int, int]] = [(start_x, start_y)]
            visited: Set[Tuple[int, int]] = set()

            while stack:
                cx, cy = stack.pop()

                if (cx, cy) in visited:
                    continue
                visited.add((cx, cy))

                if not (0 <= cx < width and 0 <= cy < height):
                    continue

                current = tilemap_grid.get((cx, cy))
                current_index = current.tile_index if current else -1

                if current_index != target_index:
                    continue

                placement = TilePlacement(
                    tileset_id=tileset_id,
                    tile_index=tile_index,
                    grid_x=cx,
                    grid_y=cy,
                    layer=layer,
                )
                tilemap_grid[(cx, cy)] = placement
                self._stats["total_placements"] += 1
                stroke.add_placement(placement)

                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) not in visited and 0 <= nx < width and 0 <= ny < height:
                        stack.append((nx, ny))

            self._brush_strokes.append(stroke)
            self._stats["total_strokes"] += 1
            self._stats["total_flood_fills"] += 1

        return stroke

    # ------------------------------------------------------------------
    # Public API: Rule configuration
    # ------------------------------------------------------------------

    def create_rule(
        self,
        ruleset_name: str,
        matching_pattern: List[List[int]],
        output_tile: int,
        priority: int = 0,
        rule_type: TileRule = TileRule.AUTO_BORDER,
    ) -> TileRuleConfig:
        """Creates and registers a new tile rule configuration.

        Args:
            ruleset_name: Descriptive name for this rule set.
            matching_pattern: 3x3 integer matrix defining neighbor match
                conditions. Zero cells are wildcards.
            output_tile: Tile index to place when the pattern matches.
            priority: Rule priority. Higher values override lower ones.
            rule_type: The TileRule category for this configuration.

        Returns:
            The registered TileRuleConfig instance.

        Raises:
            ValueError: If the matching pattern is invalid.
        """
        config = TileRuleConfig(
            ruleset_name=ruleset_name,
            matching_pattern=matching_pattern,
            output_tile=output_tile,
            priority=priority,
            rule_type=rule_type,
        )

        with self._lock:
            self._rule_configs[config.id] = config
            self._stats["total_rules"] += 1

        return config

    def remove_rule(self, rule_id: str) -> bool:
        """Removes a tile rule configuration by ID.

        Args:
            rule_id: The unique rule ID to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if rule_id in self._rule_configs:
                del self._rule_configs[rule_id]
                self._stats["total_rules"] = max(0, self._stats["total_rules"] - 1)
                return True
            return False

    def get_rule(self, rule_id: str) -> Optional[TileRuleConfig]:
        """Retrieves a tile rule configuration by ID.

        Args:
            rule_id: The unique rule ID.

        Returns:
            The TileRuleConfig if found, None otherwise.
        """
        with self._lock:
            return self._rule_configs.get(rule_id)

    def get_rules_for_tileset(self, ruleset_name: str) -> List[TileRuleConfig]:
        """Returns all rules registered under the given ruleset name.

        Args:
            ruleset_name: The ruleset name to filter by.

        Returns:
            A list of matching TileRuleConfig objects, sorted by priority.
        """
        with self._lock:
            rules = [
                r for r in self._rule_configs.values()
                if r.ruleset_name == ruleset_name
            ]
            rules.sort(key=lambda r: r.priority, reverse=True)
            return rules

    def apply_rules(
        self,
        tilemap_id: str,
        x: int,
        y: int,
        ruleset_name: str,
        layer: int = 0,
    ) -> Optional[TilePlacement]:
        """Applies matching tile rules at a position and returns the placement.

        Builds a neighbor matrix for the position and tests all rules in the
        given ruleset against it. The highest-priority matching rule determines
        the output tile.

        Args:
            tilemap_id: The target tilemap ID.
            x: Grid column.
            y: Grid row.
            ruleset_name: The ruleset to match against.
            layer: Rendering layer for the placement.

        Returns:
            The resulting TilePlacement if a rule matched, None otherwise.
        """
        tilemap_grid = self._get_tilemap_grid(tilemap_id)

        if not self._is_in_bounds(tilemap_id, x, y):
            return None

        rules = self.get_rules_for_tileset(ruleset_name)
        if not rules:
            return None

        with self._lock:
            neighbor_matrix = self._build_neighbor_matrix(tilemap_id, x, y)

            for rule in rules:
                if rule.matches(neighbor_matrix):
                    placement = TilePlacement(
                        tileset_id=ruleset_name,
                        tile_index=rule.output_tile,
                        grid_x=x,
                        grid_y=y,
                        layer=layer,
                        rule_applied=rule.rule_type.name,
                    )
                    tilemap_grid[(x, y)] = placement
                    self._stats["total_placements"] += 1
                    return placement

        return None

    # ------------------------------------------------------------------
    # Public API: Brush stroke history
    # ------------------------------------------------------------------

    def get_strokes(self) -> List[BrushStroke]:
        """Returns all recorded brush strokes.

        Returns:
            A copy of the internal brush stroke list.
        """
        with self._lock:
            return list(self._brush_strokes)

    def get_strokes_for_tilemap(self, tilemap_id: str) -> List[BrushStroke]:
        """Returns all brush strokes recorded for a specific tilemap.

        Args:
            tilemap_id: The tilemap to filter strokes for.

        Returns:
            A list of BrushStroke objects belonging to the tilemap.
        """
        with self._lock:
            return [
                s for s in self._brush_strokes if s.tilemap_id == tilemap_id
            ]

    def clear_strokes(self) -> None:
        """Clears the brush stroke history."""
        with self._lock:
            self._brush_strokes.clear()

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Returns a comprehensive statistics dictionary for monitoring.

        Includes placement and stroke totals, rule counts, tilemap counts,
        and per-tilemap placement breakdowns.

        Returns:
            A dictionary with string keys and numeric/collection values.
        """
        with self._lock:
            total_tiles_placed = sum(
                len(grid) for grid in self._tilemaps.values()
            )

            tilemaps_detail: Dict[str, dict] = {}
            for tmid, grid in self._tilemaps.items():
                meta = self._tilemap_meta(tmid)
                tilemaps_detail[tmid[:8]] = {
                    "width": meta.get("width", 0),
                    "height": meta.get("height", 0),
                    "tile_size": meta.get("tile_size", 0),
                    "placed_tiles": len(grid),
                    "scene_id": meta.get("scene_id", ""),
                }

            return {
                "total_placements": self._stats["total_placements"],
                "total_tiles_in_grids": total_tiles_placed,
                "total_strokes": self._stats["total_strokes"],
                "total_rules": self._stats["total_rules"],
                "total_tilemaps": self._stats["total_tilemaps"],
                "total_auto_borders": self._stats["total_auto_borders"],
                "total_flood_fills": self._stats["total_flood_fills"],
                "brush_strokes_recorded": len(self._brush_strokes),
                "tilemaps_detail": tilemaps_detail,
            }

    # ------------------------------------------------------------------
    # Public API: Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Performs a complete reset of all brush state.

        Clears all tilemaps, strokes, rules, and resets statistics.
        """
        with self._lock:
            self._tilemaps.clear()
            self._tilemap_metadata.clear()
            self._brush_strokes.clear()
            self._rule_configs.clear()
            self._stats = {
                "total_placements": 0,
                "total_strokes": 0,
                "total_rules": 0,
                "total_tilemaps": 0,
                "total_auto_borders": 0,
                "total_flood_fills": 0,
            }

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"TileBrush(tilemaps={len(self._tilemaps)}, "
                f"strokes={len(self._brush_strokes)}, "
                f"rules={len(self._rule_configs)}, "
                f"placements={self._stats['total_placements']})"
            )


def get_tile_brush() -> TileBrush:
    """Module-level accessor for the TileBrush singleton.

    Convenience function that returns the singleton instance without
    needing to reference TileBrush.get_instance() directly.

    Returns:
        The singleton TileBrush instance.
    """
    return TileBrush.get_instance()