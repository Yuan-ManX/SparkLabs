"""
SparkLabs Engine - Tile Map Optimizer

Large tile map rendering optimizer providing spatial chunk partitioning,
viewport-aware culling, auto-tiling rule application, texture atlas
generation, and level-of-detail management. Designed for maps with
hundreds of thousands of tiles rendered efficiently.

Architecture:
  TileMapOptimizer
    |-- TileMap (grid-based tile layout with orientation and layer stack)
    |-- TileLayer (depth-sorted tile planes with opacity and blending)
    |-- OptimizationChunk (coherent tile subregions for batch rendering)
    |-- AutoTileBrush (pattern-matching rules for contextual tile placement)
    |-- DrawCall (batched geometry submission with material and bounds)
"""
from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class TileMapOrientation(Enum):
    ORTHOGONAL = "orthogonal"
    ISOMETRIC = "isometric"
    HEXAGONAL = "hexagonal"
    STAGGERED = "staggered"


class CullingMode(Enum):
    VIEWPORT = "viewport"
    EXTENDED = "extended"
    NONE = "none"
    FRUSTUM = "frustum"


class ChunkRenderMode(Enum):
    BATCHED = "batched"
    INSTANCED = "instanced"
    ATLAS = "atlas"


class AutoTilingRule(Enum):
    CORNER = "corner"
    EDGE = "edge"
    CENTER = "center"
    RANDOM = "random"


@dataclass
class TileMap:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    width: int = 0
    height: int = 0
    tile_size: int = 32
    orientation: TileMapOrientation = TileMapOrientation.ORTHOGONAL
    layers: Dict[str, TileLayer] = field(default_factory=dict)
    chunks: List[OptimizationChunk] = field(default_factory=list)
    culling_mode: CullingMode = CullingMode.VIEWPORT
    chunk_size: int = 16
    total_tiles_set: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "width": self.width, "height": self.height,
            "tile_size": self.tile_size,
            "orientation": self.orientation.value,
            "layer_count": len(self.layers),
            "chunk_count": len(self.chunks),
            "culling_mode": self.culling_mode.value,
            "chunk_size": self.chunk_size,
            "total_tiles_set": self.total_tiles_set,
            "created_at": self.created_at,
        }


@dataclass
class TileLayer:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    depth: int = 0
    opacity: float = 1.0
    visible: bool = True
    tiles: Dict[Tuple[int, int], int] = field(default_factory=dict)
    is_collision_layer: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "depth": self.depth,
            "opacity": round(self.opacity, 2), "visible": self.visible,
            "tile_count": len(self.tiles),
            "is_collision_layer": self.is_collision_layer,
        }


@dataclass
class OptimizationChunk:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    map_id: str = ""
    start_x: int = 0
    start_y: int = 0
    end_x: int = 0
    end_y: int = 0
    render_mode: ChunkRenderMode = ChunkRenderMode.BATCHED
    visible: bool = True
    tile_count: int = 0
    lod_level: int = 0
    is_dirty: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "map_id": self.map_id,
            "start_x": self.start_x, "start_y": self.start_y,
            "end_x": self.end_x, "end_y": self.end_y,
            "render_mode": self.render_mode.value,
            "visible": self.visible, "tile_count": self.tile_count,
            "lod_level": self.lod_level, "is_dirty": self.is_dirty,
        }


@dataclass
class AutoTileBrush:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    rule_type: AutoTilingRule = AutoTilingRule.CORNER
    match_pattern: List[Tuple[int, int]] = field(default_factory=list)
    output_tile: int = 0
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "rule_type": self.rule_type.value,
            "match_pattern": self.match_pattern,
            "output_tile": self.output_tile,
            "priority": self.priority,
        }


@dataclass
class DrawCall:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    map_id: str = ""
    layer_name: str = ""
    chunk_index: int = 0
    vertex_count: int = 0
    triangle_count: int = 0
    material_name: str = "default_tile_material"
    estimated_batch_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "map_id": self.map_id,
            "layer_name": self.layer_name,
            "chunk_index": self.chunk_index,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "material_name": self.material_name,
            "estimated_batch_size": self.estimated_batch_size,
        }


class TileMapOptimizer:
    """Large tile map rendering optimizer with chunking and culling."""

    _instance: Optional["TileMapOptimizer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._maps: Dict[str, TileMap] = {}
        self._brushes: Dict[str, AutoTileBrush] = {}
        self._draw_calls: Dict[str, DrawCall] = {}
        self._atlas_cache: Dict[str, Dict[str, Any]] = {}
        self._nav_meshes: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def get_instance(cls) -> "TileMapOptimizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Map Management ----

    def create_map(self, name: str, width: int, height: int,
                   tile_size: int = 32,
                   orientation: str = "orthogonal") -> TileMap:
        try:
            o = TileMapOrientation(orientation.lower())
        except ValueError:
            o = TileMapOrientation.ORTHOGONAL
        tile_map = TileMap(name=name, width=max(1, width),
                           height=max(1, height),
                           tile_size=max(1, tile_size), orientation=o)
        self._maps[tile_map.id] = tile_map
        return tile_map

    def add_layer(self, map_id: str, name: str, depth: int = 0,
                  opacity: float = 1.0) -> Optional[TileLayer]:
        tile_map = self._maps.get(map_id)
        if tile_map is None:
            return None
        layer = TileLayer(name=name, depth=depth,
                          opacity=max(0.0, min(1.0, opacity)))
        tile_map.layers[layer.id] = layer
        return layer

    # ---- Tile Operations ----

    def set_tile(self, map_id: str, layer_id: str,
                 x: int, y: int, tile_id: int) -> bool:
        tile_map = self._maps.get(map_id)
        if tile_map is None:
            return False
        layer = tile_map.layers.get(layer_id)
        if layer is None:
            return False
        if x < 0 or x >= tile_map.width or y < 0 or y >= tile_map.height:
            return False
        prev = layer.tiles.get((x, y))
        layer.tiles[(x, y)] = tile_id
        if prev is None and tile_id >= 0:
            tile_map.total_tiles_set += 1
        elif prev is not None and tile_id < 0:
            tile_map.total_tiles_set = max(0, tile_map.total_tiles_set - 1)
        for chunk in tile_map.chunks:
            if chunk.start_x <= x <= chunk.end_x and chunk.start_y <= y <= chunk.end_y:
                chunk.is_dirty = True
                chunk.tile_count = self._count_chunk_tiles(tile_map, chunk)
                break
        return True

    def fill_region(self, map_id: str, layer_id: str,
                    x1: int, y1: int, x2: int, y2: int,
                    tile_id: int) -> int:
        tile_map = self._maps.get(map_id)
        if tile_map is None or layer_id not in tile_map.layers:
            return 0
        sx, ex = sorted([max(0, min(x1, tile_map.width - 1)),
                         max(0, min(x2, tile_map.width - 1))])
        sy, ey = sorted([max(0, min(y1, tile_map.height - 1)),
                         max(0, min(y2, tile_map.height - 1))])
        count = 0
        for y in range(sy, ey + 1):
            for x in range(sx, ex + 1):
                if self.set_tile(map_id, layer_id, x, y, tile_id):
                    count += 1
        return count

    # ---- Auto-Tiling ----

    def define_auto_tile_rule(self, name: str,
                               match_pattern: List[Tuple[int, int]],
                               output_tile: int,
                               rule_type: str = "corner") -> AutoTileBrush:
        try:
            rt = AutoTilingRule(rule_type.lower())
        except ValueError:
            rt = AutoTilingRule.CORNER
        brush = AutoTileBrush(
            name=name, rule_type=rt,
            match_pattern=[(int(p[0]), int(p[1])) for p in match_pattern],
            output_tile=output_tile, priority=len(self._brushes))
        self._brushes[brush.id] = brush
        return brush

    def apply_auto_tile(self, map_id: str, layer_id: str,
                        brush_id: str) -> int:
        tile_map = self._maps.get(map_id)
        if tile_map is None:
            return 0
        layer = tile_map.layers.get(layer_id)
        if layer is None:
            return 0
        brush = self._brushes.get(brush_id)
        if brush is None:
            return 0
        modifications = 0
        for (x, y), existing in list(layer.tiles.items()):
            if self._match_rule(tile_map, layer, x, y, brush):
                layer.tiles[(x, y)] = brush.output_tile
                modifications += 1
        if modifications > 0:
            for chunk in tile_map.chunks:
                chunk.is_dirty = True
        return modifications

    def _match_rule(self, tile_map: TileMap, layer: TileLayer,
                    cx: int, cy: int, brush: AutoTileBrush) -> bool:
        if brush.rule_type == AutoTilingRule.CORNER:
            corners = [layer.tiles.get((cx + dx, cy + dy))
                       for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]]
            return sum(1 for c in corners if c is not None and c != brush.output_tile) >= 2
        elif brush.rule_type == AutoTilingRule.EDGE:
            edges = [layer.tiles.get((cx + dx, cy + dy))
                     for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]]
            return sum(1 for e in edges if e is not None and e != brush.output_tile) >= 1
        elif brush.rule_type == AutoTilingRule.CENTER:
            center = layer.tiles.get((cx, cy))
            return center is not None and center != brush.output_tile
        elif brush.rule_type == AutoTilingRule.RANDOM:
            import random
            return random.random() > 0.5
        return True

    # ---- Chunk Partitioning ----

    def partition_chunks(self, map_id: str, chunk_size: int = 16) -> int:
        tile_map = self._maps.get(map_id)
        if tile_map is None:
            return 0
        tile_map.chunks.clear()
        tile_map.chunk_size = max(4, chunk_size)
        cols = math.ceil(tile_map.width / tile_map.chunk_size)
        rows = math.ceil(tile_map.height / tile_map.chunk_size)
        for row in range(rows):
            for col in range(cols):
                sx = col * tile_map.chunk_size
                sy = row * tile_map.chunk_size
                ex = min(sx + tile_map.chunk_size - 1, tile_map.width - 1)
                ey = min(sy + tile_map.chunk_size - 1, tile_map.height - 1)
                chunk = OptimizationChunk(map_id=map_id, start_x=sx, start_y=sy,
                                          end_x=ex, end_y=ey)
                chunk.tile_count = self._count_chunk_tiles(tile_map, chunk)
                tile_map.chunks.append(chunk)
        return len(tile_map.chunks)

    def _count_chunk_tiles(self, tile_map: TileMap,
                           chunk: OptimizationChunk) -> int:
        return sum(1 for l in tile_map.layers.values()
                   for y in range(chunk.start_y, chunk.end_y + 1)
                   for x in range(chunk.start_x, chunk.end_x + 1)
                   if (x, y) in l.tiles)

    # ---- Culling ----

    def cull_chunks(self, map_id: str,
                    viewport_bounds: Dict[str, float]) -> int:
        tile_map = self._maps.get(map_id)
        if tile_map is None:
            return 0
        if tile_map.culling_mode == CullingMode.NONE:
            for chunk in tile_map.chunks:
                chunk.visible = True
            return len(tile_map.chunks)
        vx = viewport_bounds.get("x", 0.0)
        vy = viewport_bounds.get("y", 0.0)
        vw = viewport_bounds.get("width", 800.0)
        vh = viewport_bounds.get("height", 600.0)
        margin = viewport_bounds.get("margin", 0.0)
        if tile_map.culling_mode == CullingMode.EXTENDED:
            margin = max(margin, tile_map.chunk_size * tile_map.tile_size * 1.5)
        min_vx, max_vx = vx - margin, vx + vw + margin
        min_vy, max_vy = vy - margin, vy + vh + margin
        ts = tile_map.tile_size
        visible = 0
        for chunk in tile_map.chunks:
            cmx = chunk.start_x * ts
            cmy = chunk.start_y * ts
            cMx = (chunk.end_x + 1) * ts
            cMy = (chunk.end_y + 1) * ts
            chunk.visible = not (
                cMx < min_vx or cmx > max_vx
                or cMy < min_vy or cmy > max_vy)
            if chunk.visible:
                visible += 1
        return visible

    # ---- Atlas Optimization ----

    def optimize_atlas(self, map_id: str) -> Dict[str, Any]:
        tile_map = self._maps.get(map_id)
        if tile_map is None:
            return {"error": "Map not found", "success": False}
        unique: Set[int] = set()
        for layer in tile_map.layers.values():
            for tid in layer.tiles.values():
                if tid >= 0:
                    unique.add(tid)
        sorted_tiles = sorted(unique)
        count = len(sorted_tiles)
        cols = math.ceil(math.sqrt(count)) if count > 0 else 1
        rows = math.ceil(count / cols) if cols > 0 else 1
        atlas_id = uuid.uuid4().hex
        atlas = {
            "atlas_id": atlas_id, "map_id": map_id,
            "tile_count": count, "grid_cols": cols, "grid_rows": rows,
            "tile_size": tile_map.tile_size, "uv_mappings": {},
            "total_pixels": cols * rows * tile_map.tile_size * tile_map.tile_size}
        for idx, tid in enumerate(sorted_tiles):
            col, row = idx % cols, idx // cols
            atlas["uv_mappings"][str(tid)] = {
                "u0": round(col / cols, 6), "v0": round(row / rows, 6),
                "u1": round((col + 1) / cols, 6), "v1": round((row + 1) / rows, 6)}
        self._atlas_cache[map_id] = atlas
        return {"success": True, "atlas": atlas}

    # ---- Draw Call Estimation ----

    def estimate_draw_calls(self, map_id: str) -> Dict[str, Any]:
        tile_map = self._maps.get(map_id)
        if tile_map is None:
            return {"error": "Map not found"}
        if not tile_map.chunks:
            self.partition_chunks(map_id, tile_map.chunk_size)
        dcs: List[Dict[str, Any]] = []
        total_v, total_t = 0, 0
        for idx, chunk in enumerate(tile_map.chunks):
            if not chunk.visible or chunk.tile_count == 0:
                continue
            for layer in tile_map.layers.values():
                if not layer.visible:
                    continue
                tile_ids = [layer.tiles.get((x, y), -1)
                            for y in range(chunk.start_y, chunk.end_y + 1)
                            for x in range(chunk.start_x, chunk.end_x + 1)
                            if layer.tiles.get((x, y), -1) >= 0]
                if not tile_ids:
                    continue
                verts = len(tile_ids) * 4
                tris = len(tile_ids) * 2
                dc = DrawCall(map_id=map_id, layer_name=layer.name,
                              chunk_index=idx, vertex_count=verts,
                              triangle_count=tris,
                              estimated_batch_size=len(tile_ids))
                self._draw_calls[dc.id] = dc
                dcs.append(dc.to_dict())
                total_v += verts
                total_t += tris
        return {"map_id": map_id, "map_name": tile_map.name,
                "total_draw_calls": len(dcs),
                "total_vertices": total_v, "total_triangles": total_t,
                "visible_chunks": sum(1 for c in tile_map.chunks if c.visible),
                "total_chunks": len(tile_map.chunks), "batched_draws": dcs}

    # ---- Nav Mesh Generation ----

    def generate_nav_mesh_from_layers(self, map_id: str,
                                       layer_ids: Optional[List[str]] = None
                                       ) -> List[Dict[str, Any]]:
        tile_map = self._maps.get(map_id)
        if tile_map is None:
            return []
        target_layers = ([tile_map.layers[lid] for lid in layer_ids
                          if lid in tile_map.layers] if layer_ids
                         else [l for l in tile_map.layers.values()
                               if l.is_collision_layer])
        if not target_layers:
            return []
        blocked: Set[Tuple[int, int]] = set()
        for layer in target_layers:
            for (tx, ty), tid in layer.tiles.items():
                if tid >= 0:
                    blocked.add((tx, ty))
        nav_regions: List[Dict[str, Any]] = []
        visited: Set[Tuple[int, int]] = set()
        ts = tile_map.tile_size
        for y in range(tile_map.height):
            for x in range(tile_map.width):
                if (x, y) in visited or (x, y) in blocked:
                    continue
                region = self._flood_fill(x, y, tile_map.width, tile_map.height, blocked)
                visited.update(region)
                if region:
                    mx = min(t[0] for t in region)
                    Mx = max(t[0] for t in region)
                    my = min(t[1] for t in region)
                    My = max(t[1] for t in region)
                    nav_regions.append({
                        "id": uuid.uuid4().hex, "map_id": map_id,
                        "bounds": {"x": mx * ts, "y": my * ts,
                                   "width": (Mx - mx + 1) * ts,
                                   "height": (My - my + 1) * ts},
                        "tile_count": len(region), "walkable": True,
                        "origin": {"x": mx, "y": my}})
        self._nav_meshes[map_id] = nav_regions
        return nav_regions

    def _flood_fill(self, sx: int, sy: int, max_w: int, max_h: int,
                    blocked: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
        region: Set[Tuple[int, int]] = set()
        stack = [(sx, sy)]
        dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in region:
                continue
            if cx < 0 or cx >= max_w or cy < 0 or cy >= max_h:
                continue
            if (cx, cy) in blocked:
                continue
            region.add((cx, cy))
            for dx, dy in dirs:
                stack.append((cx + dx, cy + dy))
        return region

    # ---- Access and Stats ----

    def get_map(self, map_id: str) -> Optional[TileMap]:
        return self._maps.get(map_id)

    def list_maps(self) -> List[TileMap]:
        return list(self._maps.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_maps": len(self._maps),
            "total_tiles_set": sum(m.total_tiles_set for m in self._maps.values()),
            "total_layers": sum(len(m.layers) for m in self._maps.values()),
            "total_chunks": sum(len(m.chunks) for m in self._maps.values()),
            "visible_chunks": sum(
                sum(1 for c in m.chunks if c.visible)
                for m in self._maps.values()),
            "auto_tile_brushes": len(self._brushes),
            "atlases_generated": len(self._atlas_cache),
            "nav_meshes_generated": len(self._nav_meshes),
        }


def get_tile_map_optimizer() -> TileMapOptimizer:
    return TileMapOptimizer.get_instance()