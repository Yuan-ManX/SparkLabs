"""
SparkLabs Engine - Raycast Picking System

A screen-to-world raycasting and object picking runtime for the SparkLabs
AI-native game engine. This system is distinct from the general physics
collision system: it operates on pickable object registries with layer
filtering, screen-to-world ray generation, and multi-mode selection queries
(point ray, box, sphere, frustum). It is the precise subsystem that game
editors (GDevelop object picker, Godot raycast nodes, three.js Raycaster,
Phaser input picker) require for object selection, hover highlighting, and
editor interaction.

Architecture:
  RaycastPicker (singleton)
    |-- Pickable, RaycastHit, BoxPickResult, SpherePickResult,
       FrustumPickResult, PickerStats, PickerSnapshot, PickerEvent
    |-- PickMode, PickerEventKind, CameraMode

Core Capabilities:
  - register_pickable / get_pickable / list_pickables / remove_pickable:
    lifecycle for pickable objects with AABB bounds and layer membership.
  - set_camera / get_camera: configure the screen-to-world camera matrix
    for converting mouse coordinates into world-space rays.
  - screen_to_ray: convert a screen-space (x, y) point into a world-space
    ray (origin, direction).
  - raycast: cast a ray and return sorted hit results with distance, point,
    and normal, filtered by layer mask.
  - box_pick / sphere_pick / frustum_pick: area-based selection queries
    returning all pickables within the specified volume.
  - hover / select / deselect: interaction state management for editor
    highlighting and multi-select workflows.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`RaycastPicker.get_instance` or the module-level
:func:`get_raycast_picker` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PICKABLES: int = 10000
_MAX_HITS: int = 500
_MAX_EVENTS: int = 5000
_MAX_SELECTED: int = 200


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _vec_length(v: Tuple[float, float, float]) -> float:
    return (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) ** 0.5


def _vec_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length = _vec_length(v)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _vec_dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_sub(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_add(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_scale(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# AABB Ray Intersection
# ---------------------------------------------------------------------------


def _ray_aabb_intersect(
    ray_origin: Tuple[float, float, float],
    ray_dir: Tuple[float, float, float],
    box_min: Tuple[float, float, float],
    box_max: Tuple[float, float, float],
    max_dist: float,
) -> Optional[float]:
    """Return the intersection distance if the ray hits the AABB, else None."""
    tmin = 0.0
    tmax = max_dist
    for i in range(3):
        o = ray_origin[i]
        d = ray_dir[i]
        mn = box_min[i]
        mx = box_max[i]
        if abs(d) < 1e-9:
            if o < mn or o > mx:
                return None
        else:
            t1 = (mn - o) / d
            t2 = (mx - o) / d
            if t1 > t2:
                t1, t2 = t2, t1
            tmin = max(tmin, t1)
            tmax = min(tmax, t2)
            if tmin > tmax:
                return None
    if tmin < 0.0:
        if tmax < 0.0:
            return None
        return tmax
    return tmin


def _point_in_box(
    p: Tuple[float, float, float],
    box_min: Tuple[float, float, float],
    box_max: Tuple[float, float, float],
) -> bool:
    return (
        box_min[0] <= p[0] <= box_max[0]
        and box_min[1] <= p[1] <= box_max[1]
        and box_min[2] <= p[2] <= box_max[2]
    )


def _point_in_sphere(
    p: Tuple[float, float, float],
    center: Tuple[float, float, float],
    radius: float,
) -> bool:
    diff = _vec_sub(p, center)
    return _vec_dot(diff, diff) <= radius * radius


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class PickMode(Enum):
    """Selection mode for picking queries."""
    POINT = "point"
    BOX = "box"
    SPHERE = "sphere"
    FRUSTUM = "frustum"


class CameraMode(Enum):
    """Camera projection mode for screen-to-world conversion."""
    PERSPECTIVE = "perspective"
    ORTHOGRAPHIC = "orthographic"


class PickerEventKind(Enum):
    """Audit event types emitted by the raycast picker."""
    PICKABLE_REGISTERED = "pickable_registered"
    PICKABLE_REMOVED = "pickable_removed"
    RAYCAST_PERFORMED = "raycast_performed"
    BOX_PICK_PERFORMED = "box_pick_performed"
    SPHERE_PICK_PERFORMED = "sphere_pick_performed"
    FRUSTUM_PICK_PERFORMED = "frustum_pick_performed"
    HOVER_CHANGED = "hover_changed"
    SELECTION_CHANGED = "selection_changed"
    CAMERA_UPDATED = "camera_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Pickable:
    """A pickable object with AABB bounds and layer membership."""
    pickable_id: str = ""
    name: str = ""
    layer: str = "default"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    box_min: Tuple[float, float, float] = (-0.5, -0.5, -0.5)
    box_max: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    selectable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RaycastHit:
    """A single raycast hit result."""
    pickable_id: str = ""
    distance: float = 0.0
    point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    layer: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AreaPickResult:
    """Result of an area-based pick (box, sphere, frustum)."""
    pickable_ids: List[str] = field(default_factory=list)
    count: int = 0
    mode: str = PickMode.BOX.value

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CameraState:
    """Camera state for screen-to-world ray generation."""
    position: Tuple[float, float, float] = (0.0, 0.0, -10.0)
    forward: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    up: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    right: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    fov: float = 60.0
    aspect: float = 1.778
    near: float = 0.1
    far: float = 1000.0
    mode: str = CameraMode.PERSPECTIVE.value
    ortho_size: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PickerStats:
    """Aggregate statistics for the raycast picker."""
    total_pickables: int = 0
    total_raycasts: int = 0
    total_box_picks: int = 0
    total_sphere_picks: int = 0
    total_frustum_picks: int = 0
    total_hits: int = 0
    total_misses: int = 0
    current_hovered: int = 0
    current_selected: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PickerSnapshot:
    """Full state snapshot of the raycast picker."""
    pickables: List[Pickable] = field(default_factory=list)
    camera: CameraState = field(default_factory=CameraState)
    hovered_id: str = ""
    selected_ids: List[str] = field(default_factory=list)
    stats: PickerStats = field(default_factory=PickerStats)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PickerEvent:
    """An audit event emitted by the raycast picker."""
    timestamp: str = ""
    kind: str = ""
    pickable_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class RaycastPicker:
    """Screen-to-world raycasting and object picking system.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["RaycastPicker"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._pickables: Dict[str, Pickable] = {}
        self._camera: CameraState = CameraState()
        self._hovered_id: str = ""
        self._selected_ids: List[str] = []
        self._events: List[PickerEvent] = []
        self._stats = PickerStats()
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "RaycastPicker":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed the picker with sample pickable objects."""
        seeds = [
            Pickable(
                pickable_id="pck_cube_red",
                name="Red Cube",
                layer="geometry",
                position=(0.0, 0.0, 5.0),
                box_min=(-0.5, -0.5, 4.5),
                box_max=(0.5, 0.5, 5.5),
            ),
            Pickable(
                pickable_id="pck_sphere_blue",
                name="Blue Sphere",
                layer="geometry",
                position=(3.0, 0.0, 8.0),
                box_min=(2.5, -0.5, 7.5),
                box_max=(3.5, 0.5, 8.5),
            ),
            Pickable(
                pickable_id="pck_npc_merchant",
                name="Merchant NPC",
                layer="npc",
                position=(-2.0, 0.0, 6.0),
                box_min=(-2.5, -1.0, 5.5),
                box_max=(-1.5, 1.0, 6.5),
            ),
            Pickable(
                pickable_id="pck_trigger_zone",
                name="Trigger Zone",
                layer="trigger",
                position=(0.0, 0.0, 10.0),
                box_min=(-3.0, -0.5, 9.0),
                box_max=(3.0, 0.5, 11.0),
            ),
            Pickable(
                pickable_id="pck_light_fixture",
                name="Light Fixture",
                layer="lighting",
                position=(0.0, 4.0, 5.0),
                box_min=(-0.3, 3.7, 4.7),
                box_max=(0.3, 4.3, 5.3),
            ),
        ]
        for p in seeds:
            self._pickables[p.pickable_id] = p
        self._stats.total_pickables = len(self._pickables)
        self._initialized = True

    # ------------------------------------------------------------------
    # Pickable Lifecycle
    # ------------------------------------------------------------------

    def register_pickable(self, pickable: Pickable) -> Pickable:
        with self._init_lock:
            if not pickable.pickable_id:
                pickable.pickable_id = _new_id("pck")
            self._pickables[pickable.pickable_id] = pickable
            _evict_fifo_dict(self._pickables, _MAX_PICKABLES)
            self._stats.total_pickables = len(self._pickables)
            self._emit(
                PickerEventKind.PICKABLE_REGISTERED.value,
                pickable.pickable_id,
                {"name": pickable.name, "layer": pickable.layer},
            )
            return pickable

    def get_pickable(self, pickable_id: str) -> Optional[Pickable]:
        return self._pickables.get(pickable_id)

    def list_pickables(
        self,
        layer: str = "",
        selectable_only: bool = False,
        limit: int = 100,
    ) -> List[Pickable]:
        result: List[Pickable] = []
        for p in self._pickables.values():
            if layer and p.layer != layer:
                continue
            if selectable_only and not p.selectable:
                continue
            result.append(p)
            if len(result) >= limit:
                break
        return result

    def remove_pickable(self, pickable_id: str) -> bool:
        with self._init_lock:
            existed = self._pickables.pop(pickable_id, None) is not None
            if existed:
                self._stats.total_pickables = len(self._pickables)
                if self._hovered_id == pickable_id:
                    self._hovered_id = ""
                    self._stats.current_hovered = 0
                if pickable_id in self._selected_ids:
                    self._selected_ids.remove(pickable_id)
                    self._stats.current_selected = len(self._selected_ids)
                self._emit(
                    PickerEventKind.PICKABLE_REMOVED.value,
                    pickable_id,
                    {},
                )
            return existed

    # ------------------------------------------------------------------
    # Camera Management
    # ------------------------------------------------------------------

    def set_camera(self, camera: CameraState) -> CameraState:
        with self._init_lock:
            self._camera = camera
            self._emit(
                PickerEventKind.CAMERA_UPDATED.value,
                "",
                {"mode": camera.mode, "position": list(camera.position)},
            )
            return self._camera

    def get_camera(self) -> CameraState:
        return self._camera

    # ------------------------------------------------------------------
    # Screen-to-World Ray Generation
    # ------------------------------------------------------------------

    def screen_to_ray(
        self,
        screen_x: float,
        screen_y: float,
    ) -> Dict[str, Any]:
        """Convert screen-space coordinates (NDC -1..1) to a world-space ray."""
        cam = self._camera
        if cam.mode == CameraMode.PERSPECTIVE.value:
            tan_half_fov = (
                2.0 * 3.14159265358979 * (cam.fov / 2.0) / 360.0
            )
            tan_half_fov = (
                cam.near * (screen_x * tan_half_fov),
                cam.near * (screen_y * tan_half_fov),
                cam.near,
            )
            # Compute ray direction in camera space then transform to world
            dir_cam = _vec_normalize(tan_half_fov)
            # Transform to world space using camera basis vectors
            direction = _vec_normalize(
                (
                    _vec_dot(dir_cam, cam.right),
                    _vec_dot(dir_cam, cam.up),
                    _vec_dot(dir_cam, cam.forward),
                )
            )
            origin = cam.position
        else:
            # Orthographic: ray origin shifts by screen coords, direction is forward
            origin = _vec_add(
                cam.position,
                _vec_add(
                    _vec_scale(cam.right, screen_x * cam.ortho_size),
                    _vec_scale(cam.up, screen_y * cam.ortho_size),
                ),
            )
            direction = _vec_normalize(cam.forward)

        return {
            "origin": list(origin),
            "direction": list(direction),
        }

    # ------------------------------------------------------------------
    # Raycast Query
    # ------------------------------------------------------------------

    def raycast(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float = 1000.0,
        layer_mask: str = "",
    ) -> Dict[str, Any]:
        """Cast a ray and return sorted hit results."""
        dir_norm = _vec_normalize(direction)
        hits: List[RaycastHit] = []
        for p in self._pickables.values():
            if not p.selectable:
                continue
            if layer_mask and p.layer != layer_mask:
                continue
            dist = _ray_aabb_intersect(
                origin, dir_norm, p.box_min, p.box_max, max_distance
            )
            if dist is not None:
                hit_point = _vec_add(origin, _vec_scale(dir_norm, dist))
                # Approximate normal: face closest to the ray direction
                center = _vec_scale(_vec_add(p.box_min, p.box_max), 0.5)
                to_center = _vec_sub(center, origin)
                normal = _vec_normalize(
                    (
                        1.0 if abs(dir_norm[0]) > 1e-9 else 0.0,
                        1.0 if abs(dir_norm[1]) > 1e-9 else 0.0,
                        1.0 if abs(dir_norm[2]) > 1e-9 else 0.0,
                    )
                )
                if _vec_dot(normal, dir_norm) > 0:
                    normal = _vec_scale(normal, -1.0)
                hits.append(
                    RaycastHit(
                        pickable_id=p.pickable_id,
                        distance=round(dist, 4),
                        point=(round(hit_point[0], 4), round(hit_point[1], 4), round(hit_point[2], 4)),
                        normal=normal,
                        layer=p.layer,
                    )
                )
        hits.sort(key=lambda h: h.distance)
        _evict_fifo_list(hits, _MAX_HITS)
        self._stats.total_raycasts += 1
        if hits:
            self._stats.total_hits += 1
        else:
            self._stats.total_misses += 1
        self._emit(
            PickerEventKind.RAYCAST_PERFORMED.value,
            hits[0].pickable_id if hits else "",
            {"hit_count": len(hits), "max_distance": max_distance},
        )
        return {
            "hits": [h.to_dict() for h in hits],
            "count": len(hits),
            "first_hit": hits[0].to_dict() if hits else None,
        }

    # ------------------------------------------------------------------
    # Area-Based Picks
    # ------------------------------------------------------------------

    def box_pick(
        self,
        box_min: Tuple[float, float, float],
        box_max: Tuple[float, float, float],
        layer_mask: str = "",
    ) -> Dict[str, Any]:
        """Return all pickables whose AABB overlaps the query box."""
        ids: List[str] = []
        for p in self._pickables.values():
            if not p.selectable:
                continue
            if layer_mask and p.layer != layer_mask:
                continue
            # AABB overlap test
            overlap = (
                p.box_min[0] <= box_max[0]
                and p.box_max[0] >= box_min[0]
                and p.box_min[1] <= box_max[1]
                and p.box_max[1] >= box_min[1]
                and p.box_min[2] <= box_max[2]
                and p.box_max[2] >= box_min[2]
            )
            if overlap:
                ids.append(p.pickable_id)
        self._stats.total_box_picks += 1
        self._emit(
            PickerEventKind.BOX_PICK_PERFORMED.value,
            "",
            {"count": len(ids)},
        )
        return {"pickable_ids": ids, "count": len(ids), "mode": PickMode.BOX.value}

    def sphere_pick(
        self,
        center: Tuple[float, float, float],
        radius: float,
        layer_mask: str = "",
    ) -> Dict[str, Any]:
        """Return all pickables whose AABB intersects the query sphere."""
        ids: List[str] = []
        r_sq = radius * radius
        for p in self._pickables.values():
            if not p.selectable:
                continue
            if layer_mask and p.layer != layer_mask:
                continue
            # Find the closest point on the AABB to the sphere center
            cx = _clamp(center[0], p.box_min[0], p.box_max[0])
            cy = _clamp(center[1], p.box_min[1], p.box_max[1])
            cz = _clamp(center[2], p.box_min[2], p.box_max[2])
            diff = (center[0] - cx, center[1] - cy, center[2] - cz)
            if _vec_dot(diff, diff) <= r_sq:
                ids.append(p.pickable_id)
        self._stats.total_sphere_picks += 1
        self._emit(
            PickerEventKind.SPHERE_PICK_PERFORMED.value,
            "",
            {"count": len(ids)},
        )
        return {"pickable_ids": ids, "count": len(ids), "mode": PickMode.SPHERE.value}

    def frustum_pick(
        self,
        cam_position: Tuple[float, float, float],
        cam_forward: Tuple[float, float, float],
        fov: float,
        aspect: float,
        near: float,
        far: float,
        layer_mask: str = "",
    ) -> Dict[str, Any]:
        """Return all pickables within the camera frustum (approximate)."""
        ids: List[str] = []
        fwd = _vec_normalize(cam_forward)
        tan_half_fov = (
            2.0 * 3.14159265358979 * (fov / 2.0) / 360.0
        )
        for p in self._pickables.values():
            if not p.selectable:
                continue
            if layer_mask and p.layer != layer_mask:
                continue
            center = _vec_scale(_vec_add(p.box_min, p.box_max), 0.5)
            to_obj = _vec_sub(center, cam_position)
            dist = _vec_length(to_obj)
            if dist < near or dist > far:
                continue
            # Check if object is within the FOV cone
            if dist > 1e-9:
                cos_angle = _vec_dot(_vec_normalize(to_obj), fwd)
                if cos_angle < 0.0:
                    continue
                half_fov_cos = (
                    1.0 / (1.0 + tan_half_fov * tan_half_fov) ** 0.5
                )
                if cos_angle < half_fov_cos:
                    continue
            ids.append(p.pickable_id)
        self._stats.total_frustum_picks += 1
        self._emit(
            PickerEventKind.FRUSTUM_PICK_PERFORMED.value,
            "",
            {"count": len(ids)},
        )
        return {"pickable_ids": ids, "count": len(ids), "mode": PickMode.FRUSTRUM.value}

    # ------------------------------------------------------------------
    # Interaction State
    # ------------------------------------------------------------------

    def hover(self, pickable_id: str) -> Dict[str, Any]:
        """Set the hovered pickable."""
        with self._init_lock:
            prev = self._hovered_id
            if pickable_id and pickable_id not in self._pickables:
                return {"ok": False, "reason": "pickable not found"}
            self._hovered_id = pickable_id
            self._stats.current_hovered = 1 if pickable_id else 0
            self._emit(
                PickerEventKind.HOVER_CHANGED.value,
                pickable_id,
                {"previous": prev},
            )
            return {"ok": True, "hovered_id": pickable_id, "previous": prev}

    def select(self, pickable_id: str, additive: bool = False) -> Dict[str, Any]:
        """Select a pickable, optionally adding to the current selection."""
        with self._init_lock:
            if pickable_id not in self._pickables:
                return {"ok": False, "reason": "pickable not found"}
            if not additive:
                self._selected_ids.clear()
            if pickable_id not in self._selected_ids:
                self._selected_ids.append(pickable_id)
                _evict_fifo_list(self._selected_ids, _MAX_SELECTED)
            self._stats.current_selected = len(self._selected_ids)
            self._emit(
                PickerEventKind.SELECTION_CHANGED.value,
                pickable_id,
                {"additive": additive, "count": len(self._selected_ids)},
            )
            return {"ok": True, "selected_ids": list(self._selected_ids)}

    def deselect(self, pickable_id: str = "") -> Dict[str, Any]:
        """Deselect a specific pickable, or clear all if empty."""
        with self._init_lock:
            if pickable_id:
                if pickable_id in self._selected_ids:
                    self._selected_ids.remove(pickable_id)
            else:
                self._selected_ids.clear()
            self._stats.current_selected = len(self._selected_ids)
            self._emit(
                PickerEventKind.SELECTION_CHANGED.value,
                pickable_id,
                {"action": "deselect", "count": len(self._selected_ids)},
            )
            return {"ok": True, "selected_ids": list(self._selected_ids)}

    def get_selection(self) -> Dict[str, Any]:
        return {
            "hovered_id": self._hovered_id,
            "selected_ids": list(self._selected_ids),
            "count": len(self._selected_ids),
        }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _emit(self, kind: str, pickable_id: str, details: Dict[str, Any]) -> None:
        self._events.append(
            PickerEvent(
                timestamp=_now(),
                kind=kind,
                pickable_id=pickable_id,
                details=details,
            )
        )
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, kind: str = "", limit: int = 50) -> List[PickerEvent]:
        result: List[PickerEvent] = []
        for e in reversed(self._events):
            if kind and e.kind != kind:
                continue
            result.append(e)
            if len(result) >= limit:
                break
        return result

    def get_stats(self) -> PickerStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_pickables": len(self._pickables),
            "hovered_id": self._hovered_id,
            "selected_count": len(self._selected_ids),
            "camera_mode": self._camera.mode,
        }

    def get_snapshot(self) -> PickerSnapshot:
        return PickerSnapshot(
            pickables=list(self._pickables.values()),
            camera=self._camera,
            hovered_id=self._hovered_id,
            selected_ids=list(self._selected_ids),
            stats=self._stats,
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._pickables.clear()
            self._camera = CameraState()
            self._hovered_id = ""
            self._selected_ids.clear()
            self._events.clear()
            self._stats = PickerStats()
            self._seed()
            return {"ok": True, "message": "raycast picker reset"}


def get_raycast_picker() -> RaycastPicker:
    """Factory function to get the singleton RaycastPicker instance."""
    return RaycastPicker.get_instance()
