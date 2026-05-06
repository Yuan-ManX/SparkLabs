"""
SparkLabs Engine - Rendering Server

Abstract 2D rendering pipeline that decouples rendering logic from
game mechanics. Accepts draw commands from the engine and outputs
them to a backing canvas adaptor — enabling seamless targeting of
different rendering backends (Canvas2D, WebGL, SVG, headless).

Architecture:
  RenderingServer
    |-- DrawBatch (sorted command queue per frame)
    |-- CullingPass (viewport-against-AABB visibility check)
    |-- ZSorter (stable depth ordering for layered rendering)
    |-- ViewportTransform (world-space → screen-space matrix)
    |-- RenderTarget (off-screen buffer for post-processing)
    |-- CanvasAdaptor (backend interface for actual pixel output)

Draw Command Types:
  - RECT: filled or stroked rectangle with color/corner radius
  - CIRCLE: filled circle with center + radius
  - LINE: single segment with stroke width
  - POLYGON: arbitrary polygon fill
  - SPRITE: textured quad from a stored image
  - TEXT: glyph-based string rendering with font + size
  - CLEAR: clear entire viewport to a background color

Usage:
    server = RenderingServer()
    server.set_viewport(0, 0, 1920, 1080)
    server.begin_frame()
    server.draw_rect(10, 10, 100, 50, "red")
    server.draw_sprite("hero", 200, 100, 64, 64)
    server.end_frame()
    server.flush(canvas_context)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class DrawCommandType(Enum):
    RECT = "rect"
    CIRCLE = "circle"
    LINE = "line"
    POLYGON = "polygon"
    SPRITE = "sprite"
    TEXT = "text"
    CLEAR = "clear"


class BlendMode(Enum):
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"


class RenderLayer(Enum):
    BACKGROUND = 0
    TERRAIN = 10
    DECORATION = 20
    ENTITIES = 30
    PLAYER = 40
    FOREGROUND = 50
    OVERLAY = 60
    UI = 70
    DEBUG = 80


@dataclass
class Viewport:
    x: int = 0
    y: int = 0
    width: int = 1920
    height: int = 1080
    scale_x: float = 1.0
    scale_y: float = 1.0
    camera_x: float = 0.0
    camera_y: float = 0.0

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        return (self.camera_x, self.camera_y,
                self.camera_x + self.width / self.scale_x,
                self.camera_y + self.height / self.scale_y)


@dataclass
class DrawCommand:
    cmd_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cmd_type: DrawCommandType = DrawCommandType.RECT
    layer: int = 0
    z_index: int = 0
    aabb: Tuple[float, float, float, float] = (0, 0, 0, 0)
    fill_color: str = ""
    stroke_color: str = ""
    stroke_width: float = 0.0
    corner_radius: float = 0.0
    image_key: str = ""
    text_content: str = ""
    font_family: str = ""
    font_size: int = 14
    points: List[Tuple[float, float]] = field(default_factory=list)
    blend: BlendMode = BlendMode.NORMAL
    alpha: float = 1.0
    rotation_deg: float = 0.0
    visible: bool = True


@dataclass
class RenderTarget:
    target_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    width: int = 256
    height: int = 256
    commands: List[DrawCommand] = field(default_factory=list)
    dirty: bool = True


class RenderingServer:
    """Abstract 2D rendering pipeline with batched draw commands."""

    _instance: Optional["RenderingServer"] = None

    def __init__(self):
        self._viewport: Viewport = Viewport()
        self._frame_commands: List[DrawCommand] = []
        self._sprite_registry: Dict[str, Any] = {}
        self._render_targets: Dict[str, RenderTarget] = {}
        self._active_target: Optional[str] = None
        self._stats: Dict[str, int] = {"draw_calls": 0, "culled": 0, "frames": 0}
        self._enabled: bool = True
        self._clear_color: str = "#1a1a2e"
        self._max_draw_calls_per_frame: int = 5000

    @classmethod
    def get_instance(cls) -> "RenderingServer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_viewport(self, x: int, y: int, width: int, height: int,
                     scale: float = 1.0, cam_x: float = 0.0, cam_y: float = 0.0) -> None:
        self._viewport = Viewport(x=x, y=y, width=width, height=height,
                                  scale_x=scale, scale_y=scale, camera_x=cam_x, camera_y=cam_y)

    def register_sprite(self, key: str, image_data: Any) -> None:
        self._sprite_registry[key] = image_data

    def unregister_sprite(self, key: str) -> None:
        self._sprite_registry.pop(key, None)

    def create_render_target(self, key: str, width: int, height: int) -> RenderTarget:
        rt = RenderTarget(target_id=key, width=width, height=height)
        self._render_targets[key] = rt
        return rt

    def set_render_target(self, key: Optional[str]) -> None:
        self._active_target = key

    def begin_frame(self) -> None:
        self._frame_commands.clear()

    def _world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        sx = (wx - self._viewport.camera_x) * self._viewport.scale_x + self._viewport.x
        sy = (wy - self._viewport.camera_y) * self._viewport.scale_y + self._viewport.y
        return sx, sy

    def _is_visible(self, x: float, y: float, w: float, h: float) -> bool:
        vx, vy, vw, vh = self._viewport.bounds
        if x + w < vx or x > vx + vw:
            return False
        if y + h < vy or y > vy + vh:
            return False
        return True

    def _add_command(self, cmd: DrawCommand) -> None:
        if len(self._frame_commands) >= self._max_draw_calls_per_frame:
            return
        if not cmd.visible:
            self._stats["culled"] += 1
            return
        ax, ay, aw, ah = cmd.aabb
        if not self._is_visible(ax, ay, aw, ah):
            self._stats["culled"] += 1
            return
        self._frame_commands.append(cmd)
        self._stats["draw_calls"] += 1

    def clear(self, color: str = "") -> None:
        cmd = DrawCommand(
            cmd_type=DrawCommandType.CLEAR,
            fill_color=color or self._clear_color,
            aabb=(0, 0, self._viewport.width, self._viewport.height),
        )
        self._add_command(cmd)

    def draw_rect(self, x: float, y: float, w: float, h: float,
                  fill: str = "", stroke: str = "", stroke_width: float = 0.0,
                  corner_radius: float = 0.0, layer: int = 0, z: int = 0,
                  alpha: float = 1.0, rotation: float = 0.0, blend: BlendMode = BlendMode.NORMAL) -> None:
        cmd = DrawCommand(
            cmd_type=DrawCommandType.RECT,
            layer=layer, z_index=z,
            aabb=(x, y, w, h),
            fill_color=fill, stroke_color=stroke,
            stroke_width=stroke_width, corner_radius=corner_radius,
            alpha=alpha, rotation_deg=rotation, blend=blend,
        )
        self._add_command(cmd)

    def draw_circle(self, cx: float, cy: float, radius: float,
                    fill: str = "", stroke: str = "", stroke_width: float = 0.0,
                    layer: int = 0, z: int = 0, alpha: float = 1.0) -> None:
        r2 = radius * 2
        cmd = DrawCommand(
            cmd_type=DrawCommandType.CIRCLE,
            layer=layer, z_index=z,
            aabb=(cx - radius, cy - radius, r2, r2),
            fill_color=fill, stroke_color=stroke,
            stroke_width=stroke_width, alpha=alpha,
        )
        self._add_command(cmd)

    def draw_line(self, x1: float, y1: float, x2: float, y2: float,
                  stroke: str = "white", stroke_width: float = 1.0,
                  layer: int = 0, z: int = 0, alpha: float = 1.0) -> None:
        min_x = min(x1, x2)
        min_y = min(y1, y2)
        max_x = max(x1, x2)
        max_y = max(y1, y2)
        cmd = DrawCommand(
            cmd_type=DrawCommandType.LINE,
            layer=layer, z_index=z,
            aabb=(min_x, min_y, max_x - min_x, max_y - min_y),
            stroke_color=stroke, stroke_width=stroke_width, alpha=alpha,
            points=[(x1, y1), (x2, y2)],
        )
        self._add_command(cmd)

    def draw_polygon(self, points: List[Tuple[float, float]],
                     fill: str = "", stroke: str = "", stroke_width: float = 0.0,
                     layer: int = 0, z: int = 0, alpha: float = 1.0) -> None:
        if not points or len(points) < 3:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        cmd = DrawCommand(
            cmd_type=DrawCommandType.POLYGON,
            layer=layer, z_index=z,
            aabb=(min_x, min_y, max_x - min_x, max_y - min_y),
            fill_color=fill, stroke_color=stroke,
            stroke_width=stroke_width, alpha=alpha,
            points=points,
        )
        self._add_command(cmd)

    def draw_sprite(self, image_key: str, x: float, y: float,
                    w: float, h: float, layer: int = 0, z: int = 0,
                    alpha: float = 1.0, rotation: float = 0.0,
                    blend: BlendMode = BlendMode.NORMAL) -> None:
        cmd = DrawCommand(
            cmd_type=DrawCommandType.SPRITE,
            layer=layer, z_index=z,
            aabb=(x, y, w, h),
            image_key=image_key, alpha=alpha,
            rotation_deg=rotation, blend=blend,
        )
        self._add_command(cmd)

    def draw_text(self, text: str, x: float, y: float,
                  font: str = "sans-serif", size: int = 14,
                  fill: str = "white", layer: int = RenderLayer.UI.value,
                  z: int = 0, alpha: float = 1.0) -> None:
        cmd = DrawCommand(
            cmd_type=DrawCommandType.TEXT,
            layer=layer, z_index=z,
            aabb=(x, y, len(text) * size * 0.6, size * 1.4),
            fill_color=fill, font_family=font,
            font_size=size, alpha=alpha,
            text_content=text,
        )
        self._add_command(cmd)

    def end_frame(self) -> None:
        self._stats["frames"] += 1

    def get_commands(self) -> List[DrawCommand]:
        return sorted(self._frame_commands,
                       key=lambda c: (c.layer, c.z_index, c.aabb[1]))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "draw_calls": self._stats["draw_calls"],
            "culled": self._stats["culled"],
            "frames": self._stats["frames"],
            "sprites_registered": len(self._sprite_registry),
            "render_targets": len(self._render_targets),
            "active_target": self._active_target,
            "viewport": {
                "width": self._viewport.width,
                "height": self._viewport.height,
                "scale": self._viewport.scale_x,
                "camera": (self._viewport.camera_x, self._viewport.camera_y),
            },
            "max_draw_calls": self._max_draw_calls_per_frame,
            "enabled": self._enabled,
        }

    def get_frame_draw_count(self) -> int:
        return len(self._frame_commands)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def reset_stats(self) -> None:
        self._stats = {"draw_calls": 0, "culled": 0, "frames": 0}


def get_rendering_server() -> RenderingServer:
    return RenderingServer.get_instance()
