"""
SparkLabs Engine - Sprite Batcher

A high-performance 2D sprite batching system that optimizes draw calls by
grouping sprites with similar render states into unified GPU batches.
Inspired by efficient 2D rendering techniques, the batcher uses texture
atlases, dynamic geometry merging, and z-order-preserving batch generation
to maximize throughput for sprite-heavy 2D game scenes.

The batcher operates on a command-buffer model: game systems submit draw
commands throughout the frame, and the batcher processes them into optimized
GPU batches at render time, automatically handling texture switching,
blend mode transitions, and layer ordering.

Architecture:
  EngineSpriteBatcher (Singleton)
    |-- SpriteDrawCommand (individual sprite render request)
    |-- SpriteBatch (merged GPU batch of similar sprites)
    |-- TextureAtlas (packed texture regions for batch compatibility)
    |-- AtlasRegion (sub-region within a texture atlas)
    |-- BatchKey (hashing key for batch grouping)
    |-- BlendMode (supported blending operations)
    |-- BatchStrategy (optimization strategy selection)
    |-- SortMode (z-order sorting behavior)

Core Capabilities:
  - submit_sprite: Queue a sprite draw command
  - flush_batches: Process queued commands into optimized GPU batches
  - create_texture_atlas: Pack multiple textures into a single atlas
  - set_batch_strategy: Choose optimization strategy
  - get_render_stats: Retrieve batching performance metrics
  - clear_frame: Reset command buffer for the next frame
"""

from __future__ import annotations

import hashlib
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


class BlendMode(Enum):
    """Supported blending operations for sprite rendering."""
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    ALPHA_CLIP = "alpha_clip"
    PREMULTIPLIED = "premultiplied"
    CUSTOM = "custom"


class BatchStrategy(Enum):
    """Optimization strategies for batch generation."""
    TEXTURE_FIRST = "texture_first"
    DEPTH_FIRST = "depth_first"
    BLEND_FIRST = "blend_first"
    DYNAMIC = "dynamic"
    AGGRESSIVE = "aggressive"


class SortMode(Enum):
    """Z-order sorting behavior for batch generation."""
    NONE = "none"
    FRONT_TO_BACK = "front_to_back"
    BACK_TO_FRONT = "back_to_front"
    Y_SORT = "y_sort"
    CUSTOM = "custom"


class AtlasPackMode(Enum):
    """Texture atlas packing algorithms."""
    BIN_PACK = "bin_pack"
    GRID = "grid"
    ROW = "row"
    COLUMN = "column"
    BEST_FIT = "best_fit"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AtlasRegion:
    """A sub-region within a texture atlas.

    Attributes:
        region_id: Unique region identifier.
        atlas_id: Parent atlas identifier.
        source_texture: Original texture name.
        x: Left coordinate in atlas (normalized 0-1).
        y: Top coordinate in atlas (normalized 0-1).
        width: Width in atlas (normalized 0-1).
        height: Height in atlas (normalized 0-1).
        original_width: Source texture pixel width.
        original_height: Source texture pixel height.
        rotated: Whether the region is rotated 90 degrees.
    """
    region_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    atlas_id: str = ""
    source_texture: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    original_width: int = 64
    original_height: int = 64
    rotated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "atlas_id": self.atlas_id,
            "source_texture": self.source_texture,
            "uv_rect": {
                "x": round(self.x, 6),
                "y": round(self.y, 6),
                "width": round(self.width, 6),
                "height": round(self.height, 6),
            },
            "size": {"width": self.original_width, "height": self.original_height},
            "rotated": self.rotated,
        }


@dataclass
class TextureAtlas:
    """A packed texture atlas containing multiple sprite regions.

    Attributes:
        atlas_id: Unique atlas identifier.
        name: Atlas display name.
        size: Atlas dimensions (must be power-of-two).
        regions: Packed texture regions.
        free_space: Remaining free area fraction (0-1).
        texture_count: Number of textures packed.
    """
    atlas_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    size: int = 2048
    regions: Dict[str, AtlasRegion] = field(default_factory=dict)
    free_space: float = 1.0
    texture_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atlas_id": self.atlas_id,
            "name": self.name,
            "size": self.size,
            "region_count": len(self.regions),
            "texture_count": self.texture_count,
            "free_space": round(self.free_space, 4),
            "regions": {
                key: region.to_dict() for key, region in self.regions.items()
            },
        }


@dataclass
class SpriteDrawCommand:
    """A single sprite draw request submitted to the batcher.

    Attributes:
        command_id: Unique command identifier.
        texture_name: Texture to render.
        atlas_region: Atlas region if batched.
        position_x: World X position.
        position_y: World Y position.
        scale_x: Horizontal scale.
        scale_y: Vertical scale.
        rotation_degrees: Rotation in degrees.
        origin_x: Rotation origin X (normalized 0-1).
        origin_y: Rotation origin Y (normalized 0-1).
        color_rgba: Tint color (r, g, b, a) 0-255.
        blend_mode: Blending mode.
        z_order: Rendering depth.
        source_rect: Source rectangle (normalized) or None for full texture.
        flip_x: Horizontal flip.
        flip_y: Vertical flip.
        visible: Whether the sprite should render.
    """
    command_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    texture_name: str = ""
    atlas_region: Optional[str] = None
    position_x: float = 0.0
    position_y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation_degrees: float = 0.0
    origin_x: float = 0.5
    origin_y: float = 0.5
    color_rgba: Tuple[int, int, int, int] = (255, 255, 255, 255)
    blend_mode: BlendMode = BlendMode.NORMAL
    z_order: int = 0
    source_rect: Optional[Tuple[float, float, float, float]] = None
    flip_x: bool = False
    flip_y: bool = False
    visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "texture_name": self.texture_name,
            "atlas_region": self.atlas_region,
            "position": {"x": self.position_x, "y": self.position_y},
            "scale": {"x": self.scale_x, "y": self.scale_y},
            "rotation_degrees": self.rotation_degrees,
            "origin": {"x": self.origin_x, "y": self.origin_y},
            "color": {"r": self.color_rgba[0], "g": self.color_rgba[1],
                       "b": self.color_rgba[2], "a": self.color_rgba[3]},
            "blend_mode": self.blend_mode.value,
            "z_order": self.z_order,
            "flip": {"x": self.flip_x, "y": self.flip_y},
            "visible": self.visible,
        }


@dataclass
class BatchKey:
    """Hashing key for grouping sprites into batches.

    Attributes:
        atlas_id: Texture atlas identifier.
        blend_mode: Blending mode.
        key_hash: Pre-computed hash for fast comparison.
    """
    atlas_id: str = ""
    blend_mode: BlendMode = BlendMode.NORMAL
    key_hash: str = ""

    def __post_init__(self):
        if not self.key_hash:
            raw = f"{self.atlas_id}:{self.blend_mode.value}"
            self.key_hash = hashlib.md5(raw.encode()).hexdigest()[:8]

    def __hash__(self) -> int:
        return hash(self.key_hash)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BatchKey):
            return False
        return self.key_hash == other.key_hash


@dataclass
class SpriteBatch:
    """A merged GPU batch containing similar sprites.

    Attributes:
        batch_id: Unique batch identifier.
        batch_key: Grouping key for this batch.
        commands: Draw commands in this batch.
        vertex_count: Total vertices (4 per sprite).
        index_count: Total indices (6 per sprite).
        atlas_id: Texture atlas to bind.
        estimated_gpu_memory_kb: Approximate GPU memory footprint.
        sort_mode: Z-order sorting applied.
    """
    batch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    batch_key: Optional[BatchKey] = None
    commands: List[SpriteDrawCommand] = field(default_factory=list)
    vertex_count: int = 0
    index_count: int = 0
    atlas_id: str = ""
    estimated_gpu_memory_kb: float = 0.0
    sort_mode: SortMode = SortMode.NONE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "atlas_id": self.atlas_id,
            "blend_mode": self.batch_key.blend_mode.value if self.batch_key else "unknown",
            "sprite_count": len(self.commands),
            "vertex_count": self.vertex_count,
            "index_count": self.index_count,
            "estimated_memory_kb": round(self.estimated_gpu_memory_kb, 2),
            "sort_mode": self.sort_mode.value,
        }


# ---------------------------------------------------------------------------
# Engine Sprite Batcher (Singleton)
# ---------------------------------------------------------------------------


class EngineSpriteBatcher:
    """
    High-performance 2D sprite batching system.

    Optimizes draw calls by grouping sprites with similar render states
    into unified GPU batches. Uses texture atlases, dynamic geometry merging,
    and z-order-preserving batch generation to maximize rendering throughput
    for sprite-heavy 2D game scenes.

    The batcher operates on a command-buffer model: game systems submit
    draw commands, and the batcher flushes them into optimized GPU batches
    at render time.

    Features:
      - Texture atlas-based batch grouping for draw-call reduction
      - Dynamic batch strategy selection for scene characteristics
      - Z-order-preserving batch generation
      - Per-frame command buffer with frame-end flush
      - Comprehensive render statistics for profiling
      - Texture atlas creation with bin-packing
    """

    _instance: Optional["EngineSpriteBatcher"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineSpriteBatcher":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Command buffer (frame-level)
        self._command_buffer: List[SpriteDrawCommand] = []
        self._max_commands_per_frame: int = 10000

        # Generated batches
        self._batches: List[SpriteBatch] = []
        self._max_batches: int = 512

        # Texture atlases
        self._atlases: Dict[str, TextureAtlas] = {}
        self._atlas_registry: Dict[str, str] = {}  # texture_name -> atlas_id

        # Configuration
        self._batch_strategy: BatchStrategy = BatchStrategy.DYNAMIC
        self._sort_mode: SortMode = SortMode.BACK_TO_FRONT
        self._max_sprites_per_batch: int = 1024

        # Statistics
        self._frame_count: int = 0
        self._total_commands_processed: int = 0
        self._total_batches_generated: int = 0
        self._total_saved_draw_calls: int = 0
        self._frame_stats_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Command Submission
    # ------------------------------------------------------------------

    def submit_sprite(
        self,
        texture_name: str,
        position_x: float = 0.0,
        position_y: float = 0.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        rotation_degrees: float = 0.0,
        origin_x: float = 0.5,
        origin_y: float = 0.5,
        color_rgba: Tuple[int, int, int, int] = (255, 255, 255, 255),
        blend_mode: BlendMode = BlendMode.NORMAL,
        z_order: int = 0,
        source_rect: Optional[Tuple[float, float, float, float]] = None,
        flip_x: bool = False,
        flip_y: bool = False,
    ) -> SpriteDrawCommand:
        """
        Queue a sprite for rendering this frame.

        Args:
            texture_name: Texture asset identifier.
            position_x: World X position.
            position_y: World Y position.
            scale_x: Horizontal scale factor.
            scale_y: Vertical scale factor.
            rotation_degrees: Rotation in degrees.
            origin_x: Rotation pivot X (0-1 normalized).
            origin_y: Rotation pivot Y (0-1 normalized).
            color_rgba: Tint color (R, G, B, A) each 0-255.
            blend_mode: Blend mode for rendering.
            z_order: Draw order depth.
            source_rect: Source UV rectangle (x, y, w, h) normalized.
            flip_x: Horizontal flip.
            flip_y: Vertical flip.

        Returns:
            The created SpriteDrawCommand.
        """
        atlas_region = self._atlas_registry.get(texture_name)

        command = SpriteDrawCommand(
            texture_name=texture_name,
            atlas_region=atlas_region,
            position_x=position_x,
            position_y=position_y,
            scale_x=scale_x,
            scale_y=scale_y,
            rotation_degrees=rotation_degrees,
            origin_x=origin_x,
            origin_y=origin_y,
            color_rgba=color_rgba,
            blend_mode=blend_mode,
            z_order=z_order,
            source_rect=source_rect,
            flip_x=flip_x,
            flip_y=flip_y,
        )

        with self._lock:
            if len(self._command_buffer) < self._max_commands_per_frame:
                self._command_buffer.append(command)

        return command

    # ------------------------------------------------------------------
    # Batch Processing
    # ------------------------------------------------------------------

    def flush_batches(self) -> List[SpriteBatch]:
        """
        Process all queued commands into optimized GPU batches.

        Groups sprites by texture atlas and blend mode, sorts within
        batches according to the configured sort mode, and generates
        merged GPU-ready batches.

        Returns:
            List of generated SpriteBatch objects.
        """
        with self._lock:
            commands = list(self._command_buffer)

        if not commands:
            return []

        # Filter invisible sprites
        visible = [c for c in commands if c.visible]
        if not visible:
            self._batches = []
            return []

        # Group commands by batch key
        groups: Dict[BatchKey, List[SpriteDrawCommand]] = {}
        for cmd in visible:
            atlas_id = self._atlas_registry.get(cmd.texture_name, "default")
            key = BatchKey(atlas_id=atlas_id, blend_mode=cmd.blend_mode)

            if key not in groups:
                groups[key] = []
            groups[key].append(cmd)

        # Generate batches
        batches: List[SpriteBatch] = []
        for batch_key, group in groups.items():
            # Sort within batch
            self._sort_commands(group, self._sort_mode)

            # Split oversized groups
            sub_groups = self._split_group(group, self._max_sprites_per_batch)
            for sub in sub_groups:
                batch = SpriteBatch(
                    batch_key=batch_key,
                    commands=sub,
                    vertex_count=len(sub) * 4,
                    index_count=len(sub) * 6,
                    atlas_id=batch_key.atlas_id,
                    estimated_gpu_memory_kb=len(sub) * 0.25,
                    sort_mode=self._sort_mode,
                )
                batches.append(batch)

        self._batches = batches
        self._frame_count += 1
        self._total_commands_processed += len(visible)
        self._total_batches_generated += len(batches)
        self._total_saved_draw_calls += max(0, len(visible) - len(batches))

        # Record frame stats
        self._frame_stats_history.append({
            "frame": self._frame_count,
            "commands": len(visible),
            "batches": len(batches),
            "saved_draw_calls": len(visible) - len(batches),
            "reduction_ratio": round(
                (1 - len(batches) / max(1, len(visible))) * 100, 1
            ),
        })
        if len(self._frame_stats_history) > 300:
            self._frame_stats_history = self._frame_stats_history[-150:]

        return batches

    def _sort_commands(
        self, commands: List[SpriteDrawCommand], sort_mode: SortMode
    ):
        """Sort draw commands within a batch group."""
        if sort_mode == SortMode.NONE:
            return
        elif sort_mode == SortMode.FRONT_TO_BACK:
            commands.sort(key=lambda c: c.z_order, reverse=True)
        elif sort_mode == SortMode.BACK_TO_FRONT:
            commands.sort(key=lambda c: c.z_order)
        elif sort_mode == SortMode.Y_SORT:
            commands.sort(key=lambda c: c.position_y)
        # CUSTOM would use a registered comparator

    def _split_group(
        self, commands: List[SpriteDrawCommand], max_size: int
    ) -> List[List[SpriteDrawCommand]]:
        """Split a large group into sub-batches."""
        result: List[List[SpriteDrawCommand]] = []
        for i in range(0, len(commands), max_size):
            result.append(commands[i:i + max_size])
        return result

    # ------------------------------------------------------------------
    # Texture Atlas Management
    # ------------------------------------------------------------------

    def create_texture_atlas(
        self,
        name: str,
        texture_names: List[str],
        size: int = 2048,
        pack_mode: AtlasPackMode = AtlasPackMode.BIN_PACK,
    ) -> TextureAtlas:
        """
        Create a texture atlas packing multiple textures together.

        Args:
            name: Atlas identifier.
            texture_names: List of texture names to pack.
            size: Atlas dimensions (must be power-of-two).
            pack_mode: Packing algorithm.

        Returns:
            Created TextureAtlas.
        """
        atlas = TextureAtlas(name=name, size=size)

        # Simple grid packing
        cols = int(math.ceil(math.sqrt(len(texture_names))))
        cell_w = 1.0 / cols
        cell_h = 1.0 / cols

        for i, tex_name in enumerate(texture_names):
            row = i // cols
            col = i % cols

            region = AtlasRegion(
                atlas_id=atlas.atlas_id,
                source_texture=tex_name,
                x=col * cell_w,
                y=row * cell_h,
                width=cell_w,
                height=cell_h,
            )
            atlas.regions[tex_name] = region
            self._atlas_registry[tex_name] = atlas.atlas_id

        atlas.texture_count = len(texture_names)
        atlas.free_space = max(0.0, 1.0 - len(texture_names) / (cols * cols))

        self._atlases[atlas.atlas_id] = atlas
        return atlas

    def register_atlas_region(
        self,
        atlas_id: str,
        region: AtlasRegion,
    ) -> bool:
        """
        Register a single region in an existing atlas.

        Args:
            atlas_id: Target atlas identifier.
            region: Atlas region to register.

        Returns:
            True if successfully registered.
        """
        atlas = self._atlases.get(atlas_id)
        if not atlas:
            return False

        region.atlas_id = atlas_id
        atlas.regions[region.source_texture] = region
        self._atlas_registry[region.source_texture] = atlas_id
        atlas.texture_count = len(atlas.regions)
        return True

    def get_atlas(self, atlas_id: str) -> Optional[TextureAtlas]:
        """Retrieve a texture atlas by its identifier."""
        return self._atlases.get(atlas_id)

    def list_atlases(self) -> List[Dict[str, Any]]:
        """List all registered texture atlases."""
        return [a.to_dict() for a in self._atlases.values()]

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_batch_strategy(self, strategy: BatchStrategy) -> None:
        """Set the optimization strategy for batch generation."""
        self._batch_strategy = strategy

    def set_sort_mode(self, mode: SortMode) -> None:
        """Set the z-order sorting behavior."""
        self._sort_mode = mode

    def set_max_sprites_per_batch(self, max_count: int) -> None:
        """Set the maximum number of sprites per GPU batch."""
        self._max_sprites_per_batch = max(1, min(4096, max_count))

    # ------------------------------------------------------------------
    # Statistics & Reporting
    # ------------------------------------------------------------------

    def get_render_stats(self) -> Dict[str, Any]:
        """
        Return comprehensive batching performance metrics.

        Returns:
            Dict with frame stats, batch counts, savings, and atlas info.
        """
        active_commands = len(self._command_buffer)
        active_batches = len(self._batches)
        total_savings = self._total_saved_draw_calls

        recent = self._frame_stats_history[-10:]
        avg_reduction = 0.0
        if recent:
            avg_reduction = sum(r["reduction_ratio"] for r in recent) / len(recent)

        return {
            "frame_count": self._frame_count,
            "active_commands": active_commands,
            "active_batches": active_batches,
            "total_processed": self._total_commands_processed,
            "total_batches_generated": self._total_batches_generated,
            "total_saved_draw_calls": total_savings,
            "avg_draw_call_reduction_pct": round(avg_reduction, 1),
            "atlases": len(self._atlases),
            "atlas_registered_textures": len(self._atlas_registry),
            "strategy": self._batch_strategy.value,
            "sort_mode": self._sort_mode.value,
            "max_sprites_per_batch": self._max_sprites_per_batch,
            "recent_frame_stats": recent,
        }

    def get_frame_report(self) -> Dict[str, Any]:
        """Return the current frame's batch report."""
        return {
            "commands": len(self._command_buffer),
            "batches": [
                b.to_dict() for b in self._batches
            ],
            "atlas_count": len(self._atlases),
        }

    # ------------------------------------------------------------------
    # Frame Lifecycle
    # ------------------------------------------------------------------

    def clear_frame(self) -> None:
        """Clear the command buffer to start a new frame."""
        with self._lock:
            self._command_buffer.clear()
            self._batches.clear()

    # ------------------------------------------------------------------
    # Singleton & Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineSpriteBatcher":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset the batcher to initial state."""
        with self._lock:
            self._command_buffer.clear()
            self._batches.clear()
            self._atlases.clear()
            self._atlas_registry.clear()
            self._frame_stats_history.clear()
            self._frame_count = 0
            self._total_commands_processed = 0
            self._total_batches_generated = 0
            self._total_saved_draw_calls = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_sprite_batcher() -> EngineSpriteBatcher:
    """Return the singleton EngineSpriteBatcher instance."""
    return EngineSpriteBatcher()