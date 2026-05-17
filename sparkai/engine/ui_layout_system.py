"""
SparkLabs Engine - UI Layout System

Anchor-based positioning and container layout system for the
SparkLabs AI-native game engine. Provides anchor-preset positioning,
flexbox-style container layouts, grid containers, and responsive
sizing modes for UI elements.

Architecture:
  UILayoutSystem (singleton orchestrator)
    |-- UIAnchor (percentage-based position anchor with pixel margins)
    |-- UIContainer (box model container with children and layout rect)
    |-- UILayout (named layout with root container and anchors)
    |-- ContainerType / AlignmentType / SizeMode / AnchorMode (enums)

Layout Flow:
  1. Define layout with root container
  2. Add child containers organized in a tree
  3. Set anchors for game nodes within parent containers
  4. Compute final pixel positions through container arrangement
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class ContainerType(Enum):
    NONE = "none"
    BOX = "box"
    HBOX = "hbox"
    VBOX = "vbox"
    GRID = "grid"
    SCROLL = "scroll"
    CENTER = "center"
    PANEL = "panel"
    MARGIN_CONTAINER = "margin_container"
    ASPECT_RATIO_CONTAINER = "aspect_ratio_container"


class AlignmentType(Enum):
    START = "start"
    CENTER = "center"
    END = "end"
    STRETCH = "stretch"
    SPACE_BETWEEN = "space_between"
    SPACE_AROUND = "space_around"


class SizeMode(Enum):
    FIXED = "fixed"
    EXPAND = "expand"
    FIT_CONTENT = "fit_content"
    ASPECT_RATIO = "aspect_ratio"
    PERCENT = "percent"


class AnchorMode(Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    FULL_RECT = "full_rect"
    TOP_WIDE = "top_wide"
    BOTTOM_WIDE = "bottom_wide"
    LEFT_TALL = "left_tall"
    RIGHT_TALL = "right_tall"


# ---------------------------------------------------------------------------
# Anchor Presets — canonical (left, top, right, bottom) values for each mode
# ---------------------------------------------------------------------------

_ANCHOR_PRESETS: Dict[AnchorMode, Tuple[float, float, float, float]] = {
    AnchorMode.TOP_LEFT: (0.0, 0.0, 0.0, 0.0),
    AnchorMode.TOP_CENTER: (0.5, 0.0, 0.5, 0.0),
    AnchorMode.TOP_RIGHT: (1.0, 0.0, 1.0, 0.0),
    AnchorMode.CENTER_LEFT: (0.0, 0.5, 0.0, 0.5),
    AnchorMode.CENTER: (0.5, 0.5, 0.5, 0.5),
    AnchorMode.CENTER_RIGHT: (1.0, 0.5, 1.0, 0.5),
    AnchorMode.BOTTOM_LEFT: (0.0, 1.0, 0.0, 1.0),
    AnchorMode.BOTTOM_CENTER: (0.5, 1.0, 0.5, 1.0),
    AnchorMode.BOTTOM_RIGHT: (1.0, 1.0, 1.0, 1.0),
    AnchorMode.FULL_RECT: (0.0, 0.0, 1.0, 1.0),
    AnchorMode.TOP_WIDE: (0.0, 0.0, 1.0, 0.0),
    AnchorMode.BOTTOM_WIDE: (0.0, 1.0, 1.0, 1.0),
    AnchorMode.LEFT_TALL: (0.0, 0.0, 0.0, 1.0),
    AnchorMode.RIGHT_TALL: (1.0, 0.0, 1.0, 1.0),
}


# ---------------------------------------------------------------------------
# Anchor Mode helpers (patched into AnchorMode so callers can do
# AnchorMode.from_points(left, top, right, bottom) .)
# ---------------------------------------------------------------------------

def _anchor_mode_from_points(
    cls: type,
    anchor_left: float,
    anchor_top: float,
    anchor_right: float,
    anchor_bottom: float,
) -> AnchorMode:
    """Return the nearest AnchorMode for a given set of anchor values.

    Each AnchorMode preset maps to canonical (left, top, right, bottom)
    anchor values. The method computes Euclidean distance in 4-D anchor
    space and returns the closest mode.
    """
    best_mode: AnchorMode = AnchorMode.TOP_LEFT
    best_dist: float = float("inf")
    for mode, (al, at, ar, ab) in _ANCHOR_PRESETS.items():
        dist = math.sqrt(
            (anchor_left - al) ** 2
            + (anchor_top - at) ** 2
            + (anchor_right - ar) ** 2
            + (anchor_bottom - ab) ** 2
        )
        if dist < best_dist:
            best_dist = dist
            best_mode = mode
    return best_mode


AnchorMode.from_points = classmethod(_anchor_mode_from_points)  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Severity for metric thresholds
# ---------------------------------------------------------------------------


class MetricSeverity(Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class OverlaySection(Enum):
    FPS = "fps"
    FRAME_TIME = "frame_time"
    MEMORY = "memory"
    DRAW_CALLS = "draw_calls"
    OBJECTS = "objects"
    PHYSICS = "physics"
    SCRIPT_CPU = "script_cpu"
    GPU_TIME = "gpu_time"
    ALL = "all"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class FrameSample:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    delta_time: float = 0.0
    fps: float = 0.0
    draw_calls: int = 0
    triangle_count: int = 0
    memory_used_mb: float = 0.0
    cpu_time_ms: float = 0.0
    gpu_time_ms: float = 0.0
    physics_time_ms: float = 0.0
    script_time_ms: float = 0.0
    object_count: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "delta_time": self.delta_time,
            "fps": self.fps,
            "draw_calls": self.draw_calls,
            "triangle_count": self.triangle_count,
            "memory_used_mb": self.memory_used_mb,
            "cpu_time_ms": self.cpu_time_ms,
            "gpu_time_ms": self.gpu_time_ms,
            "physics_time_ms": self.physics_time_ms,
            "script_time_ms": self.script_time_ms,
            "object_count": self.object_count,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrameSample":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            frame_number=data.get("frame_number", 0),
            delta_time=data.get("delta_time", 0.0),
            fps=data.get("fps", 0.0),
            draw_calls=data.get("draw_calls", 0),
            triangle_count=data.get("triangle_count", 0),
            memory_used_mb=data.get("memory_used_mb", 0.0),
            cpu_time_ms=data.get("cpu_time_ms", 0.0),
            gpu_time_ms=data.get("gpu_time_ms", 0.0),
            physics_time_ms=data.get("physics_time_ms", 0.0),
            script_time_ms=data.get("script_time_ms", 0.0),
            object_count=data.get("object_count", 0),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class MetricThreshold:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metric_name: str = ""
    warning_threshold: float = 0.0
    error_threshold: float = 0.0
    is_enabled: bool = True

    def evaluate(self, current_value: float) -> MetricSeverity:
        if not self.is_enabled:
            return MetricSeverity.OK
        if self.error_threshold != 0.0 and current_value >= self.error_threshold:
            return MetricSeverity.ERROR
        if self.warning_threshold != 0.0 and current_value >= self.warning_threshold:
            return MetricSeverity.WARNING
        return MetricSeverity.OK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "metric_name": self.metric_name,
            "warning_threshold": self.warning_threshold,
            "error_threshold": self.error_threshold,
            "is_enabled": self.is_enabled,
        }


@dataclass
class ProfilingSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    samples: List[FrameSample] = field(default_factory=list)
    avg_fps: float = 0.0
    min_fps: float = 0.0
    max_fps: float = 0.0
    fps_stddev: float = 0.0
    sample_count: int = 0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def finalize(self) -> None:
        fps_values = [s.fps for s in self.samples]
        self.sample_count = len(self.samples)
        if not fps_values:
            self.avg_fps = 0.0
            self.min_fps = 0.0
            self.max_fps = 0.0
            self.fps_stddev = 0.0
            self.duration_seconds = 0.0
            return
        self.avg_fps = sum(fps_values) / len(fps_values)
        self.min_fps = min(fps_values)
        self.max_fps = max(fps_values)
        if len(fps_values) > 1:
            mean = self.avg_fps
            variance = sum((f - mean) ** 2 for f in fps_values) / len(fps_values)
            self.fps_stddev = math.sqrt(variance)
        else:
            self.fps_stddev = 0.0
        if self.samples:
            self.duration_seconds = (
                self.samples[-1].timestamp - self.samples[0].timestamp
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "avg_fps": self.avg_fps,
            "min_fps": self.min_fps,
            "max_fps": self.max_fps,
            "fps_stddev": self.fps_stddev,
            "sample_count": self.sample_count,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
        }


@dataclass
class UIAnchor:
    """Anchor definition mapping a node to a position within a parent rect.

    anchor_left / anchor_top mark the origin point (0.0 - 1.0 relative
    to parent width/height). anchor_right / anchor_bottom define the
    extent when stretching across the parent. Margins are pixel offsets
    applied after calculating the anchor position.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_id: str = ""
    anchor_left: float = 0.0
    anchor_top: float = 0.0
    anchor_right: float = 0.0
    anchor_bottom: float = 0.0
    margin_left: float = 0.0
    margin_top: float = 0.0
    margin_right: float = 0.0
    margin_bottom: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "anchor_left": self.anchor_left,
            "anchor_top": self.anchor_top,
            "anchor_right": self.anchor_right,
            "anchor_bottom": self.anchor_bottom,
            "margin_left": self.margin_left,
            "margin_top": self.margin_top,
            "margin_right": self.margin_right,
            "margin_bottom": self.margin_bottom,
        }


@dataclass
class UIContainer:
    """Box-model container within a layout tree.

    Holds a layout rect (x, y, w, h), a list of child container ids,
    padding and gap for auto-layout, and an alignment policy.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    container_type: ContainerType = ContainerType.NONE
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    w: float = 100.0
    h: float = 100.0
    padding_top: float = 0.0
    padding_right: float = 0.0
    padding_bottom: float = 0.0
    padding_left: float = 0.0
    gap: float = 4.0
    alignment: AlignmentType = AlignmentType.START
    created_at: float = field(default_factory=time.time)

    def content_rect(self) -> Tuple[float, float, float, float]:
        cx = self.x + self.padding_left
        cy = self.y + self.padding_top
        cw = max(0.0, self.w - self.padding_left - self.padding_right)
        ch = max(0.0, self.h - self.padding_top - self.padding_bottom)
        return (cx, cy, cw, ch)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "container_type": self.container_type.value,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "padding_top": self.padding_top,
            "padding_right": self.padding_right,
            "padding_bottom": self.padding_bottom,
            "padding_left": self.padding_left,
            "gap": self.gap,
            "alignment": self.alignment.value,
            "created_at": self.created_at,
        }


@dataclass
class UILayout:
    """A complete UI layout definition.

    Holds a tree of UIContainer instances rooted at root_container_id,
    along with per-node UIAnchor bindings and a theme reference.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_container_id: str = ""
    containers: Dict[str, UIContainer] = field(default_factory=dict)
    anchors: Dict[str, UIAnchor] = field(default_factory=dict)
    theme_name: str = "default"
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# UILayoutSystem — Singleton Orchestrator
# ---------------------------------------------------------------------------


class UILayoutSystem:
    """Performance debug overlay and layout orchestration system.

    Records per-frame performance samples, manages container layout
    trees, anchors game nodes within parent rects, and produces
    formatted overlay text for in-game display. Supports profiling
    snapshots and configurable metric thresholds.
    """

    _instance: Optional["UILayoutSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_ROLLING_SAMPLES: int = 300

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._samples: List[FrameSample] = []
        self._thresholds: Dict[str, MetricThreshold] = {}
        self._snapshots: List[ProfilingSnapshot] = []
        self._sample_count: int = 0
        self._snapshot_count: int = 0
        self._layouts: Dict[str, UILayout] = {}
        self._layout_count: int = 0
        self._container_count: int = 0
        self._is_capturing: bool = False
        self._active_snapshot: Optional[ProfilingSnapshot] = None
        self._init_default_thresholds()

    @classmethod
    def get_instance(cls) -> "UILayoutSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Default Thresholds
    # ------------------------------------------------------------------

    def _init_default_thresholds(self) -> None:
        defaults: Dict[str, Tuple[float, float]] = {
            "fps": (45.0, 30.0),         # warning <45, error <30 → rising danger
            "frame_time": (22.0, 33.0),
            "memory": (500.0, 1000.0),
            "draw_calls": (2000.0, 5000.0),
            "objects": (5000.0, 10000.0),
            "cpu_time": (16.0, 32.0),
            "gpu_time": (16.0, 32.0),
        }
        for metric_name, (warn, err) in defaults.items():
            self._thresholds[metric_name] = MetricThreshold(
                metric_name=metric_name,
                warning_threshold=warn,
                error_threshold=err,
            )

    # ------------------------------------------------------------------
    # Frame Recording
    # ------------------------------------------------------------------

    def record_frame(
        self,
        delta_time: float = 0.0,
        draw_calls: int = 0,
        triangle_count: int = 0,
        memory_used_mb: float = 0.0,
        cpu_time_ms: float = 0.0,
        gpu_time_ms: float = 0.0,
        physics_time_ms: float = 0.0,
        script_time_ms: float = 0.0,
        object_count: int = 0,
    ) -> FrameSample:
        frame_number = len(self._samples) + 1
        fps = 1000.0 / delta_time if delta_time > 0.0 else 0.0
        sample = FrameSample(
            frame_number=frame_number,
            delta_time=delta_time,
            fps=fps,
            draw_calls=draw_calls,
            triangle_count=triangle_count,
            memory_used_mb=memory_used_mb,
            cpu_time_ms=cpu_time_ms,
            gpu_time_ms=gpu_time_ms,
            physics_time_ms=physics_time_ms,
            script_time_ms=script_time_ms,
            object_count=object_count,
        )
        self._samples.append(sample)
        self._sample_count += 1
        # Rolling window
        if len(self._samples) > self.MAX_ROLLING_SAMPLES:
            self._samples.pop(0)
        # Feed into active snapshot
        if self._is_capturing and self._active_snapshot is not None:
            self._active_snapshot.samples.append(sample)
        return sample

    # ------------------------------------------------------------------
    # FPS / Frame-Time Queries
    # ------------------------------------------------------------------

    def get_current_fps(self) -> float:
        recent = self._samples[-60:]
        if not recent:
            return 0.0
        return sum(s.fps for s in recent) / len(recent)

    def get_frame_time_stats(self) -> Dict[str, float]:
        recent = self._samples[-60:]
        if not recent:
            return {"avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
        deltas = [s.delta_time for s in recent]
        return {
            "avg_ms": sum(deltas) / len(deltas),
            "min_ms": min(deltas),
            "max_ms": max(deltas),
        }

    def get_memory_usage(self) -> Dict[str, float]:
        if not self._samples:
            return {"current_mb": 0.0, "peak_mb": 0.0}
        current = self._samples[-1].memory_used_mb
        peak = max(s.memory_used_mb for s in self._samples)
        return {"current_mb": current, "peak_mb": peak}

    # ------------------------------------------------------------------
    # Metric Summary by Overlay Section
    # ------------------------------------------------------------------

    def get_metric_summary(
        self, overlay_section: OverlaySection
    ) -> Dict[str, Any]:
        if not self._samples:
            return {"current": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0, "severity": MetricSeverity.OK.value}
        recent = self._samples[-60:]
        extractors: Dict[OverlaySection, Any] = {
            OverlaySection.FPS: lambda s: s.fps,
            OverlaySection.FRAME_TIME: lambda s: s.delta_time,
            OverlaySection.MEMORY: lambda s: s.memory_used_mb,
            OverlaySection.DRAW_CALLS: lambda s: s.draw_calls,
            OverlaySection.OBJECTS: lambda s: s.object_count,
            OverlaySection.PHYSICS: lambda s: s.physics_time_ms,
            OverlaySection.SCRIPT_CPU: lambda s: s.script_time_ms,
            OverlaySection.GPU_TIME: lambda s: s.gpu_time_ms,
        }
        if overlay_section == OverlaySection.ALL:
            return {section.name: self.get_metric_summary(section) for section in OverlaySection if section != OverlaySection.ALL}
        extractor = extractors.get(overlay_section)
        if extractor is None:
            return {"current": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0, "severity": MetricSeverity.OK.value}
        values = [extractor(s) for s in recent]
        current = extractor(self._samples[-1])
        avg = sum(values) / len(values)
        severity = MetricSeverity.OK
        threshold_key = overlay_section.value
        if threshold_key in self._thresholds:
            severity = self._thresholds[threshold_key].evaluate(current)
        return {
            "current": current,
            "avg": avg,
            "min": min(values),
            "max": max(values),
            "severity": severity.value,
        }

    # ------------------------------------------------------------------
    # Threshold Management
    # ------------------------------------------------------------------

    def set_threshold(
        self,
        metric_name: str,
        warning: float,
        error: float,
    ) -> str:
        existing = self._thresholds.get(metric_name)
        if existing:
            existing.warning_threshold = warning
            existing.error_threshold = error
            existing.is_enabled = True
            return existing.id
        threshold = MetricThreshold(
            metric_name=metric_name,
            warning_threshold=warning,
            error_threshold=error,
        )
        self._thresholds[metric_name] = threshold
        return threshold.id

    def check_thresholds(self) -> List[Dict[str, Any]]:
        if not self._samples:
            return []
        latest = self._samples[-1]
        metric_values: Dict[str, float] = {
            "fps": latest.fps,
            "frame_time": latest.delta_time,
            "memory": latest.memory_used_mb,
            "draw_calls": float(latest.draw_calls),
            "objects": float(latest.object_count),
            "cpu_time": latest.cpu_time_ms,
            "gpu_time": latest.gpu_time_ms,
        }
        results: List[Dict[str, Any]] = []
        for metric_name, threshold in self._thresholds.items():
            if not threshold.is_enabled:
                continue
            value = metric_values.get(metric_name, 0.0)
            severity = threshold.evaluate(value)
            if severity != MetricSeverity.OK:
                results.append({
                    "metric_name": metric_name,
                    "current_value": value,
                    "severity": severity.value,
                    "warning_threshold": threshold.warning_threshold,
                    "error_threshold": threshold.error_threshold,
                })
        return results

    # ------------------------------------------------------------------
    # Layout Creation / Container Tree
    # ------------------------------------------------------------------

    def create_layout(self, name: str, theme_name: str = "default") -> str:
        root = UIContainer(
            name=f"{name}_root",
            container_type=ContainerType.BOX,
        )
        layout = UILayout(
            name=name,
            root_container_id=root.id,
            theme_name=theme_name,
        )
        layout.containers[root.id] = root
        self._layouts[layout.id] = layout
        self._layout_count += 1
        self._container_count += 1
        return layout.id

    def add_container(
        self,
        layout_id: str,
        parent_id: str,
        name: str,
        container_type: ContainerType = ContainerType.NONE,
        x: float = 0.0,
        y: float = 0.0,
        w: float = 100.0,
        h: float = 100.0,
    ) -> Optional[str]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None
        if not parent_id:
            parent_id = layout.root_container_id
        parent = layout.containers.get(parent_id)
        if parent is None:
            return None
        container = UIContainer(
            name=name,
            container_type=container_type,
            parent_id=parent_id,
            x=x,
            y=y,
            w=w,
            h=h,
        )
        layout.containers[container.id] = container
        self._container_count += 1
        parent.children_ids.append(container.id)
        self.arrange_children(layout_id, parent_id)
        return container.id

    def remove_container(self, layout_id: str, container_id: str) -> bool:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return False
        container = layout.containers.get(container_id)
        if container is None:
            return False
        # Reparent children to the removed container's parent
        for child_id in container.children_ids:
            child = layout.containers.get(child_id)
            if child is not None:
                child.parent_id = container.parent_id
                if container.parent_id and container.parent_id in layout.containers:
                    layout.containers[container.parent_id].children_ids.append(child_id)
        # Remove from parent's children_ids
        if container.parent_id and container.parent_id in layout.containers:
            parent = layout.containers[container.parent_id]
            parent.children_ids = [cid for cid in parent.children_ids if cid != container_id]
        # Remove anchors referencing this container
        anchor_keys = [k for k, a in layout.anchors.items() if a.node_id == container_id]
        for key in anchor_keys:
            del layout.anchors[key]
        del layout.containers[container_id]
        return True

    def get_container_chain(
        self, layout_id: str, container_id: str
    ) -> Optional[List[str]]:
        layout = self._layouts.get(layout_id)
        if layout is None or container_id not in layout.containers:
            return None
        chain: List[str] = []
        current_id: Optional[str] = container_id
        while current_id is not None:
            chain.insert(0, current_id)
            container = layout.containers.get(current_id)
            current_id = container.parent_id if container else None
        return chain

    # ------------------------------------------------------------------
    # Anchor Binding
    # ------------------------------------------------------------------

    def set_anchor(
        self,
        layout_id: str,
        node_id: str,
        anchor_mode: AnchorMode = AnchorMode.TOP_LEFT,
        margins: Optional[Tuple[float, float, float, float]] = None,
    ) -> Optional[str]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None
        al, at, ar, ab = _ANCHOR_PRESETS.get(anchor_mode, (0.0, 0.0, 0.0, 0.0))
        ml, mt, mr, mb = (margins if margins is not None else (0.0, 0.0, 0.0, 0.0))
        existing_id: Optional[str] = None
        for anchor in layout.anchors.values():
            if anchor.node_id == node_id:
                existing_id = anchor.id
                break
        if existing_id:
            anchor = layout.anchors[existing_id]
            anchor.anchor_left = al
            anchor.anchor_top = at
            anchor.anchor_right = ar
            anchor.anchor_bottom = ab
            anchor.margin_left = ml
            anchor.margin_top = mt
            anchor.margin_right = mr
            anchor.margin_bottom = mb
            return existing_id
        anchor = UIAnchor(
            node_id=node_id,
            anchor_left=al,
            anchor_top=at,
            anchor_right=ar,
            anchor_bottom=ab,
            margin_left=ml,
            margin_top=mt,
            margin_right=mr,
            margin_bottom=mb,
        )
        layout.anchors[anchor.id] = anchor
        return anchor.id

    def resolve_anchor_position(
        self,
        layout_id: str,
        node_id: str,
        parent_rect: Tuple[float, float, float, float],
    ) -> Optional[Tuple[float, float, float, float]]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None
        anchor: Optional[UIAnchor] = None
        for a in layout.anchors.values():
            if a.node_id == node_id:
                anchor = a
                break
        if anchor is None:
            return None
        px, py, pw, ph = parent_rect
        x = px + anchor.anchor_left * pw + anchor.margin_left
        y = py + anchor.anchor_top * ph + anchor.margin_top
        w = (anchor.anchor_right - anchor.anchor_left) * pw - anchor.margin_left + anchor.margin_right
        h = (anchor.anchor_bottom - anchor.anchor_top) * ph - anchor.margin_top + anchor.margin_bottom
        return (x, y, max(0.0, w), max(0.0, h))

    # ------------------------------------------------------------------
    # Container Layout (Rect Computation & Child Arrangement)
    # ------------------------------------------------------------------

    def compute_container_rect(
        self,
        layout_id: str,
        container_id: str,
        available_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1920.0, 1080.0),
    ) -> Optional[Tuple[float, float, float, float]]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None
        container = layout.containers.get(container_id)
        if container is None:
            return None
        ax, ay, aw, ah = available_rect
        # Anchor resolution if this container has an anchor bound
        resolved = self.resolve_anchor_position(layout_id, container_id, available_rect)
        if resolved is not None:
            return resolved
        # Use container's own rect relative to available space
        return (ax + container.x, ay + container.y, container.w, container.h)

    def arrange_children(self, layout_id: str, container_id: str) -> bool:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return False
        container = layout.containers.get(container_id)
        if container is None:
            return False
        child_ids = container.children_ids
        if not child_ids:
            return True
        cx, cy, cw, ch = container.content_rect()
        ctype = container.container_type
        if ctype == ContainerType.HBOX:
            self._arrange_hbox(layout, child_ids, cx, cy, cw, ch, container.gap, container.alignment)
        elif ctype == ContainerType.VBOX:
            self._arrange_vbox(layout, child_ids, cx, cy, cw, ch, container.gap, container.alignment)
        elif ctype == ContainerType.GRID:
            self._arrange_grid(layout, child_ids, cx, cy, cw, ch, container.gap)
        elif ctype == ContainerType.CENTER:
            self._arrange_center(layout, child_ids, cx, cy, cw, ch)
        # BOX / NONE / SCROLL: children keep their manually assigned positions
        return True

    def _arrange_hbox(
        self,
        layout: UILayout,
        child_ids: List[str],
        cx: float,
        cy: float,
        cw: float,
        ch: float,
        gap: float,
        alignment: AlignmentType,
    ) -> None:
        children = [layout.containers[cid] for cid in child_ids if cid in layout.containers]
        if not children:
            return
        total_width = sum(c.w for c in children) + gap * (len(children) - 1)
        offset_x = cx
        if alignment == AlignmentType.CENTER:
            offset_x += max(0.0, (cw - total_width) / 2.0)
        elif alignment == AlignmentType.END:
            offset_x += max(0.0, cw - total_width)
        elif alignment == AlignmentType.SPACE_BETWEEN and len(children) > 1:
            gap = max(0.0, (cw - sum(c.w for c in children)) / (len(children) - 1))
        elif alignment == AlignmentType.SPACE_AROUND and len(children) > 0:
            padding = max(0.0, (cw - sum(c.w for c in children)) / (len(children) + 1))
            offset_x += padding
            gap = padding * 2.0 if len(children) > 1 else padding

        for child in children:
            child.x = offset_x
            child.y = cy
            if alignment == AlignmentType.STRETCH:
                child.y = cy
                child.h = ch
            offset_x += child.w + gap

    def _arrange_vbox(
        self,
        layout: UILayout,
        child_ids: List[str],
        cx: float,
        cy: float,
        cw: float,
        ch: float,
        gap: float,
        alignment: AlignmentType,
    ) -> None:
        children = [layout.containers[cid] for cid in child_ids if cid in layout.containers]
        if not children:
            return
        total_height = sum(c.h for c in children) + gap * (len(children) - 1)
        offset_y = cy
        if alignment == AlignmentType.CENTER:
            offset_y += max(0.0, (ch - total_height) / 2.0)
        elif alignment == AlignmentType.END:
            offset_y += max(0.0, ch - total_height)
        elif alignment == AlignmentType.SPACE_BETWEEN and len(children) > 1:
            gap = max(0.0, (ch - sum(c.h for c in children)) / (len(children) - 1))
        elif alignment == AlignmentType.SPACE_AROUND and len(children) > 0:
            padding = max(0.0, (ch - sum(c.h for c in children)) / (len(children) + 1))
            offset_y += padding
            gap = padding * 2.0 if len(children) > 1 else padding

        for child in children:
            child.x = cx
            child.y = offset_y
            if alignment == AlignmentType.STRETCH:
                child.x = cx
                child.w = cw
            offset_y += child.h + gap

    def _arrange_grid(
        self,
        layout: UILayout,
        child_ids: List[str],
        cx: float,
        cy: float,
        cw: float,
        ch: float,
        gap: float,
    ) -> None:
        children = [layout.containers[cid] for cid in child_ids if cid in layout.containers]
        if not children:
            return
        cols = max(1, int(math.sqrt(len(children))))
        col_index = 0
        row_index = 0
        cell_width = (cw - gap * (cols - 1)) / cols if cols > 0 else cw
        for child in children:
            child.x = cx + col_index * (cell_width + gap)
            child.y = cy + row_index * (child.h + gap)
            child.w = cell_width
            col_index += 1
            if col_index >= cols:
                col_index = 0
                row_index += 1

    def _arrange_center(
        self,
        layout: UILayout,
        child_ids: List[str],
        cx: float,
        cy: float,
        cw: float,
        ch: float,
    ) -> None:
        for cid in child_ids:
            child = layout.containers.get(cid)
            if child is None:
                continue
            child.x = cx + (cw - child.w) / 2.0
            child.y = cy + (ch - child.h) / 2.0

    # ------------------------------------------------------------------
    # Size Mode Computation
    # ------------------------------------------------------------------

    @staticmethod
    def get_size_for_mode(
        mode: SizeMode,
        available_space: Tuple[float, float],
        content_size: Tuple[float, float],
        aspect_ratio: float = 1.0,
    ) -> Tuple[float, float]:
        aw, ah = available_space
        cw, ch = content_size
        if mode == SizeMode.FIXED:
            return (cw, ch)
        elif mode == SizeMode.EXPAND:
            return (aw, ah)
        elif mode == SizeMode.FIT_CONTENT:
            return (min(cw, aw), min(ch, ah))
        elif mode == SizeMode.PERCENT:
            return (cw * aw, ch * ah)
        elif mode == SizeMode.ASPECT_RATIO:
            ratio = aspect_ratio if aspect_ratio > 0.0 else 1.0
            if aw / ratio >= ah:
                return (ah * ratio, ah)
            else:
                return (aw, aw / ratio)
        return (cw, ch)

    # ------------------------------------------------------------------
    # Profiling Snapshots
    # ------------------------------------------------------------------

    def start_snapshot(self, name: str) -> str:
        snapshot = ProfilingSnapshot(name=name)
        self._active_snapshot = snapshot
        self._is_capturing = True
        return snapshot.id

    def stop_snapshot(self) -> Optional[str]:
        if self._active_snapshot is None or not self._is_capturing:
            return None
        self._is_capturing = False
        self._active_snapshot.finalize()
        self._snapshots.append(self._active_snapshot)
        self._snapshot_count += 1
        sid = self._active_snapshot.id
        self._active_snapshot = None
        return sid

    def get_recent_snapshots(self, limit: int = 10) -> List[ProfilingSnapshot]:
        return self._snapshots[-limit:]

    # ------------------------------------------------------------------
    # Overlay Text Generation
    # ------------------------------------------------------------------

    def generate_overlay_text(
        self,
        sections: Optional[List[OverlaySection]] = None,
    ) -> str:
        if sections is None:
            sections = [OverlaySection.ALL]
        lines: List[str] = []
        for section in sections:
            summary = self.get_metric_summary(section)
            if section == OverlaySection.ALL:
                for key, sub in summary.items():
                    lines.append(
                        f"[{sub['severity'].upper()} {key:>12s}] "
                        f"cur={sub['current']:7.1f} "
                        f"avg={sub['avg']:7.1f} "
                        f"min={sub['min']:7.1f} "
                        f"max={sub['max']:7.1f}"
                    )
            else:
                lines.append(
                    f"[{summary['severity'].upper()} {section.value:>12s}] "
                    f"cur={summary['current']:7.1f} "
                    f"avg={summary['avg']:7.1f} "
                    f"min={summary['min']:7.1f} "
                    f"max={summary['max']:7.1f}"
                )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset_metrics(self) -> None:
        self._samples.clear()
        self._sample_count = 0

    # ------------------------------------------------------------------
    # Serialization (Export / Import)
    # ------------------------------------------------------------------

    def export_layout(self, layout_id: str) -> Optional[Dict[str, Any]]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None
        return {
            "id": layout.id,
            "name": layout.name,
            "root_container_id": layout.root_container_id,
            "theme_name": layout.theme_name,
            "created_at": layout.created_at,
            "containers": {
                cid: c.to_dict() for cid, c in layout.containers.items()
            },
            "anchors": {
                aid: a.to_dict() for aid, a in layout.anchors.items()
            },
        }

    def import_layout(self, data: Dict[str, Any]) -> str:
        layout = UILayout(
            name=data.get("name", "Imported"),
            root_container_id=data.get("root_container_id", ""),
            theme_name=data.get("theme_name", "default"),
            created_at=data.get("created_at", time.time()),
        )
        for cid, cdata in data.get("containers", {}).items():
            ct_value = cdata.get("container_type", "none")
            ct = ContainerType(ct_value) if ct_value in {e.value for e in ContainerType} else ContainerType.NONE
            al_value = cdata.get("alignment", "start")
            al = AlignmentType(al_value) if al_value in {e.value for e in AlignmentType} else AlignmentType.START
            layout.containers[cid] = UIContainer(
                id=cdata.get("id", cid),
                name=cdata.get("name", ""),
                container_type=ct,
                parent_id=cdata.get("parent_id"),
                children_ids=cdata.get("children_ids", []),
                x=cdata.get("x", 0.0),
                y=cdata.get("y", 0.0),
                w=cdata.get("w", 100.0),
                h=cdata.get("h", 100.0),
                padding_top=cdata.get("padding_top", 0.0),
                padding_right=cdata.get("padding_right", 0.0),
                padding_bottom=cdata.get("padding_bottom", 0.0),
                padding_left=cdata.get("padding_left", 0.0),
                gap=cdata.get("gap", 4.0),
                alignment=al,
                created_at=cdata.get("created_at", time.time()),
            )
        for aid, adata in data.get("anchors", {}).items():
            layout.anchors[aid] = UIAnchor(
                id=adata.get("id", aid),
                node_id=adata.get("node_id", ""),
                anchor_left=adata.get("anchor_left", 0.0),
                anchor_top=adata.get("anchor_top", 0.0),
                anchor_right=adata.get("anchor_right", 0.0),
                anchor_bottom=adata.get("anchor_bottom", 0.0),
                margin_left=adata.get("margin_left", 0.0),
                margin_top=adata.get("margin_top", 0.0),
                margin_right=adata.get("margin_right", 0.0),
                margin_bottom=adata.get("margin_bottom", 0.0),
            )
        self._layouts[layout.id] = layout
        self._layout_count += 1
        self._container_count += len(layout.containers)
        return layout.id

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        type_breakdown: Dict[str, int] = {}
        total_containers = 0
        for layout in self._layouts.values():
            for container in layout.containers.values():
                ct = container.container_type.value
                type_breakdown[ct] = type_breakdown.get(ct, 0) + 1
                total_containers += 1
        return {
            "layout_count": self._layout_count,
            "container_count": self._container_count,
            "sample_count": self._sample_count,
            "snapshot_count": self._snapshot_count,
            "active_snapshots": 1 if self._is_capturing else 0,
            "threshold_count": len(self._thresholds),
            "rolling_window_size": len(self._samples),
            "type_breakdown": type_breakdown,
        }


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

def get_ui_layout_system() -> UILayoutSystem:
    return UILayoutSystem.get_instance()