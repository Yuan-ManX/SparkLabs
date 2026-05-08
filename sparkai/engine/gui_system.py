"""
SparkLabs Engine - GUI System

Retained-mode GUI widget system for the SparkLabs AI-native
game engine. Provides a hierarchical widget tree with layout,
styling, and event handling. AI agents can construct game UIs
programmatically through a declarative widget API including
containers, buttons, labels, sliders, and input fields.

Architecture:
  GUISystem
    |-- Widget (base class with rect, visibility, z-order)
    |-- Container (stacks children with layout policy)
    |-- Label (text rendering with alignment options)
    |-- Button (clickable with hover/press states)
    |-- Slider (value bar with drag interaction)
    |-- TextInput (keyboard-capturing text field)
    |-- Image (sprite-based display widget)
    |-- LayoutEngine (auto-sizing and constraint resolution)
    |-- ThemeManager (shared color/font/style presets)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class WidgetAxis(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class TextAlign(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class WidgetState(Enum):
    NORMAL = "normal"
    HOVERED = "hovered"
    PRESSED = "pressed"
    DISABLED = "disabled"
    FOCUSED = "focused"


class LayoutMode(Enum):
    NONE = "none"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    GRID = "grid"
    ANCHOR = "anchor"


@dataclass
class WidgetStyle:
    background_color: Tuple[int, int, int, int] = (40, 40, 40, 255)
    foreground_color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    border_color: Tuple[int, int, int, int] = (80, 80, 80, 255)
    border_width: int = 1
    corner_radius: int = 0
    font_size: int = 14
    padding: Tuple[int, int, int, int] = (4, 4, 4, 4)
    opacity: float = 1.0

    def to_dict(self) -> dict:
        return {
            "background_color": list(self.background_color),
            "foreground_color": list(self.foreground_color),
            "border_color": list(self.border_color),
            "border_width": self.border_width,
            "corner_radius": self.corner_radius,
            "font_size": self.font_size,
            "padding": list(self.padding),
            "opacity": self.opacity,
        }


@dataclass
class Widget:
    widget_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "widget"
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 30.0
    visible: bool = True
    enabled: bool = True
    z_index: int = 0
    alpha: float = 1.0
    state: WidgetState = WidgetState.NORMAL
    style: WidgetStyle = field(default_factory=WidgetStyle)
    tooltip: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    _on_click: Optional[Callable] = None
    _on_hover: Optional[Callable] = None
    _on_change: Optional[Callable] = None

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def to_dict(self) -> dict:
        return {
            "id": self.widget_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "visible": self.visible,
            "enabled": self.enabled,
            "z_index": self.z_index,
            "state": self.state.value,
            "type": type(self).__name__,
        }

    def set_click_handler(self, handler: Callable) -> None:
        self._on_click = handler

    def set_hover_handler(self, handler: Callable) -> None:
        self._on_hover = handler

    def set_change_handler(self, handler: Callable) -> None:
        self._on_change = handler


@dataclass
class Container(Widget):
    children: List[Widget] = field(default_factory=list)
    layout: LayoutMode = LayoutMode.VERTICAL
    spacing: float = 4.0
    scrollable: bool = False
    scroll_x: float = 0.0
    scroll_y: float = 0.0

    def add(self, widget: Widget) -> Widget:
        self.children.append(widget)
        self._apply_layout()
        return widget

    def remove(self, widget_id: str) -> bool:
        for i, child in enumerate(self.children):
            if child.widget_id == widget_id:
                del self.children[i]
                self._apply_layout()
                return True
        return False

    def find(self, widget_id: str) -> Optional[Widget]:
        for child in self.children:
            if child.widget_id == widget_id:
                return child
        return None

    def find_recursive(self, widget_id: str) -> Optional[Widget]:
        result = self.find(widget_id)
        if result:
            return result
        for child in self.children:
            if isinstance(child, Container):
                result = child.find_recursive(widget_id)
                if result:
                    return result
        return None

    def clear(self) -> None:
        self.children.clear()

    def _apply_layout(self) -> None:
        if self.layout == LayoutMode.VERTICAL:
            y_offset = self.spacing
            for child in self.children:
                child.x = self.spacing
                child.y = y_offset
                child.width = self.width - self.spacing * 2
                y_offset += child.height + self.spacing
        elif self.layout == LayoutMode.HORIZONTAL:
            x_offset = self.spacing
            for child in self.children:
                child.x = x_offset
                child.y = self.spacing
                child.height = self.height - self.spacing * 2
                x_offset += child.width + self.spacing

    def get_all_descendants(self) -> List[Widget]:
        result = list(self.children)
        for child in self.children:
            if isinstance(child, Container):
                result.extend(child.get_all_descendants())
        return result

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["type"] = "container"
        base["children"] = [c.to_dict() for c in self.children]
        base["layout"] = self.layout.value
        base["child_count"] = len(self.children)
        return base


@dataclass
class Label(Widget):
    text: str = "Label"
    text_align: TextAlign = TextAlign.LEFT
    word_wrap: bool = False
    max_lines: int = 0

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["type"] = "label"
        base["text"] = self.text
        base["text_align"] = self.text_align.value
        return base


@dataclass
class Button(Widget):
    text: str = "Button"
    icon_name: str = ""

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["type"] = "button"
        base["text"] = self.text
        return base


@dataclass
class Slider(Widget):
    value: float = 0.0
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 1.0
    show_value: bool = True
    axis: WidgetAxis = WidgetAxis.HORIZONTAL

    def set_value(self, val: float) -> None:
        self.value = max(self.min_value, min(self.max_value, val))
        if self._on_change:
            self._on_change(self.value)

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["type"] = "slider"
        base["value"] = self.value
        base["min_value"] = self.min_value
        base["max_value"] = self.max_value
        return base


@dataclass
class TextInput(Widget):
    text: str = ""
    placeholder: str = ""
    max_length: int = 256
    password_mode: bool = False

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["type"] = "text_input"
        base["text"] = self.text
        base["placeholder"] = self.placeholder
        return base


@dataclass
class Image(Widget):
    texture_path: str = ""
    tint_color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    keep_aspect: bool = False

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["type"] = "image"
        base["texture_path"] = self.texture_path
        return base


@dataclass
class Theme:
    name: str = "default"
    primary_color: Tuple[int, int, int, int] = (70, 130, 230, 255)
    secondary_color: Tuple[int, int, int, int] = (100, 100, 100, 255)
    background_color: Tuple[int, int, int, int] = (30, 30, 30, 255)
    text_color: Tuple[int, int, int, int] = (240, 240, 240, 255)
    accent_color: Tuple[int, int, int, int] = (255, 180, 50, 255)
    error_color: Tuple[int, int, int, int] = (220, 60, 60, 255)
    success_color: Tuple[int, int, int, int] = (60, 180, 80, 255)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "primary_color": list(self.primary_color),
            "secondary_color": list(self.secondary_color),
            "background_color": list(self.background_color),
            "text_color": list(self.text_color),
            "accent_color": list(self.accent_color),
            "error_color": list(self.error_color),
            "success_color": list(self.success_color),
        }


class GUISystem:
    """
    Retained-mode GUI widget system for game interfaces.

    Provides a hierarchical widget tree that AI agents can
    construct programmatically. Supports containers with
    automatic layout, styled widgets, and event routing.
    Integrates with the engine's rendering pipeline for
    drawing and the input system for interaction.
    """

    _instance: Optional["GUISystem"] = None

    def __init__(self):
        self._root: Optional[Container] = None
        self._themes: Dict[str, Theme] = {}
        self._active_theme: str = "default"
        self._widget_count: int = 0
        self._focus_widget: Optional[str] = None
        self._hover_widget: Optional[str] = None
        self._init_defaults()

    @classmethod
    def get_instance(cls) -> "GUISystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_root(self, width: float = 800, height: float = 600) -> Container:
        self._root = Container(
            name="root",
            width=width,
            height=height,
            layout=LayoutMode.NONE,
        )
        return self._root

    @property
    def root(self) -> Optional[Container]:
        return self._root

    def create_button(self, text: str = "Button", parent: Optional[Container] = None, **kwargs) -> Button:
        btn = Button(text=text, **kwargs)
        if parent is None:
            parent = self._root
        if parent:
            parent.add(btn)
        self._widget_count += 1
        return btn

    def create_label(self, text: str = "Label", parent: Optional[Container] = None, **kwargs) -> Label:
        lbl = Label(text=text, **kwargs)
        if parent is None:
            parent = self._root
        if parent:
            parent.add(lbl)
        self._widget_count += 1
        return lbl

    def create_slider(self, parent: Optional[Container] = None, **kwargs) -> Slider:
        slider = Slider(**kwargs)
        if parent is None:
            parent = self._root
        if parent:
            parent.add(slider)
        self._widget_count += 1
        return slider

    def create_text_input(self, parent: Optional[Container] = None, **kwargs) -> TextInput:
        inp = TextInput(**kwargs)
        if parent is None:
            parent = self._root
        if parent:
            parent.add(inp)
        self._widget_count += 1
        return inp

    def create_image(self, texture_path: str = "", parent: Optional[Container] = None, **kwargs) -> Image:
        img = Image(texture_path=texture_path, **kwargs)
        if parent is None:
            parent = self._root
        if parent:
            parent.add(img)
        self._widget_count += 1
        return img

    def create_container(self, parent: Optional[Container] = None, **kwargs) -> Container:
        ctr = Container(**kwargs)
        if parent is None:
            parent = self._root
        if parent:
            parent.add(ctr)
        self._widget_count += 1
        return ctr

    def find_widget(self, widget_id: str) -> Optional[Widget]:
        if self._root is None:
            return None
        return self._root.find_recursive(widget_id)

    def handle_mouse_move(self, mx: float, my: float) -> None:
        if self._root is None:
            return
        self._hover_widget = None
        for widget in self._root.get_all_descendants():
            if widget.visible and widget.enabled and widget.contains(mx, my):
                self._hover_widget = widget.widget_id
                if widget.state != WidgetState.DISABLED:
                    widget.state = WidgetState.HOVERED
                    if widget._on_hover:
                        widget._on_hover()
                break

    def handle_mouse_click(self, mx: float, my: float) -> Optional[str]:
        if self._root is None:
            return None
        for widget in sorted(
            self._root.get_all_descendants(),
            key=lambda w: w.z_index,
            reverse=True,
        ):
            if widget.visible and widget.enabled and widget.contains(mx, my):
                widget.state = WidgetState.PRESSED
                if widget._on_click:
                    widget._on_click()
                self._focus_widget = widget.widget_id
                return widget.widget_id
        self._focus_widget = None
        return None

    def register_theme(self, theme: Theme) -> None:
        self._themes[theme.name] = theme

    def set_theme(self, name: str) -> bool:
        if name in self._themes:
            self._active_theme = name
            return True
        return False

    def get_theme(self) -> Optional[Theme]:
        return self._themes.get(self._active_theme)

    def _init_defaults(self) -> None:
        self._themes["default"] = Theme(name="default")
        self._themes["dark"] = Theme(
            name="dark",
            background_color=(20, 20, 20, 255),
            text_color=(220, 220, 220, 255),
        )
        self._themes["light"] = Theme(
            name="light",
            primary_color=(50, 100, 200, 255),
            background_color=(240, 240, 240, 255),
            text_color=(30, 30, 30, 255),
            secondary_color=(180, 180, 180, 255),
        )

    def get_stats(self) -> dict:
        return {
            "widget_count": self._widget_count,
            "root_exists": self._root is not None,
            "themes": list(self._themes.keys()),
            "active_theme": self._active_theme,
            "focus_widget": self._focus_widget,
            "hover_widget": self._hover_widget,
        }

    def reset(self) -> None:
        self._root = None
        self._widget_count = 0
        self._focus_widget = None
        self._hover_widget = None


def get_gui_system() -> GUISystem:
    return GUISystem.get_instance()
