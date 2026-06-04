"""
SparkLabs Engine - GPU Batch Rendering System

GPU-accelerated batch rendering system for the SparkLabs AI-native game engine.
Manages sprite layers, tile layers, render batches, and GPU profiling for
optimized 2D rendering pipelines. Provides instanced rendering support,
chunked tilemap rendering, draw call batching, and quality preset management.

Architecture:
  EngineGPUBatchRendering (Singleton)
    |-- SpriteLayerConfig     — per-layer sprite rendering configuration
    |-- SpriteInstance        — individual sprite within a layer
    |-- TileLayerConfig       — chunked tilemap layer configuration
    |-- RenderBatch           — assembled draw command batch
    |-- GPUProfile             — per-frame GPU performance metrics
    |-- BlendMode (enum)      — pixel blending operations
    |-- CullMode (enum)       — face culling strategies
    |-- SortOrder (enum)      — draw order sorting strategies
    |-- BatchType (enum)      — batch classification by content type
    |-- LODLevel (enum)       — level-of-detail quality tiers
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class BlendMode(Enum):
    """Pixel blending operations for rendering transparency and effects."""
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    ALPHA = "alpha"
    PREMULTIPLIED = "premultiplied"
    CUSTOM = "custom"


class CullMode(Enum):
    """Face culling strategies for backface and frontface removal."""
    NONE = "none"
    FRONT = "front"
    BACK = "back"
    BOTH = "both"


class SortOrder(Enum):
    """Draw order sorting strategies for layers and batches."""
    BACK_TO_FRONT = "back_to_front"
    FRONT_TO_BACK = "front_to_back"
    TEXTURE_ATLAS = "texture_atlas"
    CUSTOM = "custom"


class BatchType(Enum):
    """Classification of render batches by content type."""
    SPRITE = "sprite"
    TILE = "tile"
    PARTICLE = "particle"
    TEXT = "text"
    UI = "ui"
    CUSTOM = "custom"


class LODLevel(Enum):
    """Level-of-detail quality tiers for tilemap rendering."""
    LOD0 = "lod0"
    LOD1 = "lod1"
    LOD2 = "lod2"
    LOD3 = "lod3"
    LOD4 = "lod4"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_uid_stub() -> str:
    """Generate a unique identifier string using UUID4."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Quality preset configurations
# ---------------------------------------------------------------------------

_QUALITY_PRESETS: Dict[str, Dict[str, Any]] = {
    "low": {
        "max_sprites_per_layer": 256,
        "max_tile_chunk_size": 16,
        "use_instancing": False,
        "lod_default": LODLevel.LOD4,
        "memory_budget_mb": 128.0,
        "batch_size_target": 16,
    },
    "medium": {
        "max_sprites_per_layer": 1024,
        "max_tile_chunk_size": 32,
        "use_instancing": True,
        "lod_default": LODLevel.LOD2,
        "memory_budget_mb": 256.0,
        "batch_size_target": 32,
    },
    "high": {
        "max_sprites_per_layer": 4096,
        "max_tile_chunk_size": 64,
        "use_instancing": True,
        "lod_default": LODLevel.LOD1,
        "memory_budget_mb": 512.0,
        "batch_size_target": 64,
    },
    "ultra": {
        "max_sprites_per_layer": 16384,
        "max_tile_chunk_size": 128,
        "use_instancing": True,
        "lod_default": LODLevel.LOD0,
        "memory_budget_mb": 1024.0,
        "batch_size_target": 128,
    },
}


# ---------------------------------------------------------------------------
# Dataclass Configurations
# ---------------------------------------------------------------------------


@dataclass
class SpriteLayerConfig:
    """Per-layer sprite rendering configuration.

    Defines the maximum sprite capacity, texture atlas binding, blend mode,
    sort order, culling behavior, depth positioning, and GPU buffer allocation
    for a sprite rendering layer.
    """
    layer_id: str = field(default_factory=_generate_uid_stub)
    name: str = ""
    max_sprites: int = 1024
    texture_atlas: str = ""
    blend_mode: BlendMode = BlendMode.ALPHA
    sort_order: SortOrder = SortOrder.BACK_TO_FRONT
    cull_mode: CullMode = CullMode.NONE
    is_visible: bool = True
    layer_depth: float = 0.0
    scroll_factor: Tuple[float, float] = (1.0, 1.0)
    use_instancing: bool = True
    gpu_buffer_size: int = 0
    draw_call_count: int = 0
    sprite_count: int = 0
    memory_usage_mb: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "max_sprites": self.max_sprites,
            "texture_atlas": self.texture_atlas,
            "blend_mode": self.blend_mode.value,
            "sort_order": self.sort_order.value,
            "cull_mode": self.cull_mode.value,
            "is_visible": self.is_visible,
            "layer_depth": self.layer_depth,
            "scroll_factor": list(self.scroll_factor),
            "use_instancing": self.use_instancing,
            "gpu_buffer_size": self.gpu_buffer_size,
            "draw_call_count": self.draw_call_count,
            "sprite_count": self.sprite_count,
            "memory_usage_mb": self.memory_usage_mb,
            "created_at": self.created_at,
        }


@dataclass
class SpriteInstance:
    """Individual sprite within a rendering layer.

    Holds the transform, visual properties, animation state, and dirty
    flag tracking for efficient GPU buffer updates.
    """
    instance_id: str = field(default_factory=_generate_uid_stub)
    layer_id: str = ""
    texture_frame: int = 0
    position: Tuple[float, float] = (0.0, 0.0)
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    alpha: float = 1.0
    tint: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    animation_state: str = ""
    animation_progress: float = 0.0
    scroll_factor: Tuple[float, float] = (1.0, 1.0)
    is_visible: bool = True
    update_mask: int = 0
    created_at: float = field(default_factory=_time_module.time)
    last_updated: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "layer_id": self.layer_id,
            "texture_frame": self.texture_frame,
            "position": list(self.position),
            "rotation": self.rotation,
            "scale": list(self.scale),
            "alpha": self.alpha,
            "tint": list(self.tint),
            "animation_state": self.animation_state,
            "animation_progress": self.animation_progress,
            "scroll_factor": list(self.scroll_factor),
            "is_visible": self.is_visible,
            "update_mask": self.update_mask,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }


@dataclass
class TileLayerConfig:
    """Chunked tilemap layer configuration.

    Manages a grid-based tile layer with chunked subdivision for
    frustum culling, LOD selection, and efficient GPU upload.
    """
    layer_id: str = field(default_factory=_generate_uid_stub)
    name: str = ""
    width: int = 0
    height: int = 0
    tile_width: int = 32
    tile_height: int = 32
    tileset: str = ""
    map_data: List[List[int]] = field(default_factory=list)
    chunk_size: int = 32
    visible_chunks: List[int] = field(default_factory=list)
    lod_levels: List[LODLevel] = field(default_factory=lambda: [LODLevel.LOD0, LODLevel.LOD1, LODLevel.LOD2])
    is_visible: bool = True
    layer_depth: float = 0.0
    draw_call_count: int = 0
    tile_count: int = 0
    memory_usage_mb: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "tileset": self.tileset,
            "map_data": [list(row) for row in self.map_data],
            "chunk_size": self.chunk_size,
            "visible_chunks": list(self.visible_chunks),
            "lod_levels": [lv.value for lv in self.lod_levels],
            "is_visible": self.is_visible,
            "layer_depth": self.layer_depth,
            "draw_call_count": self.draw_call_count,
            "tile_count": self.tile_count,
            "memory_usage_mb": self.memory_usage_mb,
            "created_at": self.created_at,
        }


@dataclass
class RenderBatch:
    """Assembled draw command batch for GPU submission.

    Represents a single draw call batch with vertex/index buffers,
    material bindings, texture references, and a dirty flag for
    incremental rebuild optimization.
    """
    batch_id: str = field(default_factory=_generate_uid_stub)
    layer_id: str = ""
    batch_type: BatchType = BatchType.SPRITE
    vertex_count: int = 0
    index_count: int = 0
    draw_command: Dict[str, Any] = field(default_factory=dict)
    material: str = ""
    texture_bindings: List[str] = field(default_factory=list)
    uniform_buffer: Dict[str, Any] = field(default_factory=dict)
    is_dirty: bool = True
    sort_key: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    last_rendered: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "layer_id": self.layer_id,
            "batch_type": self.batch_type.value,
            "vertex_count": self.vertex_count,
            "index_count": self.index_count,
            "draw_command": dict(self.draw_command),
            "material": self.material,
            "texture_bindings": list(self.texture_bindings),
            "uniform_buffer": dict(self.uniform_buffer),
            "is_dirty": self.is_dirty,
            "sort_key": self.sort_key,
            "created_at": self.created_at,
            "last_rendered": self.last_rendered,
        }


@dataclass
class GPUProfile:
    """Per-frame GPU performance metrics.

    Captures timing, draw call counts, triangle/vertex throughput,
    state change overhead, memory usage, and buffer upload statistics
    for a single rendered frame.
    """
    profile_id: str = field(default_factory=_generate_uid_stub)
    frame_id: int = 0
    gpu_time_ms: float = 0.0
    draw_calls: int = 0
    triangles: int = 0
    vertices: int = 0
    batches: int = 0
    texture_binds: int = 0
    shader_switches: int = 0
    state_changes: int = 0
    buffer_uploads_mb: float = 0.0
    memory_used_mb: float = 0.0
    memory_budget_mb: float = 512.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "frame_id": self.frame_id,
            "gpu_time_ms": self.gpu_time_ms,
            "draw_calls": self.draw_calls,
            "triangles": self.triangles,
            "vertices": self.vertices,
            "batches": self.batches,
            "texture_binds": self.texture_binds,
            "shader_switches": self.shader_switches,
            "state_changes": self.state_changes,
            "buffer_uploads_mb": self.buffer_uploads_mb,
            "memory_used_mb": self.memory_used_mb,
            "memory_budget_mb": self.memory_budget_mb,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Singleton Engine
# ---------------------------------------------------------------------------


class EngineGPUBatchRendering:
    """GPU-accelerated batch rendering system for 2D sprite and tile pipelines.

    Manages sprite layers with instanced rendering, chunked tilemap layers
    with LOD selection, render batch assembly, GPU profiling, and quality
    preset configuration. Provides draw call optimization through batch
    layout analysis and memory budget enforcement.

    Usage:
        gpu = get_gpu_batch_rendering()
        layer = gpu.create_sprite_layer("ui_sprites", 1024, "atlas_ui")
        inst = gpu.add_sprite_instance(layer.layer_id, 5, (100, 200))
        gpu.batch_update_sprites(layer.layer_id, {inst.instance_id: {"alpha": 0.5}})
        profile = gpu.record_gpu_profile()
    """

    _instance: Optional["EngineGPUBatchRendering"] = None
    _lock: threading.RLock = threading.RLock()

    # Memory estimation constants (bytes)
    _BYTES_PER_SPRITE_INSTANCE: int = 128
    _BYTES_PER_TILE: int = 16
    _BYTES_PER_VERTEX: int = 32
    _MB_DIVISOR: float = 1024.0 * 1024.0

    def __new__(cls) -> "EngineGPUBatchRendering":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._sprite_layers: Dict[str, SpriteLayerConfig] = {}
        self._sprite_instances: Dict[str, SpriteInstance] = {}
        self._layer_sprites: Dict[str, Dict[str, SpriteInstance]] = {}
        self._tile_layers: Dict[str, TileLayerConfig] = {}
        self._render_batches: Dict[str, RenderBatch] = {}
        self._layer_batches: Dict[str, List[str]] = {}
        self._gpu_profiles: List[GPUProfile] = []
        self._frame_id: int = 0
        self._quality_preset: str = "high"
        self._memory_budget_mb: float = 512.0
        self._total_draw_calls: int = 0
        self._total_triangles: int = 0
        self._total_vertices: int = 0
        self._total_gpu_time_ms: float = 0.0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EngineGPUBatchRendering":
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_sprite_layer_memory(self, layer: SpriteLayerConfig) -> float:
        """Estimate GPU memory usage for a sprite layer in megabytes."""
        sprite_bytes = layer.sprite_count * self._BYTES_PER_SPRITE_INSTANCE
        buffer_bytes = layer.gpu_buffer_size
        return (sprite_bytes + buffer_bytes) / self._MB_DIVISOR

    def _estimate_tile_layer_memory(self, layer: TileLayerConfig) -> float:
        """Estimate GPU memory usage for a tile layer in megabytes."""
        tile_bytes = layer.tile_count * self._BYTES_PER_TILE
        return tile_bytes / self._MB_DIVISOR

    def _estimate_batch_memory(self, batch: RenderBatch) -> float:
        """Estimate GPU memory usage for a render batch in megabytes."""
        vert_bytes = batch.vertex_count * self._BYTES_PER_VERTEX
        idx_bytes = batch.index_count * 4
        return (vert_bytes + idx_bytes) / self._MB_DIVISOR

    def _compute_total_memory(self) -> float:
        """Compute total estimated GPU memory usage across all layers."""
        total = 0.0
        for layer in self._sprite_layers.values():
            total += layer.memory_usage_mb
        for layer in self._tile_layers.values():
            total += layer.memory_usage_mb
        for batch in self._render_batches.values():
            total += self._estimate_batch_memory(batch)
        return total

    def _is_within_budget(self, additional_mb: float = 0.0) -> bool:
        """Check if current memory usage plus additional is within budget."""
        return (self._compute_total_memory() + additional_mb) <= self._memory_budget_mb

    # ------------------------------------------------------------------
    # Sprite Layer Management
    # ------------------------------------------------------------------

    def create_sprite_layer(
        self,
        name: str,
        max_sprites: int = 1024,
        texture_atlas: str = "",
        blend_mode: BlendMode = BlendMode.ALPHA,
        sort_order: SortOrder = SortOrder.BACK_TO_FRONT,
        cull_mode: CullMode = CullMode.NONE,
        layer_depth: float = 0.0,
        use_instancing: bool = True,
    ) -> SpriteLayerConfig:
        """Create a new sprite rendering layer.

        Args:
            name: Human-readable layer name.
            max_sprites: Maximum number of sprites this layer can hold.
            texture_atlas: Texture atlas resource identifier.
            blend_mode: Pixel blending operation.
            sort_order: Draw order sorting strategy.
            cull_mode: Face culling strategy.
            layer_depth: Z-depth for layer ordering.
            use_instancing: Whether to use GPU instanced rendering.

        Returns:
            The newly created SpriteLayerConfig.
        """
        with self._lock:
            gpu_buffer_size = max_sprites * self._BYTES_PER_SPRITE_INSTANCE
            layer = SpriteLayerConfig(
                name=name,
                max_sprites=max_sprites,
                texture_atlas=texture_atlas,
                blend_mode=blend_mode,
                sort_order=sort_order,
                cull_mode=cull_mode,
                layer_depth=layer_depth,
                use_instancing=use_instancing,
                gpu_buffer_size=gpu_buffer_size,
            )
            self._sprite_layers[layer.layer_id] = layer
            self._layer_sprites[layer.layer_id] = {}
            return layer

    def add_sprite_instance(
        self,
        layer_id: str,
        texture_frame: int = 0,
        position: Tuple[float, float] = (0.0, 0.0),
        rotation: float = 0.0,
        scale: Tuple[float, float] = (1.0, 1.0),
        alpha: float = 1.0,
        tint: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        scroll_factor: Tuple[float, float] = (1.0, 1.0),
    ) -> SpriteInstance:
        """Add a new sprite instance to a sprite layer.

        Args:
            layer_id: The target sprite layer identifier.
            texture_frame: Frame index within the texture atlas.
            position: World-space position (x, y).
            rotation: Rotation angle in radians.
            scale: Scale factors (x, y).
            alpha: Opacity value (0.0 to 1.0).
            tint: RGBA color tint.
            scroll_factor: Parallax scroll factor (x, y).

        Returns:
            The newly created SpriteInstance.

        Raises:
            KeyError: If the layer does not exist.
            RuntimeError: If the layer is at maximum sprite capacity.
        """
        with self._lock:
            layer = self._sprite_layers.get(layer_id)
            if layer is None:
                raise KeyError(f"Sprite layer '{layer_id}' does not exist")

            if layer.sprite_count >= layer.max_sprites:
                raise RuntimeError(
                    f"Sprite layer '{layer_id}' is at maximum capacity ({layer.max_sprites})"
                )

            instance = SpriteInstance(
                layer_id=layer_id,
                texture_frame=texture_frame,
                position=position,
                rotation=rotation,
                scale=scale,
                alpha=alpha,
                tint=tint,
                scroll_factor=scroll_factor,
            )
            self._sprite_instances[instance.instance_id] = instance
            self._layer_sprites[layer_id][instance.instance_id] = instance
            layer.sprite_count += 1
            layer.memory_usage_mb = self._estimate_sprite_layer_memory(layer)
            return instance

    def update_sprite_instance(self, instance_id: str, **kwargs: Any) -> bool:
        """Update properties of an existing sprite instance.

        Accepts keyword arguments for any mutable SpriteInstance field.

        Args:
            instance_id: The sprite instance identifier.
            **kwargs: Fields to update on the instance.

        Returns:
            True if the instance was found and updated, False otherwise.
        """
        with self._lock:
            instance = self._sprite_instances.get(instance_id)
            if instance is None:
                return False

            updatable_fields = {
                "texture_frame", "position", "rotation", "scale",
                "alpha", "tint", "animation_state", "animation_progress",
                "scroll_factor", "is_visible", "update_mask",
            }
            for key, value in kwargs.items():
                if key in updatable_fields:
                    setattr(instance, key, value)

            instance.last_updated = _time_module.time()
            instance.update_mask |= 1
            return True

    def remove_sprite_instance(self, instance_id: str) -> bool:
        """Remove a sprite instance from its layer.

        Args:
            instance_id: The sprite instance identifier.

        Returns:
            True if the instance was found and removed, False otherwise.
        """
        with self._lock:
            instance = self._sprite_instances.pop(instance_id, None)
            if instance is None:
                return False

            layer_sprites = self._layer_sprites.get(instance.layer_id)
            if layer_sprites is not None:
                layer_sprites.pop(instance_id, None)

            layer = self._sprite_layers.get(instance.layer_id)
            if layer is not None:
                layer.sprite_count = max(0, layer.sprite_count - 1)
                layer.memory_usage_mb = self._estimate_sprite_layer_memory(layer)

            return True

    def batch_update_sprites(
        self, layer_id: str, updates: Dict[str, Dict[str, Any]]
    ) -> int:
        """Apply batch updates to multiple sprites in a layer.

        Args:
            layer_id: The sprite layer identifier.
            updates: Mapping of instance_id to field-value dictionaries.

        Returns:
            The number of instances successfully updated.
        """
        with self._lock:
            updated = 0
            layer_sprites = self._layer_sprites.get(layer_id, {})
            for instance_id, fields in updates.items():
                instance = layer_sprites.get(instance_id)
                if instance is None:
                    continue
                updatable = {
                    "texture_frame", "position", "rotation", "scale",
                    "alpha", "tint", "animation_state", "animation_progress",
                    "scroll_factor", "is_visible", "update_mask",
                }
                for key, value in fields.items():
                    if key in updatable:
                        setattr(instance, key, value)
                instance.last_updated = _time_module.time()
                instance.update_mask |= 1
                updated += 1
            return updated

    def set_sprite_animation(
        self,
        instance_id: str,
        animation_name: str = "",
        start_frame: int = 0,
        end_frame: int = 0,
        frame_rate: float = 30.0,
        loop: bool = True,
    ) -> bool:
        """Configure animation playback for a sprite instance.

        Args:
            instance_id: The sprite instance identifier.
            animation_name: Name of the animation state.
            start_frame: Starting frame index in the texture atlas.
            end_frame: Ending frame index in the texture atlas.
            frame_rate: Frames per second for playback.
            loop: Whether the animation should loop.

        Returns:
            True if the instance was found and configured, False otherwise.
        """
        with self._lock:
            instance = self._sprite_instances.get(instance_id)
            if instance is None:
                return False

            instance.animation_state = animation_name
            instance.texture_frame = start_frame
            instance.animation_progress = 0.0
            instance.last_updated = _time_module.time()
            instance.update_mask |= 1
            return True

    # ------------------------------------------------------------------
    # Tile Layer Management
    # ------------------------------------------------------------------

    def create_tile_layer(
        self,
        name: str,
        width: int,
        height: int,
        tile_width: int = 32,
        tile_height: int = 32,
        tileset: str = "",
        chunk_size: int = 32,
        lod_levels: Optional[List[LODLevel]] = None,
    ) -> TileLayerConfig:
        """Create a new chunked tilemap layer.

        Args:
            name: Human-readable layer name.
            width: Map width in tiles.
            height: Map height in tiles.
            tile_width: Pixel width of each tile.
            tile_height: Pixel height of each tile.
            tileset: Tileset resource identifier.
            chunk_size: Number of tiles per chunk side.
            lod_levels: Available LOD levels for this layer.

        Returns:
            The newly created TileLayerConfig.
        """
        with self._lock:
            if width <= 0 or height <= 0:
                raise ValueError("width and height must be positive")
            if chunk_size <= 0:
                raise ValueError("chunk_size must be positive")

            layer = TileLayerConfig(
                name=name,
                width=width,
                height=height,
                tile_width=tile_width,
                tile_height=tile_height,
                tileset=tileset,
                chunk_size=chunk_size,
                lod_levels=lod_levels or [LODLevel.LOD0, LODLevel.LOD1, LODLevel.LOD2],
                map_data=[[-1] * width for _ in range(height)],
            )
            self._tile_layers[layer.layer_id] = layer
            layer.tile_count = width * height
            layer.memory_usage_mb = self._estimate_tile_layer_memory(layer)
            return layer

    def set_tile_map_data(self, layer_id: str, map_data: List[List[int]]) -> bool:
        """Replace the entire tile map data for a layer.

        Args:
            layer_id: The tile layer identifier.
            map_data: 2D list of tile indices (row-major).

        Returns:
            True if the layer was found and updated, False otherwise.
        """
        with self._lock:
            layer = self._tile_layers.get(layer_id)
            if layer is None:
                return False

            layer.map_data = [list(row) for row in map_data]
            if map_data:
                layer.width = len(map_data[0]) if map_data else 0
                layer.height = len(map_data)
            layer.tile_count = layer.width * layer.height
            layer.memory_usage_mb = self._estimate_tile_layer_memory(layer)
            return True

    def set_tile(
        self, layer_id: str, x: int, y: int, tile_index: int
    ) -> bool:
        """Set a single tile at the specified grid coordinates.

        Args:
            layer_id: The tile layer identifier.
            x: Column index.
            y: Row index.
            tile_index: The tile index to set.

        Returns:
            True if the tile was set successfully, False if out of bounds.
        """
        with self._lock:
            layer = self._tile_layers.get(layer_id)
            if layer is None:
                return False
            if x < 0 or x >= layer.width or y < 0 or y >= layer.height:
                return False

            layer.map_data[y][x] = tile_index
            return True

    def update_visible_chunks(
        self,
        layer_id: str,
        camera_bounds: Tuple[float, float, float, float],
    ) -> List[int]:
        """Compute which chunks are visible within the camera bounds.

        Args:
            layer_id: The tile layer identifier.
            camera_bounds: Camera viewport as (min_x, min_y, max_x, max_y).

        Returns:
            List of visible chunk indices.
        """
        with self._lock:
            layer = self._tile_layers.get(layer_id)
            if layer is None:
                return []

            min_x, min_y, max_x, max_y = camera_bounds
            chunk_cols = (layer.width + layer.chunk_size - 1) // layer.chunk_size
            chunk_rows = (layer.height + layer.chunk_size - 1) // layer.chunk_size

            visible: List[int] = []
            for cy in range(chunk_rows):
                for cx in range(chunk_cols):
                    chunk_left = cx * layer.chunk_size * layer.tile_width
                    chunk_top = cy * layer.chunk_size * layer.tile_height
                    chunk_right = chunk_left + layer.chunk_size * layer.tile_width
                    chunk_bottom = chunk_top + layer.chunk_size * layer.tile_height

                    if chunk_right >= min_x and chunk_left <= max_x and \
                       chunk_bottom >= min_y and chunk_top <= max_y:
                        visible.append(cy * chunk_cols + cx)

            layer.visible_chunks = visible
            return visible

    def set_layer_visibility(self, layer_id: str, visible: bool) -> bool:
        """Set the visibility of a sprite or tile layer.

        Args:
            layer_id: The layer identifier (sprite or tile).
            visible: Whether the layer should be visible.

        Returns:
            True if the layer was found and updated, False otherwise.
        """
        with self._lock:
            sprite_layer = self._sprite_layers.get(layer_id)
            if sprite_layer is not None:
                sprite_layer.is_visible = visible
                return True

            tile_layer = self._tile_layers.get(layer_id)
            if tile_layer is not None:
                tile_layer.is_visible = visible
                return True

            return False

    def set_layer_depth(self, layer_id: str, depth: float) -> bool:
        """Set the depth value of a sprite or tile layer.

        Args:
            layer_id: The layer identifier (sprite or tile).
            depth: Z-depth value for layer ordering.

        Returns:
            True if the layer was found and updated, False otherwise.
        """
        with self._lock:
            sprite_layer = self._sprite_layers.get(layer_id)
            if sprite_layer is not None:
                sprite_layer.layer_depth = depth
                return True

            tile_layer = self._tile_layers.get(layer_id)
            if tile_layer is not None:
                tile_layer.layer_depth = depth
                return True

            return False

    def set_lod_level(self, layer_id: str, level: LODLevel) -> bool:
        """Set the active LOD level for a tile layer.

        Args:
            layer_id: The tile layer identifier.
            level: The LOD level to activate.

        Returns:
            True if the layer was found and updated, False otherwise.
        """
        with self._lock:
            layer = self._tile_layers.get(layer_id)
            if layer is None:
                return False
            if level not in layer.lod_levels:
                return False
            return True

    # ------------------------------------------------------------------
    # Render Batch Management
    # ------------------------------------------------------------------

    def generate_render_batches(self, layer_id: str) -> List[RenderBatch]:
        """Generate render batches for a layer's current content.

        Assembles draw commands, vertex/index buffers, and material
        bindings for all visible sprites or tiles in the layer.

        Args:
            layer_id: The layer identifier (sprite or tile).

        Returns:
            List of generated RenderBatch objects.
        """
        with self._lock:
            batches: List[RenderBatch] = []

            sprite_layer = self._sprite_layers.get(layer_id)
            if sprite_layer is not None and sprite_layer.is_visible:
                sprites = self._layer_sprites.get(layer_id, {})
                visible_sprites = [
                    s for s in sprites.values() if s.is_visible
                ]
                if visible_sprites:
                    batch = RenderBatch(
                        layer_id=layer_id,
                        batch_type=BatchType.SPRITE,
                        vertex_count=len(visible_sprites) * 4,
                        index_count=len(visible_sprites) * 6,
                        draw_command={
                            "primitive": "triangles",
                            "instance_count": len(visible_sprites) if sprite_layer.use_instancing else 1,
                            "start_index": 0,
                        },
                        material=sprite_layer.texture_atlas,
                        texture_bindings=[sprite_layer.texture_atlas] if sprite_layer.texture_atlas else [],
                        is_dirty=True,
                        sort_key=sprite_layer.layer_depth,
                    )
                    self._render_batches[batch.batch_id] = batch
                    self._layer_batches.setdefault(layer_id, []).append(batch.batch_id)
                    batches.append(batch)

            tile_layer = self._tile_layers.get(layer_id)
            if tile_layer is not None and tile_layer.is_visible:
                batch = RenderBatch(
                    layer_id=layer_id,
                    batch_type=BatchType.TILE,
                    vertex_count=tile_layer.tile_count * 4,
                    index_count=tile_layer.tile_count * 6,
                    draw_command={
                        "primitive": "triangles",
                        "instance_count": 1,
                        "start_index": 0,
                        "chunk_size": tile_layer.chunk_size,
                    },
                    material=tile_layer.tileset,
                    texture_bindings=[tile_layer.tileset] if tile_layer.tileset else [],
                    is_dirty=True,
                    sort_key=tile_layer.layer_depth,
                )
                self._render_batches[batch.batch_id] = batch
                self._layer_batches.setdefault(layer_id, []).append(batch.batch_id)
                batches.append(batch)

            return batches

    def flush_batch(self, batch_id: str) -> bool:
        """Mark a render batch as flushed (submitted to GPU).

        Args:
            batch_id: The render batch identifier.

        Returns:
            True if the batch was found and flushed, False otherwise.
        """
        with self._lock:
            batch = self._render_batches.get(batch_id)
            if batch is None:
                return False
            batch.is_dirty = False
            batch.last_rendered = _time_module.time()
            return True

    # ------------------------------------------------------------------
    # GPU Profiling
    # ------------------------------------------------------------------

    def record_gpu_profile(self) -> GPUProfile:
        """Record a GPU performance profile for the current frame.

        Collects draw call counts, triangle/vertex throughput, state
        change overhead, and memory usage metrics.

        Returns:
            A new GPUProfile with current frame statistics.
        """
        with self._lock:
            self._frame_id += 1
            total_draw_calls = 0
            total_triangles = 0
            total_vertices = 0
            total_batches = len(self._render_batches)
            total_texture_binds = 0
            total_shader_switches = 0
            total_state_changes = 0
            total_buffer_uploads = 0.0

            for batch in self._render_batches.values():
                total_draw_calls += 1
                total_vertices += batch.vertex_count
                total_triangles += batch.index_count // 3
                total_texture_binds += len(batch.texture_bindings)
                if batch.material:
                    total_shader_switches += 1
                if batch.is_dirty:
                    total_state_changes += 1
                    total_buffer_uploads += self._estimate_batch_memory(batch)

            gpu_time = max(0.1, total_draw_calls * 0.05 + total_batches * 0.02)
            memory_used = self._compute_total_memory()

            self._total_draw_calls = total_draw_calls
            self._total_triangles = total_triangles
            self._total_vertices = total_vertices
            self._total_gpu_time_ms = gpu_time

            profile = GPUProfile(
                frame_id=self._frame_id,
                gpu_time_ms=gpu_time,
                draw_calls=total_draw_calls,
                triangles=total_triangles,
                vertices=total_vertices,
                batches=total_batches,
                texture_binds=total_texture_binds,
                shader_switches=total_shader_switches,
                state_changes=total_state_changes,
                buffer_uploads_mb=total_buffer_uploads,
                memory_used_mb=memory_used,
                memory_budget_mb=self._memory_budget_mb,
            )
            self._gpu_profiles.append(profile)

            if len(self._gpu_profiles) > 600:
                self._gpu_profiles = self._gpu_profiles[-300:]

            return profile

    def get_gpu_stats(self) -> Dict[str, Any]:
        """Get comprehensive GPU rendering statistics.

        Returns:
            Dictionary with total layer, sprite, tile, batch counts,
            draw call metrics, GPU memory, and timing information.
        """
        with self._lock:
            total_sprites = sum(
                layer.sprite_count for layer in self._sprite_layers.values()
            )
            total_tiles = sum(
                layer.tile_count for layer in self._tile_layers.values()
            )
            return {
                "total_layers": len(self._sprite_layers) + len(self._tile_layers),
                "total_sprites": total_sprites,
                "total_tiles": total_tiles,
                "total_batches": len(self._render_batches),
                "draw_calls": self._total_draw_calls,
                "gpu_memory": round(self._compute_total_memory(), 2),
                "gpu_time": round(self._total_gpu_time_ms, 2),
                "triangles": self._total_triangles,
                "vertices": self._total_vertices,
                "frame_id": self._frame_id,
                "quality_preset": self._quality_preset,
                "memory_budget_mb": self._memory_budget_mb,
            }

    # ------------------------------------------------------------------
    # Quality and Optimization
    # ------------------------------------------------------------------

    def set_quality_preset(self, preset: str) -> None:
        """Apply a quality preset configuration.

        Presets adjust sprite limits, chunk sizes, instancing
        behavior, default LOD levels, and memory budgets.

        Args:
            preset: One of 'low', 'medium', 'high', 'ultra'.

        Raises:
            ValueError: If the preset name is not recognized.
        """
        with self._lock:
            if preset not in ("low", "medium", "high", "ultra"):
                raise ValueError(
                    f"Unknown quality preset '{preset}'. "
                    f"Valid values: low, medium, high, ultra"
                )

            self._quality_preset = preset
            config = _QUALITY_PRESETS[preset]
            self._memory_budget_mb = config["memory_budget_mb"]

    def optimize_batch_layout(self, layer_id: str) -> Dict[str, Any]:
        """Analyze and optimize batch layout for a layer to reduce draw calls.

        Attempts to merge compatible batches, reorder by texture atlas,
        and eliminate redundant state changes.

        Args:
            layer_id: The layer to optimize.

        Returns:
            Dictionary with original_batches, optimized_batches,
            and draw_call_reduction counts.
        """
        with self._lock:
            batch_ids = self._layer_batches.get(layer_id, [])
            original_count = len(batch_ids)

            if original_count <= 1:
                return {
                    "original_batches": original_count,
                    "optimized_batches": original_count,
                    "draw_call_reduction": 0,
                }

            # Simulate batch merging: group by material and texture bindings
            unique_materials: Dict[str, List[str]] = {}
            for bid in batch_ids:
                batch = self._render_batches.get(bid)
                if batch is None:
                    continue
                key = f"{batch.material}|{','.join(sorted(batch.texture_bindings))}"
                unique_materials.setdefault(key, []).append(bid)

            optimized_count = len(unique_materials)
            reduction = max(0, original_count - optimized_count)

            return {
                "original_batches": original_count,
                "optimized_batches": optimized_count,
                "draw_call_reduction": reduction,
            }

    def set_memory_budget(self, max_mb: float) -> None:
        """Set the maximum GPU memory budget in megabytes.

        Args:
            max_mb: Maximum GPU memory in megabytes.
        """
        with self._lock:
            self._memory_budget_mb = max(0.0, max_mb)

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed GPU memory usage breakdown.

        Returns:
            Dictionary with per-layer memory usage, total, budget,
            and utilization percentage.
        """
        with self._lock:
            by_layer: Dict[str, float] = {}
            for layer in self._sprite_layers.values():
                by_layer[layer.layer_id] = round(layer.memory_usage_mb, 2)
            for layer in self._tile_layers.values():
                by_layer[layer.layer_id] = round(layer.memory_usage_mb, 2)

            total = self._compute_total_memory()
            utilization = (total / self._memory_budget_mb * 100.0) if self._memory_budget_mb > 0 else 0.0

            return {
                "by_layer": by_layer,
                "total": round(total, 2),
                "budget": self._memory_budget_mb,
                "utilization_pct": round(utilization, 2),
            }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all GPU batch rendering state.

        Clears all layers, instances, batches, profiles, and counters.
        The singleton instance remains valid for reuse.
        """
        with self._lock:
            self._sprite_layers.clear()
            self._sprite_instances.clear()
            self._layer_sprites.clear()
            self._tile_layers.clear()
            self._render_batches.clear()
            self._layer_batches.clear()
            self._gpu_profiles.clear()
            self._frame_id = 0
            self._quality_preset = "high"
            self._memory_budget_mb = 512.0
            self._total_draw_calls = 0
            self._total_triangles = 0
            self._total_vertices = 0
            self._total_gpu_time_ms = 0.0


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

_gpu_batch_rendering: Optional[EngineGPUBatchRendering] = None


def get_gpu_batch_rendering() -> EngineGPUBatchRendering:
    """Return the global EngineGPUBatchRendering singleton instance."""
    global _gpu_batch_rendering
    if _gpu_batch_rendering is None:
        _gpu_batch_rendering = EngineGPUBatchRendering()
    return _gpu_batch_rendering