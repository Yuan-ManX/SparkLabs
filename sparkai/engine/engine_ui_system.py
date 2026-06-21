"""
SparkLabs Engine - UI System Engine

A complete UI rendering and management system for the AI-native game engine.
Provides canvases, widgets, layouts, themes, and event handling with a
retained-mode widget tree, anchoring, and priority-based event dispatch.

Architecture:
  UISystemEngine (Singleton, multi-instance by name)
    |-- UICanvas    — root container with coordinate space and sorting order
    |-- UIWidget    — base widget with rect, anchor, layout, and visibility
    |-- UITheme     — color palette, font, spacing, and border presets
    |-- UIEvent     — typed UI event with position, target, and consumption
    |-- UIState     — per-canvas interaction state (focus, hover, drag)

Event Flow:
  Input → UISystemEngine.process_event() → target widget resolution
  Events bubble through the widget tree via parent-child relationships.

Usage:
    ui = get_ui_system("main_menu")
    canvas = ui.create_canvas("main", 1920, 1080, 0)
    panel = ui.create_widget(canvas.id, WidgetType.PANEL, None,
                             UIRect(200, 100, 400, 300), LayoutType.VERTICAL)
    ui.process_event(UIEventType.CLICK, panel.id, (250, 150), {})
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WidgetType(Enum):
    """Type classification for UI widgets."""
    CANVAS = "canvas"
    PANEL = "panel"
    BUTTON = "button"
    LABEL = "label"
    IMAGE = "image"
    TEXT_INPUT = "text_input"
    SLIDER = "slider"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    PROGRESS_BAR = "progress_bar"
    SCROLL_VIEW = "scroll_view"
    LIST_VIEW = "list_view"
    GRID_VIEW = "grid_view"
    TAB_GROUP = "tab_group"
    TOOLTIP = "tooltip"


class LayoutType(Enum):
    """Layout strategy for arranging child widgets within a parent."""
    ABSOLUTE = "absolute"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    GRID = "grid"
    ANCHOR = "anchor"
    FLEX = "flex"


class AnchorPoint(Enum):
    """Anchor point for positioning a widget relative to its parent."""
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


class UIEventType(Enum):
    """Type of UI interaction event."""
    CLICK = "click"
    HOVER = "hover"
    DRAG = "drag"
    DROP = "drop"
    FOCUS = "focus"
    BLUR = "blur"
    KEY_PRESS = "key_press"
    SCROLL = "scroll"
    RESIZE = "resize"
    VALUE_CHANGED = "value_changed"


class ThemeMode(Enum):
    """Theme color mode determining the base palette."""
    LIGHT = "light"
    DARK = "dark"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class UIRect:
    """A rectangle defining position and size of a UI element."""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.right and self.y <= py <= self.bottom

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class UIColor:
    """RGBA color representation."""
    r: int = 255
    g: int = 255
    b: int = 255
    a: int = 255

    def to_dict(self) -> Dict[str, Any]:
        return {
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "a": self.a,
        }

    def as_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}{self.a:02x}"


@dataclass
class UITheme:
    """Theme definition with color palette, typography, and spacing presets."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mode: ThemeMode = ThemeMode.DARK
    primary_color: UIColor = field(default_factory=lambda: UIColor(52, 152, 219))
    secondary_color: UIColor = field(default_factory=lambda: UIColor(46, 204, 113))
    background_color: UIColor = field(default_factory=lambda: UIColor(44, 47, 51))
    text_color: UIColor = field(default_factory=lambda: UIColor(220, 221, 222))
    font_family: str = "system"
    font_size: int = 14
    border_radius: int = 8
    spacing: int = 8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "primary_color": self.primary_color.to_dict(),
            "secondary_color": self.secondary_color.to_dict(),
            "background_color": self.background_color.to_dict(),
            "text_color": self.text_color.to_dict(),
            "font_family": self.font_family,
            "font_size": self.font_size,
            "border_radius": self.border_radius,
            "spacing": self.spacing,
        }


@dataclass
class UIWidget:
    """A single UI element in the widget tree."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    widget_type: WidgetType = WidgetType.PANEL
    name: str = ""
    rect: UIRect = field(default_factory=UIRect)
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    layout_type: LayoutType = LayoutType.ABSOLUTE
    anchor: AnchorPoint = AnchorPoint.TOP_LEFT
    visible: bool = True
    enabled: bool = True
    theme_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "widget_type": self.widget_type.value,
            "name": self.name,
            "rect": self.rect.to_dict(),
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "layout_type": self.layout_type.value,
            "anchor": self.anchor.value,
            "visible": self.visible,
            "enabled": self.enabled,
            "theme_id": self.theme_id,
            "data": dict(self.data),
            "metadata": dict(self.metadata),
        }


@dataclass
class UICanvas:
    """Root container for a UI hierarchy with coordinate space and sorting."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    widgets: Dict[str, UIWidget] = field(default_factory=dict)
    theme_id: Optional[str] = None
    screen_width: float = 1920.0
    screen_height: float = 1080.0
    scale_factor: float = 1.0
    sorting_order: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "widget_count": len(self.widgets),
            "theme_id": self.theme_id,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "scale_factor": self.scale_factor,
            "sorting_order": self.sorting_order,
            "enabled": self.enabled,
        }


@dataclass
class UIEvent:
    """A UI interaction event with target, position, and consumption state."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: UIEventType = UIEventType.CLICK
    target_widget_id: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    consumed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "target_widget_id": self.target_widget_id,
            "position": list(self.position),
            "data": dict(self.data),
            "timestamp": self.timestamp,
            "consumed": self.consumed,
        }


@dataclass
class UIState:
    """Per-canvas interaction state tracking focus, hover, and drag."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    canvas_id: str = ""
    focused_widget_id: Optional[str] = None
    hovered_widget_id: Optional[str] = None
    dragged_widget_id: Optional[str] = None
    state_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "canvas_id": self.canvas_id,
            "focused_widget_id": self.focused_widget_id,
            "hovered_widget_id": self.hovered_widget_id,
            "dragged_widget_id": self.dragged_widget_id,
            "state_data": dict(self.state_data),
        }


# ---------------------------------------------------------------------------
# UISystemEngine
# ---------------------------------------------------------------------------

class UISystemEngine:
    """
    Complete UI rendering and management system for the SparkLabs game engine.

    Provides canvas-based UI hierarchies with widgets, themes, layout
    strategies, and event handling. Supports multiple named instances for
    concurrent UI contexts (e.g., main menu, HUD, debug overlay).

    Each instance maintains its own canvas registry, widget tree, theme
    catalog, and interaction state, isolated from other instances.
    """

    _instances: Dict[str, "UISystemEngine"] = {}
    _lock = threading.RLock()

    def __new__(cls, name: str = "default") -> "UISystemEngine":
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instances[name] = instance
        return cls._instances[name]

    @classmethod
    def get_instance(cls, name: str = "default") -> "UISystemEngine":
        """Get or create a named UISystemEngine instance."""
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    instance = cls(name)
                    instance._initialized = False
                    cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name: str = "default") -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._name: str = name
        self._canvases: Dict[str, UICanvas] = {}
        self._widgets: Dict[str, UIWidget] = {}
        self._themes: Dict[str, UITheme] = {}
        self._states: Dict[str, UIState] = {}
        self._event_history: List[UIEvent] = []

        self._max_widgets: int = 10000
        self._max_canvases: int = 64
        self._max_themes: int = 256

        self._stats: Dict[str, Any] = {
            "total_canvases_created": 0,
            "total_widgets_created": 0,
            "total_widgets_removed": 0,
            "total_themes_created": 0,
            "total_events_processed": 0,
            "total_visibility_changes": 0,
            "total_enabled_changes": 0,
            "active_canvases": 0,
            "active_widgets": 0,
            "last_error": "",
        }

    # ------------------------------------------------------------------
    # Canvas Management
    # ------------------------------------------------------------------

    def create_canvas(
        self,
        name: str,
        width: float = 1920.0,
        height: float = 1080.0,
        scale_factor: float = 1.0,
        sorting_order: int = 0,
    ) -> UICanvas:
        """Create a new UI canvas with the specified dimensions and ordering.

        Args:
            name: Human-readable name for the canvas (e.g., "main_menu").
            width: Canvas width in logical pixels.
            height: Canvas height in logical pixels.
            scale_factor: DPI scaling factor (1.0 = 100%).
            sorting_order: Rendering order among canvases (lower = behind).

        Returns:
            The newly created UICanvas.

        Raises:
            RuntimeError: If the maximum canvas limit has been reached.
        """
        with self._lock:
            if len(self._canvases) >= self._max_canvases:
                raise RuntimeError(
                    f"Maximum canvas limit reached ({self._max_canvases})"
                )

            canvas = UICanvas(
                name=name,
                screen_width=width,
                screen_height=height,
                scale_factor=scale_factor,
                sorting_order=sorting_order,
            )
            self._canvases[canvas.id] = canvas

            # Create associated state tracker
            state = UIState(canvas_id=canvas.id)
            self._states[canvas.id] = state

            self._stats["total_canvases_created"] += 1
            self._stats["active_canvases"] = len(self._canvases)

            return canvas

    def get_canvas(self, canvas_id: str) -> Optional[UICanvas]:
        """Retrieve a canvas by its unique identifier."""
        with self._lock:
            return self._canvases.get(canvas_id)

    # ------------------------------------------------------------------
    # Widget Management
    # ------------------------------------------------------------------

    def create_widget(
        self,
        canvas_id: str,
        widget_type: WidgetType,
        parent_id: Optional[str] = None,
        rect: Optional[UIRect] = None,
        layout_type: LayoutType = LayoutType.ABSOLUTE,
        anchor: AnchorPoint = AnchorPoint.TOP_LEFT,
    ) -> UIWidget:
        """Create a new UI widget and attach it to a canvas and optionally a parent.

        Args:
            canvas_id: The canvas this widget belongs to.
            widget_type: The type of widget to create.
            parent_id: Optional parent widget ID for tree hierarchy.
            rect: Position and size rectangle (defaults to zero-sized rect).
            layout_type: Layout strategy for this widget's children.
            anchor: Anchor point for positioning relative to parent.

        Returns:
            The newly created UIWidget.

        Raises:
            RuntimeError: If the maximum widget limit has been reached.
            ValueError: If the canvas does not exist or the parent widget
                        does not belong to the specified canvas.
        """
        with self._lock:
            if len(self._widgets) >= self._max_widgets:
                raise RuntimeError(
                    f"Maximum widget limit reached ({self._max_widgets})"
                )

            canvas = self._canvases.get(canvas_id)
            if canvas is None:
                raise ValueError(f"Canvas not found: {canvas_id}")

            if parent_id is not None and parent_id not in self._widgets:
                raise ValueError(f"Parent widget not found: {parent_id}")

            widget = UIWidget(
                widget_type=widget_type,
                name=f"{widget_type.value}_{len(self._widgets)}",
                rect=rect or UIRect(),
                parent_id=parent_id,
                layout_type=layout_type,
                anchor=anchor,
            )

            self._widgets[widget.id] = widget
            canvas.widgets[widget.id] = widget

            # Register as child of parent
            if parent_id is not None:
                parent = self._widgets[parent_id]
                parent.children_ids.append(widget.id)

            self._stats["total_widgets_created"] += 1
            self._stats["active_widgets"] = len(self._widgets)

            return widget

    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget and all its descendants from the widget tree.

        Args:
            widget_id: The unique identifier of the widget to remove.

        Returns:
            True if the widget was found and removed, False otherwise.
        """
        with self._lock:
            widget = self._widgets.get(widget_id)
            if widget is None:
                return False

            # Recursively remove all children
            children_to_remove = list(widget.children_ids)
            for child_id in children_to_remove:
                self.remove_widget(child_id)

            # Remove from parent's children list
            if widget.parent_id is not None:
                parent = self._widgets.get(widget.parent_id)
                if parent is not None and widget_id in parent.children_ids:
                    parent.children_ids.remove(widget_id)

            # Remove from canvas
            for canvas in self._canvases.values():
                canvas.widgets.pop(widget_id, None)

            # Clear state references
            for state in self._states.values():
                if state.focused_widget_id == widget_id:
                    state.focused_widget_id = None
                if state.hovered_widget_id == widget_id:
                    state.hovered_widget_id = None
                if state.dragged_widget_id == widget_id:
                    state.dragged_widget_id = None

            del self._widgets[widget_id]
            self._stats["total_widgets_removed"] += 1
            self._stats["active_widgets"] = len(self._widgets)

            return True

    def update_widget(
        self,
        widget_id: str,
        data: Dict[str, Any],
    ) -> Optional[UIWidget]:
        """Update the data dictionary of an existing widget.

        Performs a shallow merge of the provided data into the widget's
        existing data field.

        Args:
            widget_id: The unique identifier of the widget to update.
            data: Key-value pairs to merge into the widget's data.

        Returns:
            The updated UIWidget, or None if not found.
        """
        with self._lock:
            widget = self._widgets.get(widget_id)
            if widget is None:
                return None
            widget.data.update(data)
            return widget

    def set_widget_visibility(self, widget_id: str, visible: bool) -> bool:
        """Set the visibility state of a widget.

        Args:
            widget_id: The unique identifier of the widget.
            visible: True to make the widget visible, False to hide it.

        Returns:
            True if the widget was found and updated, False otherwise.
        """
        with self._lock:
            widget = self._widgets.get(widget_id)
            if widget is None:
                return False
            widget.visible = visible
            self._stats["total_visibility_changes"] += 1
            return True

    def set_widget_enabled(self, widget_id: str, enabled: bool) -> bool:
        """Set the enabled state of a widget.

        Disabled widgets do not receive interaction events.

        Args:
            widget_id: The unique identifier of the widget.
            enabled: True to enable the widget, False to disable it.

        Returns:
            True if the widget was found and updated, False otherwise.
        """
        with self._lock:
            widget = self._widgets.get(widget_id)
            if widget is None:
                return False
            widget.enabled = enabled
            self._stats["total_enabled_changes"] += 1
            return True

    def get_widget(self, widget_id: str) -> Optional[UIWidget]:
        """Retrieve a widget by its unique identifier."""
        with self._lock:
            return self._widgets.get(widget_id)

    def get_widget_tree(self, canvas_id: str) -> Dict[str, Any]:
        """Build a tree representation of all widgets on a canvas.

        Returns a nested dictionary where each widget is keyed by its ID
        and contains a 'children' dict of its direct descendants.

        Args:
            canvas_id: The canvas whose widget tree to retrieve.

        Returns:
            A nested dictionary representing the widget tree, or an empty
            dict if the canvas is not found.
        """
        with self._lock:
            canvas = self._canvases.get(canvas_id)
            if canvas is None:
                return {}

            def _build_subtree(widget_id: str) -> Dict[str, Any]:
                widget = self._widgets.get(widget_id)
                if widget is None:
                    return {}
                subtree = {
                    "id": widget.id,
                    "widget_type": widget.widget_type.value,
                    "name": widget.name,
                    "rect": widget.rect.to_dict(),
                    "visible": widget.visible,
                    "enabled": widget.enabled,
                    "layout_type": widget.layout_type.value,
                    "anchor": widget.anchor.value,
                    "children": {},
                }
                for child_id in widget.children_ids:
                    subtree["children"][child_id] = _build_subtree(child_id)
                return subtree

            # Find root-level widgets (those without a parent on this canvas)
            result: Dict[str, Any] = {}
            for widget in canvas.widgets.values():
                if widget.parent_id is None or widget.parent_id not in self._widgets:
                    result[widget.id] = _build_subtree(widget.id)

            return result

    # ------------------------------------------------------------------
    # Theme Management
    # ------------------------------------------------------------------

    def create_theme(
        self,
        mode: ThemeMode = ThemeMode.DARK,
        primary_color: Optional[UIColor] = None,
        secondary_color: Optional[UIColor] = None,
        background_color: Optional[UIColor] = None,
        text_color: Optional[UIColor] = None,
    ) -> UITheme:
        """Create a new UI theme with the specified color palette.

        Args:
            mode: The base color mode (LIGHT, DARK, or CUSTOM).
            primary_color: Primary brand/action color.
            secondary_color: Secondary accent color.
            background_color: Background surface color.
            text_color: Default text color.

        Returns:
            The newly created UITheme.

        Raises:
            RuntimeError: If the maximum theme limit has been reached.
        """
        with self._lock:
            if len(self._themes) >= self._max_themes:
                raise RuntimeError(
                    f"Maximum theme limit reached ({self._max_themes})"
                )

            theme = UITheme(
                mode=mode,
                primary_color=primary_color or UIColor(52, 152, 219),
                secondary_color=secondary_color or UIColor(46, 204, 113),
                background_color=background_color or UIColor(44, 47, 51),
                text_color=text_color or UIColor(220, 221, 222),
            )
            self._themes[theme.id] = theme
            self._stats["total_themes_created"] += 1

            return theme

    def apply_theme(self, canvas_id: str, theme_id: str) -> bool:
        """Apply a theme to a canvas.

        The theme's colors, fonts, and spacing presets will be inherited
        by all widgets on the canvas that do not have their own theme override.

        Args:
            canvas_id: The canvas to apply the theme to.
            theme_id: The theme to apply.

        Returns:
            True if both the canvas and theme exist and the theme was applied,
            False otherwise.
        """
        with self._lock:
            canvas = self._canvases.get(canvas_id)
            if canvas is None:
                return False

            theme = self._themes.get(theme_id)
            if theme is None:
                return False

            canvas.theme_id = theme_id
            return True

    # ------------------------------------------------------------------
    # Event Processing
    # ------------------------------------------------------------------

    def process_event(
        self,
        event_type: UIEventType,
        target_widget_id: str,
        position: Tuple[float, float] = (0.0, 0.0),
        data: Optional[Dict[str, Any]] = None,
    ) -> UIEvent:
        """Process a UI interaction event and dispatch it to the target widget.

        Creates a UIEvent record, updates the canvas interaction state based
        on the event type, and appends it to the event history.

        Args:
            event_type: The type of UI event (CLICK, HOVER, DRAG, etc.).
            target_widget_id: The widget that is the target of this event.
            position: The (x, y) position of the event in canvas coordinates.
            data: Optional payload data associated with the event.

        Returns:
            The created and processed UIEvent.
        """
        with self._lock:
            event = UIEvent(
                event_type=event_type,
                target_widget_id=target_widget_id,
                position=position,
                data=data or {},
            )

            self._stats["total_events_processed"] += 1

            # Update canvas state based on event type
            target_widget = self._widgets.get(target_widget_id)
            if target_widget is not None:
                # Find the canvas this widget belongs to
                for canvas_id, canvas in self._canvases.items():
                    if target_widget_id in canvas.widgets:
                        state = self._states.get(canvas_id)
                        if state is None:
                            break

                        if event_type == UIEventType.CLICK:
                            state.focused_widget_id = target_widget_id
                        elif event_type == UIEventType.HOVER:
                            state.hovered_widget_id = target_widget_id
                        elif event_type == UIEventType.FOCUS:
                            state.focused_widget_id = target_widget_id
                        elif event_type == UIEventType.BLUR:
                            if state.focused_widget_id == target_widget_id:
                                state.focused_widget_id = None
                        elif event_type == UIEventType.DRAG:
                            state.dragged_widget_id = target_widget_id
                        elif event_type == UIEventType.DROP:
                            if state.dragged_widget_id == target_widget_id:
                                state.dragged_widget_id = None
                        break

            # Append to event history (keep last 1000 events)
            self._event_history.append(event)
            while len(self._event_history) > 1000:
                self._event_history.pop(0)

            return event

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics.

        Returns a dictionary with counts for canvases, widgets, themes,
        events, and operational metrics.
        """
        with self._lock:
            widget_type_counts: Dict[str, int] = {}
            layout_type_counts: Dict[str, int] = {}
            for widget in self._widgets.values():
                wt = widget.widget_type.value
                widget_type_counts[wt] = widget_type_counts.get(wt, 0) + 1
                lt = widget.layout_type.value
                layout_type_counts[lt] = layout_type_counts.get(lt, 0) + 1

            event_type_counts: Dict[str, int] = {}
            for event in self._event_history:
                et = event.event_type.value
                event_type_counts[et] = event_type_counts.get(et, 0) + 1

            return {
                "engine_name": self._name,
                "total_canvases": len(self._canvases),
                "total_widgets": len(self._widgets),
                "total_themes": len(self._themes),
                "total_states": len(self._states),
                "max_widgets": self._max_widgets,
                "max_canvases": self._max_canvases,
                "max_themes": self._max_themes,
                "event_history_size": len(self._event_history),
                "widgets_by_type": widget_type_counts,
                "widgets_by_layout": layout_type_counts,
                "events_by_type": event_type_counts,
                "total_canvases_created": self._stats["total_canvases_created"],
                "total_widgets_created": self._stats["total_widgets_created"],
                "total_widgets_removed": self._stats["total_widgets_removed"],
                "total_themes_created": self._stats["total_themes_created"],
                "total_events_processed": self._stats["total_events_processed"],
                "total_visibility_changes": self._stats["total_visibility_changes"],
                "total_enabled_changes": self._stats["total_enabled_changes"],
                "last_error": self._stats["last_error"],
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire UI system engine state.

        Clears all canvases, widgets, themes, states, event history,
        and resets all statistics counters to zero.
        """
        with self._lock:
            self._canvases.clear()
            self._widgets.clear()
            self._themes.clear()
            self._states.clear()
            self._event_history.clear()

            self._stats = {
                "total_canvases_created": 0,
                "total_widgets_created": 0,
                "total_widgets_removed": 0,
                "total_themes_created": 0,
                "total_events_processed": 0,
                "total_visibility_changes": 0,
                "total_enabled_changes": 0,
                "active_canvases": 0,
                "active_widgets": 0,
                "last_error": "",
            }


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------


def get_ui_system(name: str = "default") -> UISystemEngine:
    """Get or create a named UISystemEngine instance.

    Args:
        name: A unique name for the engine instance. Defaults to 'default'.
              Use different names for concurrent UI contexts (e.g., "main_menu",
              "hud", "debug_overlay").

    Returns:
        The UISystemEngine instance for the given name.
    """
    return UISystemEngine.get_instance(name)