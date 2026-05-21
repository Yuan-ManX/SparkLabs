"""
SparkLabs Engine - Gizmo System

Editor gizmo system providing visual transform manipulation tools for
scene objects within the editor viewport. Supports translate, rotate,
and scale gizmos with configurable snapping, axis constraints, and
multi-selection box selection.

Architecture:
  GizmoSystem
    |-- GizmoConfig (per-instance gizmo mode, space, snap, and axis settings)
    |-- TransformHandle (on-screen draggable handles for per-axis manipulation)
    |-- SelectionBox (rubber-band rectangle for multi-object selection)
    |-- SnapSettings (grid/angle/scale step configuration for precise editing)

Gizmo Features:
  - TRANSLATE: move selected objects along X, Y, Z or planar axes (XY, XZ, YZ)
  - ROTATE: rotate selected objects about a specified axis with degree snapping
  - SCALE: uniform or per-axis scaling with percentage-step snapping
  - BOX_SELECT: drag-to-select multiple objects via screen-space rectangle
  - SPACE: toggle between local, world, and view coordinate spaces
  - SNAPPING: grid-based vertex/edge snapping, angle increment, scale percent
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class GizmoMode(Enum):
    TRANSLATE = "translate"
    ROTATE = "rotate"
    SCALE = "scale"
    BOX_SELECT = "box_select"


class GizmoAxis(Enum):
    X = "x"
    Y = "y"
    Z = "z"
    XY = "xy"
    XZ = "xz"
    YZ = "yz"
    NONE = "none"


class GizmoSpace(Enum):
    LOCAL = "local"
    WORLD = "world"
    VIEW = "view"


class SnappingMode(Enum):
    NONE = "none"
    GRID = "grid"
    VERTEX = "vertex"
    EDGE = "edge"
    ANGLE = "angle"
    SCALE_PCT = "scale_pct"


@dataclass
class GizmoConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: GizmoMode = GizmoMode.TRANSLATE
    space: GizmoSpace = GizmoSpace.WORLD
    snap_mode: SnappingMode = SnappingMode.NONE
    axis: GizmoAxis = GizmoAxis.NONE
    is_active: bool = False
    target_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "space": self.space.value,
            "snap_mode": self.snap_mode.value,
            "axis": self.axis.value,
            "is_active": self.is_active,
            "target_ids": self.target_ids,
            "created_at": self.created_at,
        }


@dataclass
class TransformHandle:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mode: GizmoMode = GizmoMode.TRANSLATE
    axis: GizmoAxis = GizmoAxis.X
    last_delta: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    is_dragging: bool = False
    world_matrix: List[float] = field(default_factory=lambda: [1.0] * 16)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "position": list(self.position),
            "mode": self.mode.value,
            "axis": self.axis.value,
            "last_delta": list(self.last_delta),
            "is_dragging": self.is_dragging,
        }


@dataclass
class SelectionBox:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    start_pos: Tuple[float, float] = (0.0, 0.0)
    end_pos: Tuple[float, float] = (0.0, 0.0)
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start_pos": list(self.start_pos),
            "end_pos": list(self.end_pos),
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class SnapSettings:
    grid_size: float = 1.0
    angle_step: float = 15.0
    scale_step: float = 0.1
    translation_step: float = 1.0
    rotation_step: float = 15.0
    is_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_size": self.grid_size,
            "angle_step": self.angle_step,
            "scale_step": self.scale_step,
            "translation_step": self.translation_step,
            "rotation_step": self.rotation_step,
            "is_enabled": self.is_enabled,
        }


class GizmoSystem:
    """Editor gizmo system for visual transform manipulation in the viewport."""

    _instance: Optional["GizmoSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._configs: Dict[str, GizmoConfig] = {}
        self._handles: Dict[str, TransformHandle] = {}
        self._boxes: Dict[str, SelectionBox] = {}
        self._snap_settings = SnapSettings()
        self._active_config_id: Optional[str] = None
        self._selection_state: List[str] = []
        self._operation_log: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "GizmoSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Config Management ----

    def create_config(self,
                      mode: str = "translate",
                      space: str = "world",
                      snap_mode: str = "none",
                      axis: str = "none") -> Optional[GizmoConfig]:
        try:
            gm = GizmoMode(mode.lower())
        except ValueError:
            gm = GizmoMode.TRANSLATE
        try:
            gs = GizmoSpace(space.lower())
        except ValueError:
            gs = GizmoSpace.WORLD
        try:
            sm = SnappingMode(snap_mode.lower())
        except ValueError:
            sm = SnappingMode.NONE
        try:
            ga = GizmoAxis(axis.lower())
        except ValueError:
            ga = GizmoAxis.NONE

        config = GizmoConfig(
            mode=gm,
            space=gs,
            snap_mode=sm,
            axis=ga,
        )
        self._configs[config.id] = config
        self._operation_log.append({
            "action": "config_created",
            "config_id": config.id,
            "mode": gm.value,
            "space": gs.value,
            "timestamp": time.time(),
        })
        return config

    def activate_gizmo(self,
                       config_id: str,
                       target_ids: Optional[List[str]] = None) -> bool:
        config = self._configs.get(config_id)
        if config is None:
            return False

        if self._active_config_id and self._active_config_id != config_id:
            old_config = self._configs.get(self._active_config_id)
            if old_config:
                old_config.is_active = False

        config.is_active = True
        config.target_ids = target_ids or []
        self._active_config_id = config_id
        self._selection_state = list(config.target_ids)
        self._operation_log.append({
            "action": "gizmo_activated",
            "config_id": config_id,
            "target_count": len(config.target_ids),
            "timestamp": time.time(),
        })
        return True

    def deactivate_gizmo(self) -> bool:
        if self._active_config_id is None:
            return False
        config = self._configs.get(self._active_config_id)
        if config:
            config.is_active = False
            config.target_ids = []
        self._active_config_id = None
        self._selection_state = []
        self._handles.clear()
        self._operation_log.append({
            "action": "gizmo_deactivated",
            "timestamp": time.time(),
        })
        return True

    # ---- Transform Handles ----

    def create_transform_handle(self,
                                node_id: str,
                                position: Tuple[float, float, float],
                                mode: str = "translate") -> Optional[TransformHandle]:
        try:
            gm = GizmoMode(mode.lower())
        except ValueError:
            gm = GizmoMode.TRANSLATE

        config = self._get_active_config()

        handle = TransformHandle(
            node_id=node_id,
            position=position,
            mode=gm,
            axis=config.axis if config else GizmoAxis.X,
        )
        self._handles[handle.id] = handle
        return handle

    def move_handle(self,
                    handle_id: str,
                    delta: Tuple[float, float, float],
                    constraint_axis: Optional[str] = None) -> Optional[TransformHandle]:
        handle = self._handles.get(handle_id)
        if handle is None or not handle.is_dragging:
            return None

        resolved_axis = self._resolve_constraint_axis(constraint_axis)
        snapped_delta = self._apply_snap_to_delta(delta, handle.mode)

        if resolved_axis == GizmoAxis.X:
            snapped_delta = (snapped_delta[0], 0.0, 0.0)
        elif resolved_axis == GizmoAxis.Y:
            snapped_delta = (0.0, snapped_delta[1], 0.0)
        elif resolved_axis == GizmoAxis.Z:
            snapped_delta = (0.0, 0.0, snapped_delta[2])
        elif resolved_axis == GizmoAxis.XY:
            snapped_delta = (snapped_delta[0], snapped_delta[1], 0.0)
        elif resolved_axis == GizmoAxis.XZ:
            snapped_delta = (snapped_delta[0], 0.0, snapped_delta[2])
        elif resolved_axis == GizmoAxis.YZ:
            snapped_delta = (0.0, snapped_delta[1], snapped_delta[2])

        new_x = handle.position[0] + snapped_delta[0]
        new_y = handle.position[1] + snapped_delta[1]
        new_z = handle.position[2] + snapped_delta[2]

        handle.last_delta = snapped_delta
        handle.position = (new_x, new_y, new_z)
        return handle

    def apply_transform(self, handle_id: str) -> Dict[str, Any]:
        handle = self._handles.get(handle_id)
        if handle is None:
            return {"applied": False, "error": "handle_not_found"}

        config = self._get_active_config()
        transform_data = {
            "applied": True,
            "node_id": handle.node_id,
            "mode": handle.mode.value,
            "position": list(handle.position),
            "delta": list(handle.last_delta),
            "space": config.space.value if config else "world",
            "timestamp": time.time(),
        }

        if handle.mode == GizmoMode.TRANSLATE:
            transform_data["translation"] = list(handle.last_delta)
        elif handle.mode == GizmoMode.ROTATE:
            angle = handle.last_delta[0]
            transform_data["rotation_degrees"] = round(angle, 4)
            transform_data["axis"] = handle.axis.value
        elif handle.mode == GizmoMode.SCALE:
            transform_data["scale_factors"] = [
                round(1.0 + d, 4) for d in handle.last_delta
            ]

        self._operation_log.append({
            "action": "transform_applied",
            "handle_id": handle_id,
            "node_id": handle.node_id,
            "mode": handle.mode.value,
            "timestamp": time.time(),
        })
        return transform_data

    # ---- Snap Settings ----

    def set_snap_settings(self,
                          grid_size: float = 1.0,
                          angle_step: float = 15.0,
                          scale_step: float = 0.1) -> SnapSettings:
        self._snap_settings.grid_size = max(0.01, grid_size)
        self._snap_settings.angle_step = max(0.1, min(180.0, angle_step))
        self._snap_settings.scale_step = max(0.001, min(10.0, scale_step))
        self._snap_settings.translation_step = self._snap_settings.grid_size
        self._snap_settings.rotation_step = self._snap_settings.angle_step
        return self._snap_settings

    def snap_value(self, value: float, step: float) -> float:
        if step <= 0.0:
            return value
        return round(value / step) * step

    # ---- Box Selection ----

    def start_box_select(self,
                         start_pos: Tuple[float, float]) -> SelectionBox:
        box = SelectionBox(start_pos=start_pos)
        self._boxes[box.id] = box
        self._operation_log.append({
            "action": "box_select_started",
            "box_id": box.id,
            "start_pos": list(start_pos),
            "timestamp": time.time(),
        })
        return box

    def update_box_select(self,
                          box_id: str,
                          current_pos: Tuple[float, float]) -> Optional[SelectionBox]:
        box = self._boxes.get(box_id)
        if box is None or not box.is_active:
            return None
        box.end_pos = current_pos
        return box

    def finish_box_select(self, box_id: str) -> Dict[str, Any]:
        box = self._boxes.get(box_id)
        if box is None:
            return {"completed": False, "error": "box_not_found"}
        box.is_active = False

        min_x = min(box.start_pos[0], box.end_pos[0])
        max_x = max(box.start_pos[0], box.end_pos[0])
        min_y = min(box.start_pos[1], box.end_pos[1])
        max_y = max(box.start_pos[1], box.end_pos[1])

        area = (max_x - min_x) * (max_y - min_y)

        self._selection_state = list(self._selection_state)
        self._operation_log.append({
            "action": "box_select_finished",
            "box_id": box_id,
            "selection_count": len(self._selection_state),
            "area": round(area, 2),
            "timestamp": time.time(),
        })
        return {
            "completed": True,
            "box_id": box_id,
            "bounds": {
                "min_x": round(min_x, 2),
                "max_x": round(max_x, 2),
                "min_y": round(min_y, 2),
                "max_y": round(max_y, 2),
            },
            "area": round(area, 2),
            "selected_ids": list(self._selection_state),
        }

    # ---- Query Methods ----

    def get_active_gizmo(self) -> Optional[GizmoConfig]:
        if self._active_config_id is None:
            return None
        return self._configs.get(self._active_config_id)

    def get_stats(self) -> Dict[str, Any]:
        active_handles = sum(
            1 for h in self._handles.values() if h.is_dragging
        )
        active_boxes = sum(
            1 for b in self._boxes.values() if b.is_active
        )
        return {
            "total_configs": len(self._configs),
            "active_config_id": self._active_config_id,
            "active_gizmo_mode": (
                self._configs[self._active_config_id].mode.value
                if self._active_config_id and self._active_config_id in self._configs
                else None
            ),
            "total_handles": len(self._handles),
            "active_dragging_handles": active_handles,
            "total_selection_boxes": len(self._boxes),
            "active_boxes": active_boxes,
            "selection_count": len(self._selection_state),
            "snap_enabled": self._snap_settings.is_enabled,
            "grid_size": self._snap_settings.grid_size,
            "angle_step": self._snap_settings.angle_step,
            "scale_step": self._snap_settings.scale_step,
            "operation_count": len(self._operation_log),
        }

    # ---- Internal Helpers ----

    def _get_active_config(self) -> Optional[GizmoConfig]:
        if self._active_config_id is None:
            return None
        return self._configs.get(self._active_config_id)

    def _resolve_constraint_axis(self,
                                  constraint_axis: Optional[str]) -> GizmoAxis:
        if constraint_axis is not None:
            try:
                return GizmoAxis(constraint_axis.lower())
            except ValueError:
                pass
        config = self._get_active_config()
        if config and config.axis != GizmoAxis.NONE:
            return config.axis
        return GizmoAxis.NONE

    def _apply_snap_to_delta(self,
                              delta: Tuple[float, float, float],
                              mode: GizmoMode) -> Tuple[float, float, float]:
        config = self._get_active_config()
        if config is None or config.snap_mode == SnappingMode.NONE:
            return delta
        if not self._snap_settings.is_enabled:
            return delta

        if mode == GizmoMode.TRANSLATE or config.snap_mode == SnappingMode.GRID:
            step = self._snap_settings.translation_step
            return (
                self.snap_value(delta[0], step),
                self.snap_value(delta[1], step),
                self.snap_value(delta[2], step),
            )
        elif mode == GizmoMode.ROTATE or config.snap_mode == SnappingMode.ANGLE:
            step = self._snap_settings.rotation_step
            return (
                self.snap_value(delta[0], step),
                self.snap_value(delta[1], step),
                self.snap_value(delta[2], step),
            )
        elif mode == GizmoMode.SCALE or config.snap_mode == SnappingMode.SCALE_PCT:
            step = self._snap_settings.scale_step
            return (
                self.snap_value(delta[0], step),
                self.snap_value(delta[1], step),
                self.snap_value(delta[2], step),
            )

        return delta


def get_gizmo_system() -> GizmoSystem:
    return GizmoSystem.get_instance()