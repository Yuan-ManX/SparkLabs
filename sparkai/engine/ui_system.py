"""
SparkLabs Engine - UI System

Canvas-based 2D user interface system for game HUDs, menus,
dialogs, and AI-generated UI layouts. Provides a retained-mode
widget tree with anchoring, nine-slice scaling, theme support,
and event bubbling for touch/mouse/controller input.

Architecture:
  UISystem
    |-- UICanvas (root container with coordinate space)
    |-- UIWidget (base: rect, anchor, theme-aware rendering)
      |-- UILabel (styled text with alignment + overflow modes)
      |-- UIButton (label + icon, hover/press states, callbacks)
      |-- UIPanel (nine-slice background with child clipping)
      |-- UISlider (horizontal/vertical with range + steps)
      |-- UIProgressBar (fill bar with direction + animation)
    |-- UITheme (color palette, font, spacing presets)

Event Flow:
  Input → UISystem._hit_test(root) → deepest widget
  Widgets bubble unhandled events to parent via on_* handlers.

Usage:
    ui = UISystem(canvas_width=800, canvas_height=600)
    panel = ui.create_panel("main_menu", x=200, y=100, w=400, h=400)
    label = ui.create_label("title", "My Game", 0, 0, 400, 60)
    panel.add_child(label)
    play_btn = ui.create_button("play", "PLAY", 50, 200, 300, 50, on_click=lambda: start_game())
    panel.add_child(play_btn)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class AnchorMode(Enum):
    TOP_LEFT = auto()
    TOP_CENTER = auto()
    TOP_RIGHT = auto()
    CENTER_LEFT = auto()
    CENTER = auto()
    CENTER_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_CENTER = auto()
    BOTTOM_RIGHT = auto()
    STRETCH = auto()


class OverflowMode(Enum):
    VISIBLE = auto()
    CLIP = auto()
    ELLIPSIS = auto()


class TextAlign(Enum):
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()


class FlexDirection(Enum):
    ROW = auto()
    COLUMN = auto()


@dataclass
class UIColor:
    r: int = 255
    g: int = 255
    b: int = 255
    a: int = 255

    @staticmethod
    def from_hex(hex_str: str) -> "UIColor":
        h = hex_str.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return UIColor(r=r, g=g, b=b, a=255)
        elif len(h) == 8:
            r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
            return UIColor(r=r, g=g, b=b, a=a)
        return UIColor()

    def as_css(self) -> str:
        return f"rgba({self.r},{self.g},{self.b},{self.a/255:.2f})"

    def as_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


@dataclass
class UITheme:
    name: str = "default"
    primary_color: UIColor = field(default_factory=lambda: UIColor(52, 152, 219))
    secondary_color: UIColor = field(default_factory=lambda: UIColor(46, 204, 113))
    background_color: UIColor = field(default_factory=lambda: UIColor(44, 47, 51))
    surface_color: UIColor = field(default_factory=lambda: UIColor(54, 57, 63))
    text_color: UIColor = field(default_factory=lambda: UIColor(220, 221, 222))
    text_muted_color: UIColor = field(default_factory=lambda: UIColor(153, 153, 153))
    danger_color: UIColor = field(default_factory=lambda: UIColor(231, 76, 60))
    warning_color: UIColor = field(default_factory=lambda: UIColor(241, 196, 15))
    border_color: UIColor = field(default_factory=lambda: UIColor(64, 68, 75))
    border_radius: int = 8
    font_family: str = "system"
    font_size: int = 14
    spacing: int = 8
    transition_duration: float = 0.2


class UIRect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x: float = 0.0, y: float = 0.0, w: float = 0.0, h: float = 0.0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def center_x(self) -> float:
        return self.x + self.w / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.h / 2.0

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.right and self.y <= py <= self.bottom

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


class UIWidget:
    widget_type = "widget"

    def __init__(self, widget_id: str = "", parent: Optional["UIWidget"] = None, rect: UIRect | None = None):
        self.id: str = widget_id or str(uuid.uuid4())
        self.rect: UIRect = rect or UIRect()
        self.parent: Optional["UIWidget"] = None
        self.children: List["UIWidget"] = []
        self.visible: bool = True
        self.enabled: bool = True
        self.tooltip: str = ""
        self.margin: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self.padding: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self.z_index: int = 0
        self.on_click: Optional[Callable[[], None]] = None
        self.on_hover_enter: Optional[Callable[[], None]] = None
        self.on_hover_leave: Optional[Callable[[], None]] = None
        self.on_focus: Optional[Callable[[], None]] = None
        self.on_blur: Optional[Callable[[], None]] = None
        self._hovered: bool = False
        self._focused: bool = False
        self._pressed: bool = False

    def add_child(self, child: "UIWidget") -> "UIWidget":
        child.parent = self
        self.children.append(child)
        return child

    def remove_child(self, child_id: str) -> bool:
        for i, ch in enumerate(self.children):
            if ch.id == child_id:
                self.children.pop(i)
                return True
        return False

    def find_child(self, child_id: str) -> Optional["UIWidget"]:
        for ch in self.children:
            if ch.id == child_id:
                return ch
            found = ch.find_child(child_id)
            if found:
                return found
        return None

    def hit_test(self, px: float, py: float) -> Optional["UIWidget"]:
        if not self.visible or not self.rect.contains(px, py):
            return None
        for child in reversed(self.children):
            result = child.hit_test(px - self.rect.x, py - self.rect.y)
            if result:
                return result
        return self

    def absolute_rect(self) -> UIRect:
        px, py = self.rect.x, self.rect.y
        p = self.parent
        while p:
            px += p.rect.x
            py += p.rect.y
            p = p.parent
        return UIRect(px, py, self.rect.w, self.rect.h)

    def get_flattened_tree(self) -> List[Dict[str, Any]]:
        result = [{
            "id": self.id,
            "type": self.widget_type,
            "rect": self.rect.to_dict(),
            "visible": self.visible,
            "child_count": len(self.children),
        }]
        for child in self.children:
            result.extend(child.get_flattened_tree())
        return result


class UILabel(UIWidget):
    widget_type = "label"

    def __init__(self, widget_id: str = "", text: str = "", rect: UIRect | None = None):
        super().__init__(widget_id=widget_id, rect=rect)
        self.text: str = text
        self.font_size: int = 14
        self.color: UIColor = UIColor(220, 221, 222)
        self.text_align: TextAlign = TextAlign.LEFT
        self.multiline: bool = False
        self.overflow: OverflowMode = OverflowMode.ELLIPSIS
        self.bold: bool = False
        self.italic: bool = False


class UIButton(UIWidget):
    widget_type = "button"

    def __init__(self, widget_id: str = "", label: str = "", rect: UIRect | None = None):
        super().__init__(widget_id=widget_id, rect=rect)
        self.label: str = label
        self.bg_color: UIColor = UIColor(52, 152, 219)
        self.hover_color: UIColor = UIColor(72, 172, 239)
        self.press_color: UIColor = UIColor(32, 132, 199)
        self.disabled_color: UIColor = UIColor(100, 100, 100)
        self.border_radius: int = 4
        self.icon_path: str = ""
        self._state: str = "idle"

    @property
    def state(self) -> str:
        if not self.enabled:
            return "disabled"
        if self._pressed:
            return "pressed"
        if self._hovered:
            return "hover"
        return "idle"


class UIPanel(UIWidget):
    widget_type = "panel"

    def __init__(self, widget_id: str = "", rect: UIRect | None = None, bg_color: UIColor | None = None):
        super().__init__(widget_id=widget_id, rect=rect)
        self.bg_color: UIColor = bg_color or UIColor(54, 57, 63)
        self.border_color: UIColor = UIColor(64, 68, 75)
        self.border_width: int = 1
        self.border_radius: int = 8
        self.clip_content: bool = True
        self.title: str = ""
        self.draggable: bool = False


class UISlider(UIWidget):
    widget_type = "slider"

    def __init__(self, widget_id: str = "", rect: UIRect | None = None, value: float = 0.0):
        super().__init__(widget_id=widget_id, rect=rect)
        self.value: float = value
        self.min: float = 0.0
        self.max: float = 1.0
        self.step: float = 0.01
        self.track_color: UIColor = UIColor(64, 68, 75)
        self.fill_color: UIColor = UIColor(52, 152, 219)
        self.thumb_color: UIColor = UIColor(220, 221, 222)
        self.thumb_radius: float = 8.0
        self.show_label: bool = True


class UIProgressBar(UIWidget):
    widget_type = "progress_bar"

    def __init__(self, widget_id: str = "", rect: UIRect | None = None, value: float = 0.0):
        super().__init__(widget_id=widget_id, rect=rect)
        self.value: float = value
        self.max: float = 1.0
        self.fill_color: UIColor = UIColor(52, 152, 219)
        self.bg_color: UIColor = UIColor(64, 68, 75)
        self.border_radius: int = 4
        self.show_label: bool = False
        self.animated: bool = True
        self.direction: str = "horizontal"


class UISystem:
    _instance: Optional["UISystem"] = None

    def __init__(self, canvas_width: float = 800.0, canvas_height: float = 600.0):
        self._root: UIWidget | None = None
        self._canvas_width: float = canvas_width
        self._canvas_height: float = canvas_height
        self._active_theme: UITheme = UITheme()
        self._hovered_widget_id: Optional[str] = None
        self._focused_widget_id: Optional[str] = None
        self._widget_registry: Dict[str, UIWidget] = {}
        self._setup_root()

    def _setup_root(self) -> None:
        self._root = UIWidget(widget_id="__ui_root__", rect=UIRect(0, 0, self._canvas_width, self._canvas_height))

    @classmethod
    def get_instance(cls) -> "UISystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def root(self) -> UIWidget:
        return self._root

    @property
    def theme(self) -> UITheme:
        return self._active_theme

    def set_theme(self, theme: UITheme) -> None:
        self._active_theme = theme

    def create_custom_theme(
        self,
        name: str = "custom",
        primary_color: str = "#3498db",
        bg_color: str = "#232428",
        surface_color: str = "#36393f",
        text_color: str = "#dcddde",
        border_radius: int = 8,
        font_size: int = 14,
    ) -> UITheme:
        theme = UITheme(
            name=name,
            primary_color=UIColor.from_hex(primary_color),
            background_color=UIColor.from_hex(bg_color),
            surface_color=UIColor.from_hex(surface_color),
            text_color=UIColor.from_hex(text_color),
            border_radius=border_radius,
            font_size=font_size,
        )
        self._active_theme = theme
        return theme

    def create_label(
        self,
        widget_id: str = "",
        text: str = "",
        x: float = 0.0,
        y: float = 0.0,
        w: float = 100.0,
        h: float = 24.0,
    ) -> UILabel:
        label = UILabel(widget_id=widget_id, text=text, rect=UIRect(x, y, w, h))
        label.color = self._active_theme.text_color
        label.font_size = self._active_theme.font_size
        self._register_widget(label)
        return label

    def create_button(
        self,
        widget_id: str = "",
        label: str = "",
        x: float = 0.0,
        y: float = 0.0,
        w: float = 120.0,
        h: float = 36.0,
        on_click: Optional[Callable[[], None]] = None,
    ) -> UIButton:
        btn = UIButton(widget_id=widget_id, label=label, rect=UIRect(x, y, w, h))
        btn.bg_color = self._active_theme.primary_color
        btn.border_radius = self._active_theme.border_radius // 2
        btn.on_click = on_click
        self._register_widget(btn)
        return btn

    def create_panel(
        self,
        widget_id: str = "",
        x: float = 0.0,
        y: float = 0.0,
        w: float = 300.0,
        h: float = 200.0,
        title: str = "",
        bg_color: UIColor | None = None,
    ) -> UIPanel:
        color = bg_color or self._active_theme.surface_color
        panel = UIPanel(widget_id=widget_id, rect=UIRect(x, y, w, h), bg_color=color)
        panel.border_radius = self._active_theme.border_radius
        panel.title = title
        self._register_widget(panel)
        return panel

    def create_slider(
        self,
        widget_id: str = "",
        x: float = 0.0,
        y: float = 0.0,
        w: float = 200.0,
        h: float = 20.0,
        value: float = 0.0,
        min_val: float = 0.0,
        max_val: float = 1.0,
        step: float = 0.01,
    ) -> UISlider:
        slider = UISlider(widget_id=widget_id, rect=UIRect(x, y, w, h), value=value)
        slider.min = min_val
        slider.max = max_val
        slider.step = step
        self._register_widget(slider)
        return slider

    def create_progress_bar(
        self,
        widget_id: str = "",
        x: float = 0.0,
        y: float = 0.0,
        w: float = 200.0,
        h: float = 12.0,
        value: float = 0.0,
        max_val: float = 1.0,
    ) -> UIProgressBar:
        bar = UIProgressBar(widget_id=widget_id, rect=UIRect(x, y, w, h), value=value)
        bar.max = max_val
        bar.fill_color = self._active_theme.primary_color
        bar.bg_color = self._active_theme.border_color
        self._register_widget(bar)
        return bar

    def get_widget(self, widget_id: str) -> Optional[UIWidget]:
        if self._root and widget_id == "__ui_root__":
            return self._root
        return self._root.find_child(widget_id) if self._root else None

    def update_widget_position(
        self, widget_id: str, x: float, y: float, w: float | None = None, h: float | None = None
    ) -> bool:
        widget = self.get_widget(widget_id)
        if not widget:
            return False
        widget.rect.x = x
        widget.rect.y = y
        if w is not None:
            widget.rect.w = w
        if h is not None:
            widget.rect.h = h
        return True

    def set_widget_visibility(self, widget_id: str, visible: bool) -> bool:
        widget = self.get_widget(widget_id)
        if not widget:
            return False
        widget.visible = visible
        return True

    def delete_widget(self, widget_id: str) -> bool:
        widget = self.get_widget(widget_id)
        if not widget or not widget.parent:
            return False
        result = widget.parent.remove_child(widget_id)
        self._widget_registry.pop(widget_id, None)
        return result

    def handle_mouse_move(self, x: float, y: float) -> Optional[str]:
        if not self._root:
            return None
        hit = self._root.hit_test(x, y)
        hit_id = hit.id if hit else None

        if hit_id != self._hovered_widget_id:
            prev = self.get_widget(self._hovered_widget_id) if self._hovered_widget_id else None
            if prev and prev.on_hover_leave:
                prev.on_hover_leave()
            if prev:
                prev._hovered = False

            if hit and hit.on_hover_enter:
                hit.on_hover_enter()
            if hit:
                hit._hovered = True

            self._hovered_widget_id = hit_id

        return hit_id

    def handle_mouse_down(self, x: float, y: float) -> Optional[str]:
        hit = self._root.hit_test(x, y) if self._root else None
        if hit:
            hit._pressed = True
            hit._focused = True
            self._focused_widget_id = hit.id
            if hit.on_focus:
                hit.on_focus()
            return hit.id
        return None

    def handle_mouse_up(self, x: float, y: float) -> Optional[str]:
        if not self._root:
            return None
        hit = self._root.hit_test(x, y)
        focused = self.get_widget(self._focused_widget_id) if self._focused_widget_id else None

        if focused:
            focused._pressed = False

        if focused and hit and focused.id == hit.id:
            if focused.on_click:
                focused.on_click()
            return focused.id

        return hit.id if hit else None

    def get_all_widgets(self) -> List[Dict[str, Any]]:
        if not self._root:
            return []
        return self._root.get_flattened_tree()

    def _register_widget(self, widget: UIWidget) -> None:
        self._widget_registry[widget.id] = widget

    def get_stats(self) -> Dict[str, Any]:
        widget_count = len(self.get_all_widgets()) if self._root else 0
        return {
            "canvas_width": self._canvas_width,
            "canvas_height": self._canvas_height,
            "theme": self._active_theme.name,
            "widget_count": widget_count,
            "hovered_widget": self._hovered_widget_id,
            "focused_widget": self._focused_widget_id,
        }


def get_ui_system() -> UISystem:
    return UISystem.get_instance()
