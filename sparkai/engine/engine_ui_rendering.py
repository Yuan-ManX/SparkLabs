"""
SparkLabs Engine - UI Rendering Pipeline

Comprehensive UI rendering pipeline for the SparkLabs AI-native game engine.
Handles UI layout composition, draw call batching for UI elements, IMGUI
integration, widget rendering, and UI-specific post-processing effects.

Architecture:
  UIRenderingPipeline (Singleton)
    |-- UIRenderConfig     — configuration for the UI render pipeline
    |-- Widget             — widget definitions registered with factories
    |-- LayoutNode          — computed layout tree node with rect & children
    |-- DrawCall            — single UI draw call (texture, verts, blend)
    |-- UIBatch             — merged group of UI draw calls sharing state
    |-- UIRenderStats       — per-frame UI rendering statistics
    |-- UIRenderSnapshot    — complete UI render system snapshot

Render Pass Order:
  1. BACKGROUND     — full-screen background panels and gradients
  2. WIDGETS        — primary widget geometry (buttons, panels, sliders)
  3. OVERLAY        — overlays and HUD elements above widgets
  4. TOOLTIP        — floating tooltip widgets
  5. MODAL          — modal dialogs and blocking overlays
  6. NOTIFICATION   — toast notifications and transient messages
  7. DEBUG          — debug overlays and IMGUI windows

Layout Strategies:
  FLEXBOX, GRID, ABSOLUTE, ANCHOR, FLOW, STACK
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class UIRenderPass(Enum):
    """Render pass classification for UI pipeline ordering."""
    BACKGROUND = "background"
    WIDGETS = "widgets"
    OVERLAY = "overlay"
    TOOLTIP = "tooltip"
    MODAL = "modal"
    NOTIFICATION = "notification"
    DEBUG = "debug"


class LayoutStrategy(Enum):
    """Layout strategy for arranging widgets in a layout tree."""
    FLEXBOX = "flexbox"
    GRID = "grid"
    ABSOLUTE = "absolute"
    ANCHOR = "anchor"
    FLOW = "flow"
    STACK = "stack"


class WidgetType(Enum):
    """Type classification for UI widgets."""
    BUTTON = "button"
    TEXT = "text"
    IMAGE = "image"
    PANEL = "panel"
    SLIDER = "slider"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    TEXT_INPUT = "text_input"
    SCROLL_VIEW = "scroll_view"
    CANVAS = "canvas"
    CUSTOM = "custom"


class BlendMode(Enum):
    """Blend mode for UI draw calls."""
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"


# =============================================================================
# Internal Helpers
# =============================================================================


def _uid() -> str:
    """Generate a unique identifier string."""
    return uuid.uuid4().hex


def _now() -> float:
    """Return the current time as a float."""
    return _time_module.time()


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a float value to the range [lo, hi]."""
    return max(lo, min(hi, value))


# Pass execution order (lower = rendered first / behind)
_PASS_ORDER: Dict[UIRenderPass, int] = {
    UIRenderPass.BACKGROUND: 0,
    UIRenderPass.WIDGETS: 10,
    UIRenderPass.OVERLAY: 20,
    UIRenderPass.TOOLTIP: 30,
    UIRenderPass.MODAL: 40,
    UIRenderPass.NOTIFICATION: 50,
    UIRenderPass.DEBUG: 60,
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class UIRenderConfig:
    """Configuration for the UI rendering pipeline.

    Controls resolution, batching limits, IMGUI integration, DPI scaling,
    and per-pass enable flags for the UI render pipeline.
    """

    config_id: str = field(default_factory=_uid)
    target_width: int = 1920
    target_height: int = 1080
    scale_factor: float = 1.0
    dpi_aware: bool = True
    enable_batching: bool = True
    max_batch_size: int = 128
    enable_imgui: bool = True
    enable_post_processing: bool = True
    enable_scissor_test: bool = True
    clear_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    pass_enabled: Dict[str, bool] = field(default_factory=dict)
    default_font_size: int = 14
    default_blend: BlendMode = BlendMode.NORMAL
    created_at: float = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.pass_enabled:
            self.pass_enabled = {p.value: True for p in UIRenderPass}

    def is_pass_enabled(self, pass_type: UIRenderPass) -> bool:
        """Check whether a given UI render pass is enabled."""
        return self.pass_enabled.get(pass_type.value, True)

    def set_pass_enabled(self, pass_type: UIRenderPass, enabled: bool) -> None:
        """Enable or disable a UI render pass."""
        self.pass_enabled[pass_type.value] = enabled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "target_width": self.target_width,
            "target_height": self.target_height,
            "scale_factor": self.scale_factor,
            "dpi_aware": self.dpi_aware,
            "enable_batching": self.enable_batching,
            "max_batch_size": self.max_batch_size,
            "enable_imgui": self.enable_imgui,
            "enable_post_processing": self.enable_post_processing,
            "enable_scissor_test": self.enable_scissor_test,
            "clear_color": list(self.clear_color),
            "pass_enabled": dict(self.pass_enabled),
            "default_font_size": self.default_font_size,
            "default_blend": self.default_blend.value,
            "created_at": self.created_at,
        }


@dataclass
class Widget:
    """A UI widget definition created by a registered factory.

    Widgets carry a type, layout properties, visual style, and an opaque
    properties bag used by the widget factory to construct the runtime
    representation. Widgets are arranged into a layout tree before
    draw-call generation.
    """

    widget_id: str = field(default_factory=_uid)
    widget_type: WidgetType = WidgetType.PANEL
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    anchor: Tuple[float, float] = (0.0, 0.0)
    margin: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    padding: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    visible: bool = True
    enabled: bool = True
    render_pass: UIRenderPass = UIRenderPass.WIDGETS
    blend_mode: BlendMode = BlendMode.NORMAL
    texture_id: str = ""
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    z_order: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def contains(self, px: float, py: float) -> bool:
        """Hit-test whether a point lies within this widget's rect."""
        return self.x <= px <= self.right and self.y <= py <= self.bottom

    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "anchor": list(self.anchor),
            "margin": list(self.margin),
            "padding": list(self.padding),
            "visible": self.visible,
            "enabled": self.enabled,
            "render_pass": self.render_pass.value,
            "blend_mode": self.blend_mode.value,
            "texture_id": self.texture_id,
            "color": list(self.color),
            "z_order": self.z_order,
            "properties": dict(self.properties),
            "children": list(self.children),
            "created_at": self.created_at,
        }


@dataclass
class LayoutNode:
    """A node in the computed layout tree.

    Each node holds the final computed rectangle for a widget along with
    references to its children. Layout nodes are produced by
    `UIRenderingPipeline.compute_layout` and consumed by
    `UIRenderingPipeline.build_draw_calls`.
    """

    node_id: str = field(default_factory=_uid)
    widget_id: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    z_order: int = 0
    visible: bool = True
    render_pass: UIRenderPass = UIRenderPass.WIDGETS
    child_ids: List[str] = field(default_factory=list)
    depth: int = 0
    computed: bool = False
    created_at: float = field(default_factory=_now)

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "widget_id": self.widget_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "z_order": self.z_order,
            "visible": self.visible,
            "render_pass": self.render_pass.value,
            "child_ids": list(self.child_ids),
            "depth": self.depth,
            "computed": self.computed,
            "created_at": self.created_at,
        }


@dataclass
class DrawCall:
    """A single UI draw call.

    Encapsulates the texture, vertex range, blend mode, scissor rect, and
    sort key required to issue a single GPU draw call for a UI element.
    """

    call_id: str = field(default_factory=_uid)
    texture_id: str = ""
    vertex_count: int = 0
    index_count: int = 0
    blend_mode: BlendMode = BlendMode.NORMAL
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    scissor: Optional[Tuple[float, float, float, float]] = None
    sort_key: float = 0.0
    render_pass: UIRenderPass = UIRenderPass.WIDGETS
    z_order: int = 0
    visible: bool = True
    widget_id: str = ""
    user_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "texture_id": self.texture_id,
            "vertex_count": self.vertex_count,
            "index_count": self.index_count,
            "blend_mode": self.blend_mode.value,
            "color": list(self.color),
            "scissor": list(self.scissor) if self.scissor else None,
            "sort_key": self.sort_key,
            "render_pass": self.render_pass.value,
            "z_order": self.z_order,
            "visible": self.visible,
            "widget_id": self.widget_id,
            "user_data": dict(self.user_data),
        }


@dataclass
class UIBatch:
    """A batch of merged UI draw calls sharing render state.

    Batching reduces GPU state changes by grouping draw calls that share
    the same texture, blend mode, and render pass. The batch records the
    total vertex/index counts and the number of state changes saved.
    """

    batch_id: str = field(default_factory=_uid)
    texture_id: str = ""
    blend_mode: BlendMode = BlendMode.NORMAL
    render_pass: UIRenderPass = UIRenderPass.WIDGETS
    call_ids: List[str] = field(default_factory=list)
    call_count: int = 0
    total_vertices: int = 0
    total_indices: int = 0
    state_changes_saved: int = 0
    sort_key: float = 0.0
    z_order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "texture_id": self.texture_id,
            "blend_mode": self.blend_mode.value,
            "render_pass": self.render_pass.value,
            "call_ids": list(self.call_ids),
            "call_count": self.call_count,
            "total_vertices": self.total_vertices,
            "total_indices": self.total_indices,
            "state_changes_saved": self.state_changes_saved,
            "sort_key": self.sort_key,
            "z_order": self.z_order,
        }


@dataclass
class UIRenderStats:
    """UI rendering statistics for a frame or cumulative session.

    Tracks draw call counts, batch savings, layout timings, and per-pass
    execution times for profiling and auto-quality adjustment.
    """

    frame_id: int = 0
    timestamp: float = field(default_factory=_now)
    total_widgets: int = 0
    visible_widgets: int = 0
    total_draw_calls: int = 0
    visible_draw_calls: int = 0
    total_batches: int = 0
    state_changes_saved: int = 0
    total_vertices: int = 0
    total_indices: int = 0
    layout_time_us: float = 0.0
    build_time_us: float = 0.0
    batch_time_us: float = 0.0
    render_time_us: float = 0.0
    post_process_time_us: float = 0.0
    pass_timings: Dict[str, float] = field(default_factory=dict)
    imgui_draw_calls: int = 0
    imgui_vertices: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "total_widgets": self.total_widgets,
            "visible_widgets": self.visible_widgets,
            "total_draw_calls": self.total_draw_calls,
            "visible_draw_calls": self.visible_draw_calls,
            "total_batches": self.total_batches,
            "state_changes_saved": self.state_changes_saved,
            "total_vertices": self.total_vertices,
            "total_indices": self.total_indices,
            "layout_time_us": round(self.layout_time_us, 2),
            "build_time_us": round(self.build_time_us, 2),
            "batch_time_us": round(self.batch_time_us, 2),
            "render_time_us": round(self.render_time_us, 2),
            "post_process_time_us": round(self.post_process_time_us, 2),
            "pass_timings": dict(self.pass_timings),
            "imgui_draw_calls": self.imgui_draw_calls,
            "imgui_vertices": self.imgui_vertices,
        }


@dataclass
class UIRenderSnapshot:
    """Complete UI render system snapshot.

    Captures the full state of the UI rendering pipeline at a point in
    time: configuration, statistics, batch list, and pass timings.
    """

    snapshot_id: str = field(default_factory=_uid)
    frame_id: int = 0
    timestamp: float = field(default_factory=_now)
    config: Optional[UIRenderConfig] = None
    stats: Optional[UIRenderStats] = None
    batches: List[UIBatch] = field(default_factory=list)
    pass_timings: Dict[str, float] = field(default_factory=dict)
    widget_count: int = 0
    draw_call_count: int = 0
    batch_count: int = 0
    pipeline_state: str = "idle"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "config": self.config.to_dict() if self.config else None,
            "stats": self.stats.to_dict() if self.stats else None,
            "batches": [b.to_dict() for b in self.batches],
            "pass_timings": dict(self.pass_timings),
            "widget_count": self.widget_count,
            "draw_call_count": self.draw_call_count,
            "batch_count": self.batch_count,
            "pipeline_state": self.pipeline_state,
        }


# =============================================================================
# UIRenderingPipeline (Singleton)
# =============================================================================


class UIRenderingPipeline:
    """Complete UI rendering pipeline for the SparkLabs AI-native game engine.

    Coordinates UI layout composition, draw call generation and batching,
    IMGUI integration, widget rendering, and UI-specific post-processing
    effects. Thread-safe via RLock and double-checked locking singleton.

    Subsystems:
        Widget Registry   — factories for creating widgets by type
        Layout Tree       — computed layout nodes arranged by strategy
        Draw Call Queue   — UI draw calls sorted and bucketed by pass
        Batch Cache       — merged draw call batches for GPU submission
        IMGUI Bridge      — immediate-mode UI integration hook
        Post-Process Stack — UI-specific screen-space effects
    """

    _instance: Optional["UIRenderingPipeline"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "UIRenderingPipeline":
        """Thread-safe singleton construction with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize render state, widget registry, layout tree, and draw call queue."""
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._instance_lock = threading.RLock()

        # Configuration & state
        self._config: Optional[UIRenderConfig] = None
        self._initialized_pipeline: bool = False
        self._is_rendering: bool = False
        self._frame_count: int = 0

        # Widget registry: type -> factory callable
        self._widget_factories: Dict[WidgetType, Callable[..., Widget]] = {}

        # Widget registry: widget_id -> Widget
        self._widgets: Dict[str, Widget] = OrderedDict()

        # Layout tree: node_id -> LayoutNode
        self._layout_nodes: Dict[str, LayoutNode] = OrderedDict()
        self._layout_root_id: Optional[str] = None

        # Draw call queue: call_id -> DrawCall
        self._draw_calls: Dict[str, DrawCall] = OrderedDict()

        # Batch cache: batch_id -> UIBatch
        self._batches: Dict[str, UIBatch] = OrderedDict()

        # IMGUI integration state
        self._imgui_enabled: bool = False
        self._imgui_draw_data: Optional[Dict[str, Any]] = None

        # Post-processing state for UI
        self._post_effects: Dict[str, bool] = {
            "blur": False,
            "glow": False,
            "drop_shadow": True,
            "rounded_corners": True,
        }

        # Frame statistics history
        self._frame_stats: List[UIRenderStats] = []
        self._max_stats_history: int = 300

        # Cumulative stats
        self._cumulative_stats: Dict[str, Any] = {
            "frames_rendered": 0,
            "widgets_created": 0,
            "widgets_removed": 0,
            "draw_calls_built": 0,
            "batches_built": 0,
            "state_changes_saved": 0,
            "layout_computations": 0,
            "post_process_passes": 0,
        }

    @classmethod
    def get_instance(cls) -> "UIRenderingPipeline":
        """Return the singleton UIRenderingPipeline instance."""
        return cls()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[UIRenderConfig] = None) -> UIRenderConfig:
        """Initialize the UI rendering pipeline with an optional configuration.

        Args:
            config: Optional UIRenderConfig. If None, a default config is created.

        Returns:
            The active UIRenderConfig after initialization.
        """
        with self._instance_lock:
            if config is None:
                config = UIRenderConfig()
            self._config = config
            self._imgui_enabled = config.enable_imgui
            self._initialized_pipeline = True
            return config

    def _ensure_initialized(self) -> UIRenderConfig:
        """Ensure the pipeline has been initialized, returning the active config."""
        if self._config is None or not self._initialized_pipeline:
            self.initialize()
        assert self._config is not None
        return self._config

    # ------------------------------------------------------------------
    # Widget Factory & Registry
    # ------------------------------------------------------------------

    def register_widget(
        self,
        widget_type: WidgetType,
        factory: Callable[..., Widget],
    ) -> bool:
        """Register a widget factory for a given widget type.

        Args:
            widget_type: The WidgetType the factory produces.
            factory: A callable that accepts keyword arguments and returns a Widget.

        Returns:
            True if the factory was registered (overwriting any prior), False if
            the widget_type was already registered and not overwritten.
        """
        with self._instance_lock:
            already = widget_type in self._widget_factories
            self._widget_factories[widget_type] = factory
            return not already

    def create_widget(
        self,
        widget_type: WidgetType,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[Widget]:
        """Create a UI widget using the registered factory for its type.

        Args:
            widget_type: The type of widget to create.
            properties: Optional property bag forwarded to the factory.

        Returns:
            The newly created Widget, or None if no factory is registered
            for the given type.
        """
        with self._instance_lock:
            factory = self._widget_factories.get(widget_type)
            if factory is None:
                return None
            props = dict(properties or {})
            try:
                widget = factory(**props)
            except Exception:
                return None
            if not isinstance(widget, Widget):
                return None
            widget.widget_type = widget_type
            self._widgets[widget.widget_id] = widget
            self._cumulative_stats["widgets_created"] += 1
            return widget

    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget from the registry by ID.

        Args:
            widget_id: The unique identifier of the widget to remove.

        Returns:
            True if the widget was found and removed, False otherwise.
        """
        with self._instance_lock:
            if widget_id not in self._widgets:
                return False
            del self._widgets[widget_id]
            self._cumulative_stats["widgets_removed"] += 1
            return True

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        """Retrieve a widget by ID."""
        with self._instance_lock:
            return self._widgets.get(widget_id)

    def list_widgets(
        self,
        widget_type: Optional[WidgetType] = None,
    ) -> List[Widget]:
        """List all registered widgets, optionally filtered by type."""
        with self._instance_lock:
            if widget_type is None:
                return list(self._widgets.values())
            return [w for w in self._widgets.values() if w.widget_type == widget_type]

    # ------------------------------------------------------------------
    # Layout Computation
    # ------------------------------------------------------------------

    def compute_layout(
        self,
        root_widget: Widget,
        strategy: LayoutStrategy = LayoutStrategy.ABSOLUTE,
    ) -> LayoutNode:
        """Compute layout for a widget tree using the given strategy.

        Args:
            root_widget: The root Widget of the tree to lay out.
            strategy: The LayoutStrategy to apply (FLEXBOX, GRID, ABSOLUTE,
                ANCHOR, FLOW, STACK).

        Returns:
            The root LayoutNode of the computed layout tree.
        """
        layout_start = _time_module.perf_counter()
        with self._instance_lock:
            config = self._ensure_initialized()

            # Build layout tree recursively
            root_node = self._build_layout_node(root_widget, 0, strategy, config)

            # Apply strategy-specific positioning
            self._apply_strategy(root_node, strategy, config)

            # Store the layout tree
            self._layout_nodes.clear()
            self._flatten_layout_tree(root_node)
            self._layout_root_id = root_node.node_id

            root_node.computed = True
            self._cumulative_stats["layout_computations"] += 1

            layout_end = _time_module.perf_counter()
            self._last_layout_time_us = (layout_end - layout_start) * 1_000_000.0
            return root_node

    def _build_layout_node(
        self,
        widget: Widget,
        depth: int,
        strategy: LayoutStrategy,
        config: UIRenderConfig,
    ) -> LayoutNode:
        """Recursively build a LayoutNode from a Widget and its children."""
        node = LayoutNode(
            widget_id=widget.widget_id,
            x=widget.x,
            y=widget.y,
            width=widget.width,
            height=widget.height,
            z_order=widget.z_order,
            visible=widget.visible,
            render_pass=widget.render_pass,
            depth=depth,
        )
        for child_id in widget.children:
            child_widget = self._widgets.get(child_id)
            if child_widget is None:
                continue
            child_node = self._build_layout_node(
                child_widget, depth + 1, strategy, config
            )
            node.child_ids.append(child_node.node_id)
            self._layout_nodes[child_node.node_id] = child_node
        return node

    def _flatten_layout_tree(self, node: LayoutNode) -> None:
        """Insert a node and recurse into children to populate the node map."""
        self._layout_nodes[node.node_id] = node

    def _apply_strategy(
        self,
        root: LayoutNode,
        strategy: LayoutStrategy,
        config: UIRenderConfig,
    ) -> None:
        """Apply strategy-specific positioning to a layout tree.

        ABSOLUTE/STACK: positions are left as-is on the widgets.
        FLEXBOX/FLOW: children are stacked vertically with padding gaps.
        GRID: children arranged in a square-ish grid.
        ANCHOR: children offset by their anchor relative to root center.
        """
        if strategy in (LayoutStrategy.ABSOLUTE, LayoutStrategy.STACK):
            return
        children = [
            self._layout_nodes.get(cid) for cid in root.child_ids
            if cid in self._layout_nodes
        ]
        if not children:
            return

        if strategy in (LayoutStrategy.FLEXBOX, LayoutStrategy.FLOW):
            cursor_x = root.x
            cursor_y = root.y
            for child in children:
                child.x = cursor_x
                child.y = cursor_y
                cursor_y += child.height + 4.0
        elif strategy == LayoutStrategy.GRID:
            import math as _math
            count = len(children)
            cols = max(1, int(_math.ceil(_math.sqrt(count))))
            cell_w = root.width / cols if cols > 0 else 0.0
            cell_h = max(c.height for c in children) if children else 0.0
            for i, child in enumerate(children):
                row = i // cols
                col = i % cols
                child.x = root.x + col * cell_w
                child.y = root.y + row * cell_h
        elif strategy == LayoutStrategy.ANCHOR:
            cx = root.x + root.width / 2.0
            cy = root.y + root.height / 2.0
            for child in children:
                ax, ay = (0.5, 0.5)
                widget = self._widgets.get(child.widget_id)
                if widget is not None:
                    ax, ay = widget.anchor
                child.x = cx - child.width * ax
                child.y = cy - child.height * ay

    # ------------------------------------------------------------------
    # Draw Call Generation
    # ------------------------------------------------------------------

    def build_draw_calls(self, layout_root: LayoutNode) -> List[DrawCall]:
        """Build draw calls from a layout tree.

        Traverses the layout tree depth-first, emitting one DrawCall per
        visible node ordered by z-order and render pass.

        Args:
            layout_root: The root LayoutNode produced by `compute_layout`.

        Returns:
            An ordered list of DrawCall objects.
        """
        build_start = _time_module.perf_counter()
        with self._instance_lock:
            self._draw_calls.clear()
            calls: List[DrawCall] = []

            self._collect_draw_calls(layout_root, calls)

            # Sort by render pass order, then z-order, then y (top first)
            calls.sort(
                key=lambda c: (
                    _PASS_ORDER.get(c.render_pass, 99),
                    c.z_order,
                    c.sort_key,
                )
            )

            for call in calls:
                self._draw_calls[call.call_id] = call

            self._cumulative_stats["draw_calls_built"] += len(calls)
            self._last_build_time_us = (_time_module.perf_counter() - build_start) * 1_000_000.0
            return calls

    def _collect_draw_calls(
        self,
        node: LayoutNode,
        out: List[DrawCall],
    ) -> None:
        """Recursively collect draw calls from layout nodes."""
        if not node.visible:
            return
        widget = self._widgets.get(node.widget_id)
        if widget is not None:
            call = DrawCall(
                texture_id=widget.texture_id,
                vertex_count=4,
                index_count=6,
                blend_mode=widget.blend_mode,
                color=widget.color,
                scissor=(node.x, node.y, node.width, node.height),
                sort_key=node.y + node.x * 0.001,
                render_pass=node.render_pass,
                z_order=node.z_order,
                visible=node.visible,
                widget_id=node.widget_id,
            )
            out.append(call)
        for child_id in node.child_ids:
            child = self._layout_nodes.get(child_id)
            if child is not None:
                self._collect_draw_calls(child, out)

    # ------------------------------------------------------------------
    # Batching
    # ------------------------------------------------------------------

    def batch_draw_calls(
        self,
        draw_calls: List[DrawCall],
    ) -> List[UIBatch]:
        """Batch draw calls for efficiency.

        Groups consecutive draw calls that share the same texture, blend
        mode, and render pass into a single UIBatch up to the configured
        max batch size.

        Args:
            draw_calls: The ordered list of DrawCall objects to batch.

        Returns:
            A list of UIBatch objects in draw order.
        """
        batch_start = _time_module.perf_counter()
        with self._instance_lock:
            config = self._ensure_initialized()
            self._batches.clear()

            if not config.enable_batching:
                batches: List[UIBatch] = []
                for call in draw_calls:
                    if not call.visible:
                        continue
                    batch = UIBatch(
                        texture_id=call.texture_id,
                        blend_mode=call.blend_mode,
                        render_pass=call.render_pass,
                        call_ids=[call.call_id],
                        call_count=1,
                        total_vertices=call.vertex_count,
                        total_indices=call.index_count,
                        sort_key=call.sort_key,
                        z_order=call.z_order,
                    )
                    self._batches[batch.batch_id] = batch
                    batches.append(batch)
                self._cumulative_stats["batches_built"] += len(batches)
                self._last_batch_time_us = (
                    _time_module.perf_counter() - batch_start
                ) * 1_000_000.0
                return batches

            current: Optional[UIBatch] = None
            result: List[UIBatch] = []
            max_size = max(1, config.max_batch_size)

            for call in draw_calls:
                if not call.visible:
                    continue
                can_merge = (
                    current is not None
                    and current.texture_id == call.texture_id
                    and current.blend_mode == call.blend_mode
                    and current.render_pass == call.render_pass
                    and current.call_count < max_size
                )
                if can_merge and current is not None:
                    current.call_ids.append(call.call_id)
                    current.call_count += 1
                    current.total_vertices += call.vertex_count
                    current.total_indices += call.index_count
                    current.state_changes_saved += 1
                    self._cumulative_stats["state_changes_saved"] += 1
                else:
                    if current is not None:
                        self._batches[current.batch_id] = current
                        result.append(current)
                    current = UIBatch(
                        texture_id=call.texture_id,
                        blend_mode=call.blend_mode,
                        render_pass=call.render_pass,
                        call_ids=[call.call_id],
                        call_count=1,
                        total_vertices=call.vertex_count,
                        total_indices=call.index_count,
                        sort_key=call.sort_key,
                        z_order=call.z_order,
                    )

            if current is not None:
                self._batches[current.batch_id] = current
                result.append(current)

            self._cumulative_stats["batches_built"] += len(result)
            self._last_batch_time_us = (
                _time_module.perf_counter() - batch_start
            ) * 1_000_000.0
            return result

    # ------------------------------------------------------------------
    # Frame Rendering
    # ------------------------------------------------------------------

    def render_frame(self) -> UIRenderStats:
        """Render a complete UI frame.

        Executes the full pipeline: layout computation, draw call
        generation, batching, per-pass execution, and UI post-processing.
        Records statistics and returns them.

        Returns:
            The UIRenderStats for the rendered frame.
        """
        render_start = _time_module.perf_counter()
        with self._instance_lock:
            config = self._ensure_initialized()
            self._is_rendering = True

            pass_timings: Dict[str, float] = {}

            # Find a root widget (first parent-less widget) to drive layout
            root_widget: Optional[Widget] = None
            for w in self._widgets.values():
                if not any(w.widget_id in other.children for other in self._widgets.values()):
                    root_widget = w
                    break

            total_draw_calls = 0
            visible_draw_calls = 0
            total_batches = 0
            state_changes_saved = 0
            total_vertices = 0
            total_indices = 0
            imgui_draw_calls = 0
            imgui_vertices = 0

            if root_widget is not None:
                # Layout pass
                layout_root = self.compute_layout(
                    root_widget, LayoutStrategy.ABSOLUTE
                )
                pass_timings["layout"] = getattr(self, "_last_layout_time_us", 0.0)

                # Draw call build pass
                calls = self.build_draw_calls(layout_root)
                pass_timings["build"] = getattr(self, "_last_build_time_us", 0.0)
                total_draw_calls = len(calls)
                visible_draw_calls = sum(1 for c in calls if c.visible)

                # Batch pass
                batches = self.batch_draw_calls(calls)
                pass_timings["batch"] = getattr(self, "_last_batch_time_us", 0.0)
                total_batches = len(batches)
                state_changes_saved = sum(b.state_changes_saved for b in batches)
                total_vertices = sum(b.total_vertices for b in batches)
                total_indices = sum(b.total_indices for b in batches)

                # Per-pass execution simulation
                for pass_type in UIRenderPass:
                    if not config.is_pass_enabled(pass_type):
                        continue
                    pass_start = _time_module.perf_counter()
                    pass_calls = [c for c in calls if c.render_pass == pass_type]
                    _ = len(pass_calls)  # simulate work
                    pass_timings[pass_type.value] = (
                        _time_module.perf_counter() - pass_start
                    ) * 1_000_000.0

            # IMGUI pass
            if self._imgui_enabled:
                imgui_start = _time_module.perf_counter()
                imgui_draw_calls, imgui_vertices = self._render_imgui()
                pass_timings["imgui"] = (
                    _time_module.perf_counter() - imgui_start
                ) * 1_000_000.0

            # Post-processing
            post_time = 0.0
            if config.enable_post_processing:
                post_start = _time_module.perf_counter()
                for pass_type in UIRenderPass:
                    self.apply_post_processing(pass_type)
                post_time = (
                    _time_module.perf_counter() - post_start
                ) * 1_000_000.0
                pass_timings["post_process"] = post_time
                self._cumulative_stats["post_process_passes"] += 1

            render_end = _time_module.perf_counter()
            render_time_us = (render_end - render_start) * 1_000_000.0

            self._frame_count += 1
            self._cumulative_stats["frames_rendered"] += 1

            stats = UIRenderStats(
                frame_id=self._frame_count,
                total_widgets=len(self._widgets),
                visible_widgets=sum(1 for w in self._widgets.values() if w.visible),
                total_draw_calls=total_draw_calls,
                visible_draw_calls=visible_draw_calls,
                total_batches=total_batches,
                state_changes_saved=state_changes_saved,
                total_vertices=total_vertices,
                total_indices=total_indices,
                layout_time_us=pass_timings.get("layout", 0.0),
                build_time_us=pass_timings.get("build", 0.0),
                batch_time_us=pass_timings.get("batch", 0.0),
                render_time_us=render_time_us,
                post_process_time_us=post_time,
                pass_timings=pass_timings,
                imgui_draw_calls=imgui_draw_calls,
                imgui_vertices=imgui_vertices,
            )

            self._frame_stats.append(stats)
            if len(self._frame_stats) > self._max_stats_history:
                self._frame_stats = self._frame_stats[-self._max_stats_history:]

            self._is_rendering = False
            return stats

    def _render_imgui(self) -> Tuple[int, int]:
        """Render the IMGUI draw data and return (draw_calls, vertices).

        This is a stub integration point: real implementations would
        forward to the bound IMGUI backend. Here we simulate draw data
        derived from the cached imgui draw data dictionary.
        """
        if not self._imgui_enabled or self._imgui_draw_data is None:
            return 0, 0
        cmd_lists = self._imgui_draw_data.get("cmd_lists", [])
        draw_calls = 0
        vertices = 0
        for cmd_list in cmd_lists:
            draw_calls += len(cmd_list.get("commands", []))
            vertices += cmd_list.get("vertex_count", 0)
        return draw_calls, vertices

    def set_imgui_draw_data(self, draw_data: Dict[str, Any]) -> None:
        """Set the IMGUI draw data for the next frame.

        Args:
            draw_data: The IMGUI draw data dictionary produced by the
                immediate-mode UI backend.
        """
        with self._instance_lock:
            self._imgui_draw_data = draw_data

    def enable_imgui(self, enabled: bool) -> None:
        """Enable or disable IMGUI rendering integration."""
        with self._instance_lock:
            self._imgui_enabled = enabled

    # ------------------------------------------------------------------
    # Post-Processing
    # ------------------------------------------------------------------

    def apply_post_processing(self, pass_type: UIRenderPass) -> bool:
        """Apply UI post-processing effects for a given render pass.

        Applies configured UI-specific effects (drop shadow, rounded
        corners, glow, blur) to the rendered output of a pass.

        Args:
            pass_type: The UIRenderPass whose output should be processed.

        Returns:
            True if any post-processing effect was applied, False otherwise.
        """
        with self._instance_lock:
            config = self._ensure_initialized()
            if not config.enable_post_processing:
                return False
            applied = False
            for effect_name, enabled in self._post_effects.items():
                if not enabled:
                    continue
                # Skip heavy blur for interactive passes
                if effect_name == "blur" and pass_type in (
                    UIRenderPass.WIDGETS,
                    UIRenderPass.DEBUG,
                ):
                    continue
                applied = True
            return applied

    def set_post_effect_enabled(self, effect_name: str, enabled: bool) -> bool:
        """Enable or disable a UI post-processing effect by name.

        Args:
            effect_name: One of 'blur', 'glow', 'drop_shadow', 'rounded_corners'.
            enabled: True to enable, False to disable.

        Returns:
            True if the effect existed and was updated, False otherwise.
        """
        with self._instance_lock:
            if effect_name not in self._post_effects:
                return False
            self._post_effects[effect_name] = enabled
            return True

    def get_post_effects(self) -> Dict[str, bool]:
        """Get the current UI post-processing effect enable states."""
        with self._instance_lock:
            return dict(self._post_effects)

    # ------------------------------------------------------------------
    # Hit Testing
    # ------------------------------------------------------------------

    def get_widget_at(self, point: Tuple[float, float]) -> Optional[Widget]:
        """Hit test for the topmost widget at a point.

        Walks the layout tree in reverse z-order to find the front-most
        visible widget whose rect contains the point.

        Args:
            point: The (x, y) screen-space point to test.

        Returns:
            The topmost Widget at the point, or None if none matched.
        """
        with self._instance_lock:
            px, py = point
            candidates: List[Tuple[int, float, Widget]] = []
            for widget in self._widgets.values():
                if not widget.visible or not widget.enabled:
                    continue
                if widget.contains(px, py):
                    candidates.append((widget.z_order, widget.y, widget))
            if not candidates:
                return None
            # Highest z-order first, then lowest y (front-most visually)
            candidates.sort(key=lambda t: (-t[0], t[1]))
            return candidates[0][2]

    # ------------------------------------------------------------------
    # Statistics & Status
    # ------------------------------------------------------------------

    def get_render_stats(self) -> UIRenderStats:
        """Get rendering statistics for the most recent frame.

        Returns:
            The UIRenderStats of the last rendered frame, or an empty
            stats object if no frame has been rendered yet.
        """
        with self._instance_lock:
            if self._frame_stats:
                return self._frame_stats[-1]
            return UIRenderStats()

    def get_stats_history(self, count: int = 60) -> List[UIRenderStats]:
        """Get recent frame render statistics.

        Args:
            count: The maximum number of recent stats to return.

        Returns:
            A list of up to `count` recent UIRenderStats objects.
        """
        with self._instance_lock:
            return list(self._frame_stats[-count:])

    def get_average_stats(self) -> Dict[str, Any]:
        """Get averaged UI rendering statistics over recent history."""
        with self._instance_lock:
            if not self._frame_stats:
                return {}
            n = len(self._frame_stats)
            avg_draw_calls = sum(s.total_draw_calls for s in self._frame_stats) / n
            avg_batches = sum(s.total_batches for s in self._frame_stats) / n
            avg_vertices = sum(s.total_vertices for s in self._frame_stats) / n
            avg_render_us = sum(s.render_time_us for s in self._frame_stats) / n
            avg_fps = 1_000_000.0 / avg_render_us if avg_render_us > 0 else 0.0
            return {
                "frame_count": n,
                "frame_id": self._frame_count,
                "average_fps": round(avg_fps, 1),
                "average_draw_calls": int(avg_draw_calls),
                "average_batches": int(avg_batches),
                "average_vertices": int(avg_vertices),
                "average_render_us": round(avg_render_us, 2),
            }

    def get_status(self) -> Dict[str, Any]:
        """Get the UI render system status.

        Returns:
            A dictionary describing the current pipeline state, config
            summary, widget counts, and cumulative statistics.
        """
        with self._instance_lock:
            config_dict = self._config.to_dict() if self._config else None
            widget_type_counts: Dict[str, int] = {}
            for w in self._widgets.values():
                key = w.widget_type.value
                widget_type_counts[key] = widget_type_counts.get(key, 0) + 1
            pass_counts: Dict[str, int] = {}
            for c in self._draw_calls.values():
                key = c.render_pass.value
                pass_counts[key] = pass_counts.get(key, 0) + 1
            return {
                "initialized": self._initialized_pipeline,
                "is_rendering": self._is_rendering,
                "frame_count": self._frame_count,
                "config": config_dict,
                "imgui_enabled": self._imgui_enabled,
                "widget_count": len(self._widgets),
                "layout_node_count": len(self._layout_nodes),
                "draw_call_count": len(self._draw_calls),
                "batch_count": len(self._batches),
                "widget_types": widget_type_counts,
                "draw_calls_by_pass": pass_counts,
                "post_effects": dict(self._post_effects),
                "cumulative": dict(self._cumulative_stats),
                "average_stats": self.get_average_stats(),
            }

    def snapshot(self) -> UIRenderSnapshot:
        """Capture a complete UI render system snapshot.

        Returns:
            A UIRenderSnapshot containing config, stats, batches, and
            pass timings for the most recent frame.
        """
        with self._instance_lock:
            latest = self._frame_stats[-1] if self._frame_stats else UIRenderStats()
            return UIRenderSnapshot(
                frame_id=self._frame_count,
                config=self._config,
                stats=latest,
                batches=list(self._batches.values()),
                pass_timings=dict(latest.pass_timings),
                widget_count=len(self._widgets),
                draw_call_count=len(self._draw_calls),
                batch_count=len(self._batches),
                pipeline_state="rendering" if self._is_rendering else "idle",
            )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Graceful shutdown of the UI rendering pipeline.

        Releases widget references, clears layout/draw/batch caches,
        disables IMGUI, and marks the pipeline as not initialized.
        The singleton instance remains retrievable but must be
        re-initialized before further use.
        """
        with self._instance_lock:
            self._is_rendering = False
            self._imgui_enabled = False
            self._imgui_draw_data = None
            self._widgets.clear()
            self._widget_factories.clear()
            self._layout_nodes.clear()
            self._layout_root_id = None
            self._draw_calls.clear()
            self._batches.clear()
            self._frame_stats.clear()
            self._post_effects = {
                "blur": False,
                "glow": False,
                "drop_shadow": True,
                "rounded_corners": True,
            }
            self._config = None
            self._initialized_pipeline = False

    def reset(self) -> None:
        """Reset the pipeline to a freshly initialized state.

        Equivalent to shutdown() followed by initialize() with defaults.
        """
        with self._instance_lock:
            self.shutdown()
            self.initialize()


# =============================================================================
# Module-Level Factory
# =============================================================================


def get_ui_rendering_pipeline() -> UIRenderingPipeline:
    """Get the UIRenderingPipeline singleton instance."""
    return UIRenderingPipeline.get_instance()
