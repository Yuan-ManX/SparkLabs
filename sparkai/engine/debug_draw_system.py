"""
SparkLabs Engine - Debug Draw System

Runtime debug visualization system for the SparkLabs AI-native
game engine. Provides immediate-mode drawing primitives for
visualizing collision shapes, AI paths, physics forces, spatial
partitions, and other internal engine state during development.
Supports wireframe, solid, and text overlays with configurable
categories and per-category visibility toggles.

Architecture:
  DebugDrawSystem
    |-- DebugDrawCommand (single draw instruction)
    |-- DrawCategory (grouping: physics, ai, rendering, input)
    |-- DebugTextOverlay (on-screen debug text labels)
    |-- DrawBatcher (optimizes multiple draw calls per category)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, Flag, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class DrawCategory(Flag):
    NONE = 0
    PHYSICS = auto()
    AI = auto()
    PATHFINDING = auto()
    RENDERING = auto()
    COLLISION = auto()
    GAMEPLAY = auto()
    NETWORK = auto()
    ANIMATION = auto()
    ALL = PHYSICS | AI | PATHFINDING | RENDERING | COLLISION | GAMEPLAY | NETWORK | ANIMATION


class DrawPrimitive(Enum):
    LINE = "line"
    CIRCLE = "circle"
    RECT = "rect"
    ARROW = "arrow"
    POINT = "point"
    TEXT = "text"
    POLYGON = "polygon"
    GRID = "grid"


@dataclass
class DebugDrawCommand:
    cmd_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    primitive: DrawPrimitive = DrawPrimitive.LINE
    category: DrawCategory = DrawCategory.PHYSICS
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    radius: float = 10.0
    width: float = 100.0
    height: float = 100.0
    color: Tuple[int, int, int, int] = (0, 255, 0, 200)
    thickness: float = 1.0
    fill: bool = False
    text: str = ""
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    layer: int = 0
    persistent: bool = False

    def is_expired(self) -> bool:
        if self.duration <= 0:
            return False
        return (time.time() - self.timestamp) > self.duration

    def to_dict(self) -> dict:
        return {
            "cmd_id": self.cmd_id,
            "primitive": self.primitive.value,
            "category": [c.name for c in DrawCategory if c.value & self.category.value],
            "x1": self.x1,
            "y1": self.y1,
            "color": list(self.color),
            "thickness": self.thickness,
        }


class DebugDrawSystem:
    """
    Immediate-mode debug draw system for engine development visualization.

    Provides fast drawing commands for visualizing internal engine state.
    Supports categorized commands with per-category visibility toggling,
    automatic expiration for transient visualizations, persistent overlays
    for long-running state monitoring, and performance-optimized batching
    to minimize draw call overhead during debugging sessions.
    """

    _instance: Optional["DebugDrawSystem"] = None

    def __init__(self):
        self._commands: List[DebugDrawCommand] = []
        self._persistent: Dict[str, DebugDrawCommand] = {}
        self._visible_categories: DrawCategory = DrawCategory.ALL
        self._enabled: bool = False
        self._max_commands: int = 5000
        self._text_overlays: Dict[str, str] = {}
        self._cached_batches: Dict[DrawCategory, List[dict]] = {}

    @classmethod
    def get_instance(cls) -> "DebugDrawSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def show_category(self, category: DrawCategory) -> None:
        self._visible_categories |= category

    def hide_category(self, category: DrawCategory) -> None:
        self._visible_categories &= ~category

    def is_visible(self, category: DrawCategory) -> bool:
        return bool(self._visible_categories & category)

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, color: Tuple[int, int, int, int] = (0, 255, 0, 200), category: DrawCategory = DrawCategory.PHYSICS, thickness: float = 1.0, duration: float = 0.0) -> str:
        cmd = DebugDrawCommand(primitive=DrawPrimitive.LINE, category=category, x1=x1, y1=y1, x2=x2, y2=y2, color=color, thickness=thickness, duration=duration)
        self._commands.append(cmd)
        return cmd.cmd_id

    def draw_circle(self, cx: float, cy: float, radius: float, color: Tuple[int, int, int, int] = (0, 255, 0, 200), category: DrawCategory = DrawCategory.PHYSICS, fill: bool = False, duration: float = 0.0) -> str:
        cmd = DebugDrawCommand(primitive=DrawPrimitive.CIRCLE, category=category, x1=cx, y1=cy, radius=radius, color=color, fill=fill, duration=duration)
        self._commands.append(cmd)
        return cmd.cmd_id

    def draw_rect(self, x: float, y: float, width: float, height: float, color: Tuple[int, int, int, int] = (0, 255, 0, 200), category: DrawCategory = DrawCategory.PHYSICS, fill: bool = False, duration: float = 0.0) -> str:
        cmd = DebugDrawCommand(primitive=DrawPrimitive.RECT, category=category, x1=x, y1=y, width=width, height=height, color=color, fill=fill, duration=duration)
        self._commands.append(cmd)
        return cmd.cmd_id

    def draw_arrow(self, x1: float, y1: float, x2: float, y2: float, color: Tuple[int, int, int, int] = (255, 100, 0, 200), category: DrawCategory = DrawCategory.PHYSICS, duration: float = 0.0) -> str:
        cmd = DebugDrawCommand(primitive=DrawPrimitive.ARROW, category=category, x1=x1, y1=y1, x2=x2, y2=y2, color=color, duration=duration)
        self._commands.append(cmd)
        return cmd.cmd_id

    def draw_point(self, x: float, y: float, color: Tuple[int, int, int, int] = (255, 255, 0, 255), category: DrawCategory = DrawCategory.PHYSICS, radius: float = 3.0, duration: float = 0.0) -> str:
        cmd = DebugDrawCommand(primitive=DrawPrimitive.POINT, category=category, x1=x, y1=y, radius=radius, color=color, duration=duration)
        self._commands.append(cmd)
        return cmd.cmd_id

    def draw_polygon(self, points: List[Tuple[float, float]], color: Tuple[int, int, int, int] = (0, 255, 0, 200), category: DrawCategory = DrawCategory.PHYSICS, fill: bool = False, duration: float = 0.0) -> str:
        cmd = DebugDrawCommand(primitive=DrawPrimitive.POLYGON, category=category, color=color, fill=fill, duration=duration)
        cmd.text = str(points)
        self._commands.append(cmd)
        return cmd.cmd_id

    def draw_grid(self, x: float, y: float, cell_size: float, cols: int, rows: int, color: Tuple[int, int, int, int] = (60, 60, 60, 100), category: DrawCategory = DrawCategory.RENDERING) -> str:
        cmd = DebugDrawCommand(primitive=DrawPrimitive.GRID, category=category, x1=x, y1=y, width=float(cols), height=float(rows), radius=cell_size, color=color)
        self._commands.append(cmd)
        return cmd.cmd_id

    def draw_text(self, x: float, y: float, text: str, color: Tuple[int, int, int, int] = (255, 255, 255, 255), category: DrawCategory = DrawCategory.GAMEPLAY, duration: float = 0.0) -> str:
        cmd = DebugDrawCommand(primitive=DrawPrimitive.TEXT, category=category, x1=x, y1=y, text=text, color=color, duration=duration)
        self._commands.append(cmd)
        return cmd.cmd_id

    def set_text_overlay(self, key: str, text: str) -> None:
        self._text_overlays[key] = text

    def remove_text_overlay(self, key: str) -> None:
        self._text_overlays.pop(key, None)

    def clear(self, category: Optional[DrawCategory] = None) -> None:
        if category is None:
            self._commands.clear()
        else:
            self._commands = [c for c in self._commands if c.category != category]

    def clear_expired(self) -> int:
        before = len(self._commands)
        self._commands = [c for c in self._commands if not c.is_expired()]
        return before - len(self._commands)

    def get_visible_commands(self) -> List[DebugDrawCommand]:
        self.clear_expired()
        if not self._enabled:
            return []
        return [c for c in self._commands if self.is_visible(c.category)]

    def get_commands_by_category(self, category: DrawCategory) -> List[DebugDrawCommand]:
        return [c for c in self._commands if c.category == category]

    def get_stats(self) -> dict:
        category_counts = {}
        for cat in DrawCategory:
            if cat != DrawCategory.NONE and cat != DrawCategory.ALL:
                count = sum(1 for c in self._commands if c.category == cat)
                if count > 0:
                    category_counts[cat.name] = count
        return {
            "enabled": self._enabled,
            "total_commands": len(self._commands),
            "visible_categories": [c.name for c in DrawCategory if c != DrawCategory.NONE and self._visible_categories & c],
            "category_counts": category_counts,
            "text_overlays": len(self._text_overlays),
            "max_commands": self._max_commands,
        }

    def reset(self) -> None:
        self._commands.clear()
        self._persistent.clear()
        self._text_overlays.clear()
        self._enabled = False
        self._visible_categories = DrawCategory.ALL


def get_debug_draw_system() -> DebugDrawSystem:
    return DebugDrawSystem.get_instance()
