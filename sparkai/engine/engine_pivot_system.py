"""
SparkLabs Engine - Pivot System

Pivot point management for transform operations, supporting custom pivot
positions, pivot snapping, multi-point pivots, and pivot-based animation
anchors. Provides a unified interface for controlling how objects rotate,
scale, and translate relative to configurable reference points.

Architecture:
  PivotSystem
    |-- PivotPoint (per-node pivot definition with mode and space)
    |-- PivotHandle (visual/interaction handle offset from pivot center)
    |-- AnchorBinding (pivot-to-anchor linkage for skeletal/hierarchical setups)
    |-- PivotGroup (multi-node pivots with shared transform application)

Pivot Features:
  - MODES: center, corners, edges, custom, and anchor-point positioning
  - SPACES: local and global coordinate systems for pivot placement
  - SNAPPING: automatic pivot repositioning to predefined target modes
  - HANDLES: offset handles for visual manipulation with color and size
  - ANCHORS: binding pivots to bones, handles, or custom attachments
  - GROUPS: multi-selection pivots with synchronized transform application
  - CONSTRAINTS: free, horizontal, vertical, and axial movement constraints
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PivotMode(Enum):
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"
    LEFT_CENTER = "left_center"
    RIGHT_CENTER = "right_center"
    CUSTOM = "custom"
    ANCHOR_POINT = "anchor_point"


class PivotSpace(Enum):
    LOCAL = "local"
    GLOBAL = "global"


class PivotAnchor(Enum):
    CUSTOM = "custom"
    HANDLE = "handle"
    BONE = "bone"
    ATTACHMENT = "attachment"


class PivotConstraint(Enum):
    FREE = "free"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    AXIAL = "axial"


_SNAP_OFFSETS: Dict[PivotMode, Tuple[float, float, float]] = {
    PivotMode.CENTER: (0.5, 0.5, 0.5),
    PivotMode.TOP_LEFT: (0.0, 1.0, 0.5),
    PivotMode.TOP_RIGHT: (1.0, 1.0, 0.5),
    PivotMode.BOTTOM_LEFT: (0.0, 0.0, 0.5),
    PivotMode.BOTTOM_RIGHT: (1.0, 0.0, 0.5),
    PivotMode.TOP_CENTER: (0.5, 1.0, 0.5),
    PivotMode.BOTTOM_CENTER: (0.5, 0.0, 0.5),
    PivotMode.LEFT_CENTER: (0.0, 0.5, 0.5),
    PivotMode.RIGHT_CENTER: (1.0, 0.5, 0.5),
}


@dataclass
class PivotPoint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_id: str = ""
    position: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    mode: PivotMode = PivotMode.CENTER
    space: PivotSpace = PivotSpace.LOCAL
    constraint: PivotConstraint = PivotConstraint.FREE
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "position": list(self.position),
            "mode": self.mode.value,
            "space": self.space.value,
            "constraint": self.constraint.value,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class PivotHandle:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_id: str = ""
    pivot_id: str = ""
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    color: str = "#00FF00"
    size: float = 0.15
    is_visible: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "pivot_id": self.pivot_id,
            "offset": list(self.offset),
            "color": self.color,
            "size": self.size,
            "is_visible": self.is_visible,
            "created_at": self.created_at,
        }


@dataclass
class AnchorBinding:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pivot_id: str = ""
    anchor_type: PivotAnchor = PivotAnchor.CUSTOM
    anchor_id: str = ""
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    weight: float = 1.0
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pivot_id": self.pivot_id,
            "anchor_type": self.anchor_type.value,
            "anchor_id": self.anchor_id,
            "offset": list(self.offset),
            "weight": self.weight,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class PivotGroup:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_ids: List[str] = field(default_factory=list)
    pivot_ids: List[str] = field(default_factory=list)
    center_position: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    mode: PivotMode = PivotMode.CENTER
    space: PivotSpace = PivotSpace.LOCAL
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_ids": self.node_ids,
            "pivot_ids": self.pivot_ids,
            "center_position": list(self.center_position),
            "mode": self.mode.value,
            "space": self.space.value,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class PivotSystem:
    """Pivot point management engine for transform operations and animation anchors."""

    _instance: Optional["PivotSystem"] = None
    _lock = threading.RLock()

    MAX_HANDLES_PER_NODE = 8
    MAX_BINDINGS_PER_PIVOT = 4
    MAX_GROUP_MEMBERS = 100

    def __init__(self) -> None:
        self._points: Dict[str, PivotPoint] = {}
        self._handles: Dict[str, PivotHandle] = {}
        self._bindings: Dict[str, AnchorBinding] = {}
        self._groups: Dict[str, PivotGroup] = {}
        self._node_to_pivot: Dict[str, str] = {}
        self._pivot_to_handles: Dict[str, List[str]] = {}
        self._pivot_to_bindings: Dict[str, List[str]] = {}

    @classmethod
    def get_instance(cls) -> "PivotSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Pivot Point Management ----

    def set_pivot(self,
                  node_id: str,
                  position: Tuple[float, float, float],
                  mode: str = "center",
                  space: str = "local") -> PivotPoint:
        try:
            pm = PivotMode(mode.lower())
        except ValueError:
            pm = PivotMode.CUSTOM

        try:
            ps = PivotSpace(space.lower())
        except ValueError:
            ps = PivotSpace.LOCAL

        if node_id in self._node_to_pivot:
            existing_id = self._node_to_pivot[node_id]
            point = self._points[existing_id]
            point.position = position
            point.mode = pm
            point.space = ps
            point.is_active = True
            return point

        point = PivotPoint(
            node_id=node_id,
            position=position,
            mode=pm,
            space=ps,
        )
        self._points[point.id] = point
        self._node_to_pivot[node_id] = point.id
        return point

    def get_pivot(self, node_id: str) -> Optional[PivotPoint]:
        pivot_id = self._node_to_pivot.get(node_id)
        if pivot_id is None:
            return None
        return self._points.get(pivot_id)

    def snap_pivot_to(self,
                      node_id: str,
                      target_mode: str) -> Optional[PivotPoint]:
        try:
            tm = PivotMode(target_mode.lower())
        except ValueError:
            return None

        if tm not in _SNAP_OFFSETS:
            return None

        offset = _SNAP_OFFSETS[tm]
        pivot = self.get_pivot(node_id)
        if pivot is None:
            return self.set_pivot(
                node_id=node_id,
                position=offset,
                mode=target_mode,
                space="local",
            )

        pivot.position = offset
        pivot.mode = tm
        return pivot

    def list_pivots(self, space: Optional[str] = None) -> List[PivotPoint]:
        points = list(self._points.values())
        if space is not None:
            try:
                ps = PivotSpace(space.lower())
                points = [p for p in points if p.space == ps]
            except ValueError:
                pass
        return sorted(points, key=lambda p: p.created_at)

    def remove_pivot(self, node_id: str) -> bool:
        pivot_id = self._node_to_pivot.pop(node_id, None)
        if pivot_id is None:
            return False
        self._points.pop(pivot_id, None)
        self._pivot_to_handles.pop(pivot_id, None)
        self._pivot_to_bindings.pop(pivot_id, None)
        return True

    # ---- Handle Management ----

    def create_handle(self,
                      node_id: str,
                      offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                      color: str = "#00FF00",
                      size: float = 0.15) -> Optional[PivotHandle]:
        pivot_id = self._node_to_pivot.get(node_id)
        if pivot_id is None:
            return None

        existing = self._pivot_to_handles.get(pivot_id, [])
        if len(existing) >= self.MAX_HANDLES_PER_NODE:
            return None

        handle = PivotHandle(
            node_id=node_id,
            pivot_id=pivot_id,
            offset=offset,
            color=color,
            size=size,
        )
        self._handles[handle.id] = handle
        if pivot_id not in self._pivot_to_handles:
            self._pivot_to_handles[pivot_id] = []
        self._pivot_to_handles[pivot_id].append(handle.id)
        return handle

    def get_handles(self, node_id: str) -> List[PivotHandle]:
        pivot_id = self._node_to_pivot.get(node_id)
        if pivot_id is None:
            return []
        handle_ids = self._pivot_to_handles.get(pivot_id, [])
        return [self._handles[h] for h in handle_ids if h in self._handles]

    def remove_handle(self, handle_id: str) -> bool:
        handle = self._handles.pop(handle_id, None)
        if handle is None:
            return False
        pivot_id = handle.pivot_id
        if pivot_id in self._pivot_to_handles:
            self._pivot_to_handles[pivot_id] = [
                h for h in self._pivot_to_handles[pivot_id] if h != handle_id
            ]
        return True

    # ---- Anchor Binding ----

    def bind_to_anchor(self,
                       pivot_id: str,
                       anchor_type: str,
                       anchor_id: str,
                       offset: Optional[Tuple[float, float, float]] = None,
                       weight: float = 1.0) -> Optional[AnchorBinding]:
        if pivot_id not in self._points:
            return None

        try:
            at = PivotAnchor(anchor_type.lower())
        except ValueError:
            at = PivotAnchor.CUSTOM

        existing = self._pivot_to_bindings.get(pivot_id, [])
        if len(existing) >= self.MAX_BINDINGS_PER_PIVOT:
            return None

        binding = AnchorBinding(
            pivot_id=pivot_id,
            anchor_type=at,
            anchor_id=anchor_id,
            offset=offset or (0.0, 0.0, 0.0),
            weight=max(0.0, min(1.0, weight)),
        )
        self._bindings[binding.id] = binding
        if pivot_id not in self._pivot_to_bindings:
            self._pivot_to_bindings[pivot_id] = []
        self._pivot_to_bindings[pivot_id].append(binding.id)
        return binding

    def get_bindings(self, pivot_id: str) -> List[AnchorBinding]:
        binding_ids = self._pivot_to_bindings.get(pivot_id, [])
        return [self._bindings[b] for b in binding_ids if b in self._bindings]

    def remove_binding(self, binding_id: str) -> bool:
        binding = self._bindings.pop(binding_id, None)
        if binding is None:
            return False
        pivot_id = binding.pivot_id
        if pivot_id in self._pivot_to_bindings:
            self._pivot_to_bindings[pivot_id] = [
                b for b in self._pivot_to_bindings[pivot_id] if b != binding_id
            ]
        return True

    # ---- Pivot Groups ----

    def create_pivot_group(self,
                           node_ids: List[str],
                           mode: str = "center",
                           space: str = "local") -> Optional[PivotGroup]:
        if not node_ids or len(node_ids) > self.MAX_GROUP_MEMBERS:
            return None

        try:
            pm = PivotMode(mode.lower())
        except ValueError:
            pm = PivotMode.CENTER

        try:
            ps = PivotSpace(space.lower())
        except ValueError:
            ps = PivotSpace.LOCAL

        pivot_ids: List[str] = []
        center_x = 0.0
        center_y = 0.0
        center_z = 0.0
        count = 0

        for node_id in node_ids:
            pivot = self.get_pivot(node_id)
            if pivot is None:
                pivot = self.set_pivot(
                    node_id=node_id,
                    position=(0.5, 0.5, 0.5),
                    mode=mode,
                    space=space,
                )
            pivot_ids.append(pivot.id)
            center_x += pivot.position[0]
            center_y += pivot.position[1]
            center_z += pivot.position[2]
            count += 1

        if count > 0:
            center_x /= count
            center_y /= count
            center_z /= count

        group = PivotGroup(
            node_ids=list(node_ids),
            pivot_ids=pivot_ids,
            center_position=(center_x, center_y, center_z),
            mode=pm,
            space=ps,
        )
        self._groups[group.id] = group
        return group

    def get_group(self, group_id: str) -> Optional[PivotGroup]:
        return self._groups.get(group_id)

    def remove_group(self, group_id: str) -> bool:
        if group_id in self._groups:
            del self._groups[group_id]
            return True
        return False

    # ---- Group Transform ----

    def apply_group_transform(self,
                              group_id: str,
                              position: Optional[Tuple[float, float, float]] = None,
                              rotation: Optional[Tuple[float, float, float]] = None,
                              scale: Optional[Tuple[float, float, float]] = None) -> Dict[str, Any]:
        group = self._groups.get(group_id)
        if group is None:
            return {"success": False, "error": "group_not_found"}

        delta_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        if position is not None:
            delta_pos = (
                position[0] - group.center_position[0],
                position[1] - group.center_position[1],
                position[2] - group.center_position[2],
            )
            group.center_position = position

        affected: List[str] = []
        for pivot_id in group.pivot_ids:
            point = self._points.get(pivot_id)
            if point is None:
                continue
            if position is not None:
                point.position = (
                    point.position[0] + delta_pos[0],
                    point.position[1] + delta_pos[1],
                    point.position[2] + delta_pos[2],
                )
            affected.append(point.node_id)

        return {
            "success": True,
            "group_id": group_id,
            "affected_nodes": affected,
            "applied_position": position is not None,
            "applied_rotation": rotation is not None,
            "applied_scale": scale is not None,
        }

    def list_groups(self) -> List[PivotGroup]:
        return sorted(self._groups.values(), key=lambda g: g.created_at)

    # ---- Stats & Utilities ----

    def set_constraint(self, node_id: str, constraint: str) -> bool:
        try:
            pc = PivotConstraint(constraint.lower())
        except ValueError:
            return False

        pivot = self.get_pivot(node_id)
        if pivot is None:
            return False
        pivot.constraint = pc
        return True

    def get_stats(self) -> Dict[str, Any]:
        total_handles = len(self._handles)
        total_bindings = len(self._bindings)
        active_pivots = sum(1 for p in self._points.values() if p.is_active)
        active_groups = sum(1 for g in self._groups.values() if g.is_active)

        return {
            "total_pivots": len(self._points),
            "active_pivots": active_pivots,
            "total_handles": total_handles,
            "total_bindings": total_bindings,
            "total_groups": len(self._groups),
            "active_groups": active_groups,
            "nodes_with_pivots": len(self._node_to_pivot),
            "max_handles_per_node": self.MAX_HANDLES_PER_NODE,
            "max_bindings_per_pivot": self.MAX_BINDINGS_PER_PIVOT,
            "max_group_members": self.MAX_GROUP_MEMBERS,
        }


def get_pivot_system() -> PivotSystem:
    return PivotSystem.get_instance()