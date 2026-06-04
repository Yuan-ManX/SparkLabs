"""
SparkAI Engine - Mega Sprite Layer System

High-performance GPU batch rendering for massive sprite counts.
Inspired by modern GPU-driven rendering architectures, this system
enables rendering of millions of sprites through single-pass draw
calls, GPU-resident vertex buffers, and instance-based rendering.

Supports per-sprite animations, scrolling, filtering, and dynamic
batching strategies for maximum throughput across different hardware
profiles.
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MegaSpriteBlendMode(str, Enum):
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    HARD_LIGHT = "hard_light"
    ALPHA_MASK = "alpha_mask"


class MegaSpriteSortMode(str, Enum):
    NONE = "none"
    BACK_TO_FRONT = "back_to_front"
    FRONT_TO_BACK = "front_to_back"
    TEXTURE_ATLAS = "texture_atlas"
    DISTANCE = "distance"


class GPUBufferStrategy(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    STREAMING = "streaming"
    PERSISTENT = "persistent"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MegaSpriteLayerConfig:
    """Configuration for a mega sprite layer."""
    layer_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    max_sprites: int = 100000
    texture_atlas_id: str = ""
    blend_mode: MegaSpriteBlendMode = MegaSpriteBlendMode.NORMAL
    sort_mode: MegaSpriteSortMode = MegaSpriteSortMode.NONE
    buffer_strategy: GPUBufferStrategy = GPUBufferStrategy.DYNAMIC
    is_visible: bool = True
    layer_depth: float = 0.0
    scroll_factor: Tuple[float, float] = (1.0, 1.0)
    sprite_count: int = 0
    gpu_buffer_size_bytes: int = 0
    draw_call_count: int = 0
    last_frame_duration_us: float = 0.0
    total_frames_rendered: int = 0
    is_dirty: bool = True
    use_instanced_rendering: bool = True
    instance_buffer_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "max_sprites": self.max_sprites,
            "texture_atlas_id": self.texture_atlas_id,
            "blend_mode": self.blend_mode.value,
            "sort_mode": self.sort_mode.value,
            "buffer_strategy": self.buffer_strategy.value,
            "is_visible": self.is_visible,
            "layer_depth": self.layer_depth,
            "scroll_factor": list(self.scroll_factor),
            "sprite_count": self.sprite_count,
            "gpu_buffer_size_bytes": self.gpu_buffer_size_bytes,
            "draw_call_count": self.draw_call_count,
            "last_frame_duration_us": self.last_frame_duration_us,
            "total_frames_rendered": self.total_frames_rendered,
            "use_instanced_rendering": self.use_instanced_rendering,
        }


@dataclass
class MegaSpriteInstance:
    """A single sprite instance in the mega layer."""
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    layer_id: str = ""
    texture_frame: int = 0
    position_x: float = 0.0
    position_y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    alpha: float = 1.0
    tint_r: int = 255
    tint_g: int = 255
    tint_b: int = 255
    scroll_factor_x: float = 1.0
    scroll_factor_y: float = 1.0
    is_visible: bool = True
    gpu_buffer_index: int = -1
    animation_state: str = "idle"
    animation_frame: int = 0
    animation_speed: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "layer_id": self.layer_id,
            "texture_frame": self.texture_frame,
            "position": [self.position_x, self.position_y],
            "rotation": self.rotation,
            "scale": [self.scale_x, self.scale_y],
            "alpha": self.alpha,
            "tint": [self.tint_r, self.tint_g, self.tint_b],
            "scroll_factor": [self.scroll_factor_x, self.scroll_factor_y],
            "is_visible": self.is_visible,
            "animation_state": self.animation_state,
        }


@dataclass
class GPUVertexBatch:
    """Represents a vertex batch to be submitted to GPU."""
    batch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    layer_id: str = ""
    vertex_count: int = 0
    index_count: int = 0
    draw_mode: str = "triangles"
    is_static: bool = False
    gpu_handle: int = 0
    last_upload_time: float = 0.0
    upload_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "layer_id": self.layer_id,
            "vertex_count": self.vertex_count,
            "index_count": self.index_count,
            "draw_mode": self.draw_mode,
            "is_static": self.is_static,
            "upload_size_bytes": self.upload_size_bytes,
        }


# ---------------------------------------------------------------------------
# Mega Sprite Layer System
# ---------------------------------------------------------------------------

class EngineMegaSpriteLayer:
    """
    High-performance mega sprite rendering system.

    Designed for rendering massive sprite counts (100K-1M+) using
    GPU-instanced rendering, persistent vertex buffers, and smart
    batching strategies to minimize draw calls and CPU-GPU transfers.
    """

    _instance: Optional["EngineMegaSpriteLayer"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineMegaSpriteLayer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineMegaSpriteLayer":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._layers: Dict[str, MegaSpriteLayerConfig] = {}
        self._sprites: Dict[str, Dict[str, MegaSpriteInstance]] = {}
        self._batches: Dict[str, List[GPUVertexBatch]] = {}
        self._total_sprites_rendered: int = 0
        self._total_draw_calls: int = 0
        # Estimated GPU buffer sizes based on sprite data
        self._BYTES_PER_SPRITE: int = 64  # position(8) + uv(8) + color(4) + misc

    # ------------------------------------------------------------------
    # Layer Management
    # ------------------------------------------------------------------

    def create_layer(
        self, name: str, max_sprites: int = 100000,
        texture_atlas_id: str = "",
        blend_mode: MegaSpriteBlendMode = MegaSpriteBlendMode.NORMAL,
        sort_mode: MegaSpriteSortMode = MegaSpriteSortMode.NONE,
        buffer_strategy: GPUBufferStrategy = GPUBufferStrategy.DYNAMIC,
        use_instanced_rendering: bool = True,
        scroll_factor: Tuple[float, float] = (1.0, 1.0),
    ) -> MegaSpriteLayerConfig:
        """Create a mega sprite layer configuration."""
        with self._lock:
            layer = MegaSpriteLayerConfig(
                name=name,
                max_sprites=max_sprites,
                texture_atlas_id=texture_atlas_id,
                blend_mode=blend_mode,
                sort_mode=sort_mode,
                buffer_strategy=buffer_strategy,
                use_instanced_rendering=use_instanced_rendering,
                scroll_factor=scroll_factor,
            )
            layer.gpu_buffer_size_bytes = max_sprites * self._BYTES_PER_SPRITE
            layer.instance_buffer_size = max_sprites
            self._layers[layer.layer_id] = layer
            self._sprites[layer.layer_id] = {}
            self._batches[layer.layer_id] = []
            return layer

    def remove_layer(self, layer_id: str) -> bool:
        """Remove a mega sprite layer and all its resources."""
        with self._lock:
            layer = self._layers.pop(layer_id, None)
            if layer:
                self._sprites.pop(layer_id, None)
                self._batches.pop(layer_id, None)
                return True
            return False

    # ------------------------------------------------------------------
    # Sprite Management
    # ------------------------------------------------------------------

    def add_sprite(
        self, layer_id: str, texture_frame: int,
        position: Tuple[float, float],
        rotation: float = 0.0,
        scale: Union[float, Tuple[float, float]] = 1.0,
        alpha: float = 1.0,
        tint: Tuple[int, int, int] = (255, 255, 255),
        scroll_factor: Optional[Tuple[float, float]] = None,
        animation_state: str = "idle",
        animation_speed: float = 1.0,
    ) -> Optional[MegaSpriteInstance]:
        """Add a sprite instance to a mega layer."""
        with self._lock:
            layer = self._get_layer(layer_id)
            if not layer:
                return None
            if layer.sprite_count >= layer.max_sprites:
                return None

            scale_tuple = scale if isinstance(scale, tuple) else (scale, scale)
            sf = scroll_factor or layer.scroll_factor

            instance = MegaSpriteInstance(
                layer_id=layer_id,
                texture_frame=texture_frame,
                position_x=position[0],
                position_y=position[1],
                rotation=rotation,
                scale_x=scale_tuple[0],
                scale_y=scale_tuple[1],
                alpha=alpha,
                tint_r=tint[0],
                tint_g=tint[1],
                tint_b=tint[2],
                scroll_factor_x=sf[0],
                scroll_factor_y=sf[1],
                animation_state=animation_state,
                animation_speed=animation_speed,
            )

            self._sprites[layer_id][instance.instance_id] = instance
            layer.sprite_count = len(self._sprites[layer_id])
            layer.is_dirty = True
            self._total_sprites_rendered += 1
            return instance

    def add_bulk_sprites(
        self, layer_id: str,
        sprite_descriptions: List[Dict[str, Any]],
    ) -> List[str]:
        """Bulk-add multiple sprites to a layer efficiently."""
        with self._lock:
            ids: List[str] = []
            layer = self._get_layer(layer_id)
            if not layer:
                return ids
            remaining = layer.max_sprites - layer.sprite_count
            for i, desc in enumerate(sprite_descriptions):
                if i >= remaining:
                    break
                instance = self.add_sprite(
                    layer_id=layer_id,
                    texture_frame=desc.get("texture_frame", 0),
                    position=tuple(desc.get("position", (0, 0))),
                    rotation=desc.get("rotation", 0.0),
                    scale=desc.get("scale", 1.0),
                    alpha=desc.get("alpha", 1.0),
                    tint=tuple(desc.get("tint", (255, 255, 255))),
                    animation_state=desc.get("animation_state", "idle"),
                )
                if instance:
                    ids.append(instance.instance_id)
            return ids

    def remove_sprite(self, layer_id: str, instance_id: str) -> bool:
        """Remove a sprite instance from a layer."""
        with self._lock:
            sprites = self._sprites.get(layer_id, {})
            if instance_id in sprites:
                del sprites[instance_id]
                layer = self._get_layer(layer_id)
                if layer:
                    layer.sprite_count = len(sprites)
                    layer.is_dirty = True
                return True
            return False

    def update_sprite(
        self, layer_id: str, instance_id: str,
        position: Optional[Tuple[float, float]] = None,
        rotation: Optional[float] = None,
        scale: Optional[Union[float, Tuple[float, float]]] = None,
        alpha: Optional[float] = None,
        tint: Optional[Tuple[int, int, int]] = None,
        texture_frame: Optional[int] = None,
        is_visible: Optional[bool] = None,
    ) -> bool:
        """Update an existing sprite instance."""
        with self._lock:
            sprites = self._sprites.get(layer_id, {})
            instance = sprites.get(instance_id)
            if not instance:
                return False

            if position is not None:
                instance.position_x = position[0]
                instance.position_y = position[1]
            if rotation is not None:
                instance.rotation = rotation
            if scale is not None:
                st = scale if isinstance(scale, tuple) else (scale, scale)
                instance.scale_x = st[0]
                instance.scale_y = st[1]
            if alpha is not None:
                instance.alpha = max(0.0, min(1.0, alpha))
            if tint is not None:
                instance.tint_r = tint[0]
                instance.tint_g = tint[1]
                instance.tint_b = tint[2]
            if texture_frame is not None:
                instance.texture_frame = texture_frame
            if is_visible is not None:
                instance.is_visible = is_visible

            layer = self._get_layer(layer_id)
            if layer:
                layer.is_dirty = True
            return True

    # ------------------------------------------------------------------
    # Batch Management
    # ------------------------------------------------------------------

    def build_batches(self, layer_id: str) -> List[GPUVertexBatch]:
        """Build GPU vertex batches for a layer."""
        with self._lock:
            layer = self._get_layer(layer_id)
            if not layer:
                return []

            sprites = self._sprites.get(layer_id, {})
            visible_sprites = [
                s for s in sprites.values() if s.is_visible
            ]
            if not visible_sprites:
                self._batches[layer_id] = []
                return []

            # Sort sprites based on sort mode
            if layer.sort_mode == MegaSpriteSortMode.BACK_TO_FRONT:
                visible_sprites.sort(key=lambda s: s.position_y)
            elif layer.sort_mode == MegaSpriteSortMode.FRONT_TO_BACK:
                visible_sprites.sort(key=lambda s: -s.position_y)
            elif layer.sort_mode == MegaSpriteSortMode.TEXTURE_ATLAS:
                visible_sprites.sort(key=lambda s: s.texture_frame)

            # Build batch
            batch = GPUVertexBatch(
                layer_id=layer_id,
                vertex_count=len(visible_sprites) * 4,  # 4 vertices per sprite
                index_count=len(visible_sprites) * 6,   # 6 indices per sprite
                is_static=(layer.buffer_strategy == GPUBufferStrategy.STATIC),
                upload_size_bytes=len(visible_sprites) * self._BYTES_PER_SPRITE,
            )

            self._batches[layer_id] = [batch]
            layer.draw_call_count = len(self._batches[layer_id])
            layer.last_frame_duration_us = max(
                1, len(visible_sprites) * 0.01
            )  # Simulated
            layer.total_frames_rendered += 1
            layer.is_dirty = False
            return self._batches[layer_id]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_frame(
        self, layer_id: str,
        camera_position: Tuple[float, float] = (0, 0),
        camera_zoom: float = 1.0,
        viewport_size: Tuple[float, float] = (1920, 1080),
    ) -> Dict[str, Any]:
        """Simulate a frame render for a mega sprite layer."""
        with self._lock:
            layer = self._get_layer(layer_id)
            if not layer or not layer.is_visible:
                return {"rendered": False, "sprites_visible": 0}

            sprites = self._sprites.get(layer_id, {})
            visible = []

            # Frustum culling
            hw = viewport_size[0] / 2 / max(camera_zoom, 0.001)
            hh = viewport_size[1] / 2 / max(camera_zoom, 0.001)
            min_x = camera_position[0] - hw - 100
            max_x = camera_position[0] + hw + 100
            min_y = camera_position[1] - hh - 100
            max_y = camera_position[1] + hh + 100

            for s in sprites.values():
                if not s.is_visible:
                    continue
                sx = s.position_x * s.scroll_factor_x
                sy = s.position_y * s.scroll_factor_y
                if min_x <= sx <= max_x and min_y <= sy <= max_y:
                    visible.append(s.instance_id)

            if layer.is_dirty:
                self.build_batches(layer_id)

            return {
                "rendered": True,
                "layer_name": layer.name,
                "sprites_total": len(sprites),
                "sprites_visible": len(visible),
                "sprites_culled": len(sprites) - len(visible),
                "draw_calls": layer.draw_call_count,
                "frame_time_us": layer.last_frame_duration_us,
                "gpu_buffer_mb": layer.gpu_buffer_size_bytes / (1024 * 1024),
                "camera_position": list(camera_position),
            }

    def get_layer_stats(self, layer_id: str) -> Dict[str, Any]:
        """Get statistics for a specific layer."""
        with self._lock:
            layer = self._get_layer(layer_id)
            if not layer:
                return {"error": "Layer not found"}
            return {
                "layer": layer.to_dict(),
                "sprite_count": layer.sprite_count,
                "max_sprites": layer.max_sprites,
                "utilization_percent": round(
                    (layer.sprite_count / max(layer.max_sprites, 1)) * 100, 2
                ),
                "gpu_buffer_mb": round(
                    layer.gpu_buffer_size_bytes / (1024 * 1024), 2
                ),
                "batch_count": len(self._batches.get(layer_id, [])),
            }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        with self._lock:
            total_sprites = sum(l.sprite_count for l in self._layers.values())
            total_capacity = sum(l.max_sprites for l in self._layers.values())
            total_gpu_mb = sum(
                l.gpu_buffer_size_bytes for l in self._layers.values()
            ) / (1024 * 1024)
            return {
                "layer_count": len(self._layers),
                "total_sprites": total_sprites,
                "total_capacity": total_capacity,
                "total_sprites_rendered": self._total_sprites_rendered,
                "total_gpu_buffer_mb": round(total_gpu_mb, 2),
                "utilization_percent": round(
                    (total_sprites / max(total_capacity, 1)) * 100, 2
                ),
                "layers": [
                    {
                        "name": l.name,
                        "sprites": l.sprite_count,
                        "capacity": l.max_sprites,
                        "dirty": l.is_dirty,
                    }
                    for l in self._layers.values()
                ],
            }

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def generate_sprite_grid(
        self, layer_id: str, rows: int = 50, cols: int = 50,
        spacing: float = 32.0, start_x: float = 0.0, start_y: float = 0.0,
        texture_frames: int = 4, random_rotation: bool = False,
        random_alpha: bool = False,
    ) -> int:
        """Generate a grid of sprites for stress testing."""
        with self._lock:
            layer = self._get_layer(layer_id)
            if not layer:
                return 0

            import random
            count = 0
            for row in range(rows):
                for col in range(cols):
                    if count >= layer.max_sprites:
                        break
                    x = start_x + col * spacing
                    y = start_y + row * spacing
                    rot = random.uniform(0, 360) if random_rotation else 0.0
                    alpha_val = random.uniform(0.5, 1.0) if random_alpha else 1.0
                    frame = col % texture_frames
                    self.add_sprite(
                        layer_id=layer_id,
                        texture_frame=frame,
                        position=(x, y),
                        rotation=rot,
                        alpha=alpha_val,
                    )
                    count += 1
            return count

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _get_layer(self, layer_id: str) -> Optional[MegaSpriteLayerConfig]:
        return self._layers.get(layer_id)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_mega_sprite_layer() -> EngineMegaSpriteLayer:
    return EngineMegaSpriteLayer.get_instance()