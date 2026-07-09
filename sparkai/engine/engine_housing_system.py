"""
SparkLabs Engine - Housing System

A player housing and base building system for the SparkLabs AI-native game
engine. Manages player-owned plots, furniture placement, room customization,
visitor permissions, and housing templates. Supports grid-based and free-form
placement, furniture categories, storage capacity, lighting, and social
features (inviting visitors, sharing templates).

Each plot is a rectangular region in world space that a player owns. Furniture
items are placed within plots at specific positions, rotations, and scales.
The system tracks placement validity (grid occupancy, collision, boundary),
furniture categories (decor, furniture, lighting, storage, interactive),
and visitor access permissions.

Architecture:
  HousingSystem (singleton)
    |-- HousingState, FurnitureCategory, PlotPermission, HousingEventKind
    |-- FurnitureItem, FurniturePlacement, HousingPlot, VisitorPass,
       HousingTemplate, HousingConfig, HousingStats, HousingSnapshot,
       HousingEvent
    |-- get_housing_system

Core Capabilities:
  - register_plot / remove_plot / get_plot / list_plots: manage player-owned
    housing plots.
  - register_furniture / remove_furniture / get_furniture / list_furniture:
    manage the furniture catalog.
  - place_furniture / remove_placement / move_placement / rotate_placement:
    position furniture within plots with collision and boundary checks.
  - set_permission / get_permission: control visitor access to plots.
  - invite_visitor / revoke_visitor / list_visitors: manage visitor passes.
  - save_template / load_template / list_templates: persist and restore plot
    layouts as reusable templates.
  - tick: advance regen, capacity, and time-based features.
  - set_config / get_config: global tuning for max plots, furniture, etc.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`HousingSystem.get_instance` or the module-level
:func:`get_housing_system` factory.
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
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PLOTS: int = 500
_MAX_FURNITURE_CATALOG: int = 2000
_MAX_PLACEMENTS_PER_PLOT: int = 500
_MAX_VISITORS_PER_PLOT: int = 50
_MAX_TEMPLATES: int = 200
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FurnitureCategory(str, Enum):
    """Category of furniture item."""
    DECOR = "decor"
    FURNITURE = "furniture"
    LIGHTING = "lighting"
    STORAGE = "storage"
    INTERACTIVE = "interactive"
    EXTERIOR = "exterior"
    APPLIANCE = "appliance"


class PlotPermission(str, Enum):
    """Visitor access level for a plot."""
    PRIVATE = "private"
    FRIENDS = "friends"
    GUILD = "guild"
    PUBLIC = "public"


class HousingEventKind(str, Enum):
    """Audit event types emitted by the housing system."""
    PLOT_REGISTERED = "plot_registered"
    PLOT_REMOVED = "plot_removed"
    FURNITURE_REGISTERED = "furniture_registered"
    FURNITURE_REMOVED = "furniture_removed"
    FURNITURE_PLACED = "furniture_placed"
    FURNITURE_REMOVED_FROM_PLOT = "furniture_removed_from_plot"
    FURNITURE_MOVED = "furniture_moved"
    FURNITURE_ROTATED = "furniture_rotated"
    PERMISSION_CHANGED = "permission_changed"
    VISITOR_INVITED = "visitor_invited"
    VISITOR_REVOKED = "visitor_revoked"
    TEMPLATE_SAVED = "template_saved"
    TEMPLATE_LOADED = "template_loaded"
    TEMPLATE_REMOVED = "template_removed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FurnitureItem:
    """A furniture catalog entry."""
    furniture_id: str
    name: str = ""
    category: str = FurnitureCategory.DECOR.value
    description: str = ""
    width: float = 1.0
    depth: float = 1.0
    height: float = 1.0
    footprint_cells: int = 1
    storage_capacity: int = 0
    is_interactive: bool = False
    light_source: bool = False
    light_intensity: float = 0.0
    light_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    rarity: str = "common"
    value: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FurniturePlacement:
    """A furniture item placed within a plot."""
    placement_id: str
    furniture_id: str
    plot_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_y: float = 0.0
    scale: float = 1.0
    grid_cell: Tuple[int, int] = (0, 0)
    placed_at: float = field(default_factory=_now)
    placed_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VisitorPass:
    """A visitor access pass for a plot."""
    pass_id: str
    plot_id: str
    visitor_id: str
    visitor_name: str = ""
    expires_at: float = 0.0
    granted_at: float = field(default_factory=_now)
    granted_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingPlot:
    """A player-owned housing plot."""
    plot_id: str
    owner_id: str
    name: str = ""
    plot_type: str = "standard"
    world_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    width: float = 20.0
    depth: float = 20.0
    grid_width: int = 20
    grid_depth: int = 20
    permission: str = PlotPermission.PRIVATE.value
    max_furniture: int = 200
    placements: List[FurniturePlacement] = field(default_factory=list)
    visitors: List[VisitorPass] = field(default_factory=list)
    temperature: float = 20.0
    ambient_light: float = 0.5
    wallpaper: str = ""
    flooring: str = ""
    exterior_paint: str = ""
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingTemplate:
    """A saved plot layout template."""
    template_id: str
    name: str = ""
    description: str = ""
    plot_type: str = "standard"
    placements: List[Dict[str, Any]] = field(default_factory=list)
    wallpaper: str = ""
    flooring: str = ""
    exterior_paint: str = ""
    created_by: str = ""
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingConfig:
    """Global tuning parameters for the housing system."""
    max_plots: int = 500
    max_furniture_catalog: int = 2000
    max_placements_per_plot: int = 500
    max_visitors_per_plot: int = 50
    max_templates: int = 200
    grid_cell_size: float = 1.0
    allow_overlap: bool = False
    allow_exterior_placement: bool = True
    visitor_timeout_seconds: float = 3600.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingStats:
    """Aggregate statistics for the housing system."""
    total_plots: int = 0
    total_furniture_catalog: int = 0
    total_placements: int = 0
    total_visitors: int = 0
    total_templates: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingSnapshot:
    """Full state snapshot of the housing system."""
    plots: List[Dict[str, Any]] = field(default_factory=list)
    furniture_catalog: List[Dict[str, Any]] = field(default_factory=list)
    templates: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingEvent:
    """An audit event emitted by the housing system."""
    event_id: str
    kind: str
    timestamp: float
    plot_id: Optional[str] = None
    furniture_id: Optional[str] = None
    placement_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Housing System
# ---------------------------------------------------------------------------

class HousingSystem:
    """Manages player housing plots, furniture placement, and visitor access."""

    _instance: Optional["HousingSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._plots: Dict[str, HousingPlot] = {}
        self._furniture_catalog: Dict[str, FurnitureItem] = {}
        self._templates: Dict[str, HousingTemplate] = {}
        self._events: List[HousingEvent] = []
        self._stats = HousingStats()
        self._config = HousingConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._placement_counter: int = 0
        self._visitor_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "HousingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample furniture, plot, and template data."""
        with self._init_lock:
            if self._initialized:
                return

            furniture_items = [
                FurnitureItem(
                    furniture_id="furn_wooden_chair",
                    name="Wooden Chair",
                    category=FurnitureCategory.FURNITURE.value,
                    description="A simple wooden chair.",
                    width=0.6, depth=0.6, height=1.0,
                    footprint_cells=1, rarity="common", value=50,
                ),
                FurnitureItem(
                    furniture_id="furn_oak_table",
                    name="Oak Table",
                    category=FurnitureCategory.FURNITURE.value,
                    description="A sturdy oak table.",
                    width=1.5, depth=0.8, height=0.75,
                    footprint_cells=2, rarity="common", value=100,
                ),
                FurnitureItem(
                    furniture_id="furn_lantern_lg",
                    name="Large Lantern",
                    category=FurnitureCategory.LIGHTING.value,
                    description="A warm-glowing lantern.",
                    width=0.4, depth=0.4, height=0.8,
                    footprint_cells=1, light_source=True,
                    light_intensity=0.7, light_color=(1.0, 0.8, 0.4),
                    rarity="uncommon", value=80,
                ),
                FurnitureItem(
                    furniture_id="furn_storage_chest",
                    name="Storage Chest",
                    category=FurnitureCategory.STORAGE.value,
                    description="A chest for storing items.",
                    width=1.0, depth=0.5, height=0.6,
                    footprint_cells=1, storage_capacity=30,
                    is_interactive=True, rarity="common", value=120,
                ),
                FurnitureItem(
                    furniture_id="furn_painting",
                    name="Landscape Painting",
                    category=FurnitureCategory.DECOR.value,
                    description="A beautiful landscape painting.",
                    width=1.2, depth=0.1, height=0.8,
                    footprint_cells=1, rarity="rare", value=250,
                ),
            ]
            for item in furniture_items:
                self._furniture_catalog[item.furniture_id] = item

            plot = HousingPlot(
                plot_id="plot_starter_01",
                owner_id="player_starter",
                name="Starter Cottage",
                plot_type="cottage",
                world_position=(100.0, 0.0, 200.0),
                width=20.0, depth=20.0,
                grid_width=20, grid_depth=20,
                permission=PlotPermission.FRIENDS.value,
                max_furniture=200,
                wallpaper="wp_default",
                flooring="fl_wood",
            )
            placement = FurniturePlacement(
                placement_id="place_0",
                furniture_id="furn_oak_table",
                plot_id="plot_starter_01",
                position=(5.0, 0.0, 5.0),
                rotation_y=0.0,
                grid_cell=(5, 5),
                placed_by="player_starter",
            )
            plot.placements.append(placement)
            self._plots[plot.plot_id] = plot

            template = HousingTemplate(
                template_id="tpl_cozy_room",
                name="Cozy Room Layout",
                description="A warm, inviting room with table and lantern.",
                plot_type="cottage",
                placements=[
                    {"furniture_id": "furn_oak_table", "position": [5.0, 0.0, 5.0], "rotation_y": 0.0, "grid_cell": [5, 5]},
                    {"furniture_id": "furn_lantern_lg", "position": [6.0, 1.5, 5.0], "rotation_y": 0.0, "grid_cell": [6, 5]},
                    {"furniture_id": "furn_wooden_chair", "position": [4.0, 0.0, 5.0], "rotation_y": 90.0, "grid_cell": [4, 5]},
                ],
                wallpaper="wp_default",
                flooring="fl_wood",
                created_by="system",
            )
            self._templates[template.template_id] = template

            self._stats.total_plots = 1
            self._stats.total_furniture_catalog = len(furniture_items)
            self._stats.total_placements = 1
            self._stats.total_templates = 1
            self._initialized = True

    # ------------------------------------------------------------------
    # Plot Management
    # ------------------------------------------------------------------

    def register_plot(self, plot: HousingPlot) -> Dict[str, Any]:
        if not plot.plot_id:
            return {"success": False, "reason": "missing_plot_id"}
        with self._lock:
            if plot.plot_id in self._plots:
                return {"success": False, "reason": "plot_id_exists"}
            if len(self._plots) >= self._config.max_plots:
                return {"success": False, "reason": "max_plots_reached"}
            self._plots[plot.plot_id] = plot
            self._stats.total_plots = len(self._plots)
            self._emit_event(HousingEventKind.PLOT_REGISTERED.value, plot_id=plot.plot_id,
                             details={"owner_id": plot.owner_id, "name": plot.name})
            return {"plot_id": plot.plot_id, "registered": True}

    def remove_plot(self, plot_id: str) -> Dict[str, Any]:
        with self._lock:
            if plot_id not in self._plots:
                return {"removed": False, "reason": "plot_not_found"}
            del self._plots[plot_id]
            self._stats.total_plots = len(self._plots)
            self._stats.total_placements = sum(len(p.placements) for p in self._plots.values())
            self._emit_event(HousingEventKind.PLOT_REMOVED.value, plot_id=plot_id)
            return {"plot_id": plot_id, "removed": True}

    def get_plot(self, plot_id: str) -> Optional[HousingPlot]:
        return self._plots.get(plot_id)

    def list_plots(self, owner_id: Optional[str] = None, plot_type: Optional[str] = None,
                   limit: int = 100) -> List[HousingPlot]:
        plots = list(self._plots.values())
        if owner_id:
            plots = [p for p in plots if p.owner_id == owner_id]
        if plot_type:
            plots = [p for p in plots if p.plot_type == plot_type]
        return plots[:limit]

    # ------------------------------------------------------------------
    # Furniture Catalog
    # ------------------------------------------------------------------

    def register_furniture(self, item: FurnitureItem) -> Dict[str, Any]:
        if not item.furniture_id:
            return {"success": False, "reason": "missing_furniture_id"}
        with self._lock:
            if item.furniture_id in self._furniture_catalog:
                return {"success": False, "reason": "furniture_id_exists"}
            if len(self._furniture_catalog) >= self._config.max_furniture_catalog:
                return {"success": False, "reason": "max_furniture_reached"}
            self._furniture_catalog[item.furniture_id] = item
            self._stats.total_furniture_catalog = len(self._furniture_catalog)
            self._emit_event(HousingEventKind.FURNITURE_REGISTERED.value,
                             furniture_id=item.furniture_id,
                             details={"name": item.name, "category": item.category})
            return {"furniture_id": item.furniture_id, "registered": True}

    def remove_furniture(self, furniture_id: str) -> Dict[str, Any]:
        with self._lock:
            if furniture_id not in self._furniture_catalog:
                return {"removed": False, "reason": "furniture_not_found"}
            del self._furniture_catalog[furniture_id]
            self._stats.total_furniture_catalog = len(self._furniture_catalog)
            self._emit_event(HousingEventKind.FURNITURE_REMOVED.value, furniture_id=furniture_id)
            return {"furniture_id": furniture_id, "removed": True}

    def get_furniture(self, furniture_id: str) -> Optional[FurnitureItem]:
        return self._furniture_catalog.get(furniture_id)

    def list_furniture(self, category: Optional[str] = None, limit: int = 100) -> List[FurnitureItem]:
        items = list(self._furniture_catalog.values())
        if category:
            items = [i for i in items if i.category == category]
        return items[:limit]

    # ------------------------------------------------------------------
    # Furniture Placement
    # ------------------------------------------------------------------

    def place_furniture(self, plot_id: str, furniture_id: str,
                        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                        rotation_y: float = 0.0, scale: float = 1.0,
                        grid_cell: Tuple[int, int] = (0, 0),
                        placed_by: str = "") -> Dict[str, Any]:
        with self._lock:
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            furniture = self._furniture_catalog.get(furniture_id)
            if furniture is None:
                return {"success": False, "reason": "furniture_not_found"}
            if len(plot.placements) >= plot.max_furniture:
                return {"success": False, "reason": "plot_full"}
            if not self._config.allow_overlap:
                for p in plot.placements:
                    if p.grid_cell == grid_cell:
                        return {"success": False, "reason": "cell_occupied"}
            if not self._is_within_bounds(plot, position):
                return {"success": False, "reason": "out_of_bounds"}
            self._placement_counter += 1
            placement = FurniturePlacement(
                placement_id=f"place_{self._placement_counter}",
                furniture_id=furniture_id,
                plot_id=plot_id,
                position=position,
                rotation_y=rotation_y,
                scale=scale,
                grid_cell=grid_cell,
                placed_by=placed_by,
            )
            plot.placements.append(placement)
            plot.updated_at = _now()
            self._stats.total_placements = sum(len(p.placements) for p in self._plots.values())
            self._emit_event(HousingEventKind.FURNITURE_PLACED.value, plot_id=plot_id,
                             placement_id=placement.placement_id,
                             details={"furniture_id": furniture_id, "position": list(position)})
            return {"placement_id": placement.placement_id, "plot_id": plot_id, "success": True}

    def remove_placement(self, plot_id: str, placement_id: str) -> Dict[str, Any]:
        with self._lock:
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            for i, p in enumerate(plot.placements):
                if p.placement_id == placement_id:
                    plot.placements.pop(i)
                    plot.updated_at = _now()
                    self._stats.total_placements = sum(len(pl.placements) for pl in self._plots.values())
                    self._emit_event(HousingEventKind.FURNITURE_REMOVED_FROM_PLOT.value,
                                     plot_id=plot_id, placement_id=placement_id)
                    return {"placement_id": placement_id, "success": True}
            return {"success": False, "reason": "placement_not_found"}

    def move_placement(self, plot_id: str, placement_id: str,
                       position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                       grid_cell: Tuple[int, int] = (0, 0)) -> Dict[str, Any]:
        with self._lock:
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            for p in plot.placements:
                if p.placement_id == placement_id:
                    if not self._is_within_bounds(plot, position):
                        return {"success": False, "reason": "out_of_bounds"}
                    if not self._config.allow_overlap:
                        for other in plot.placements:
                            if other.placement_id != placement_id and other.grid_cell == grid_cell:
                                return {"success": False, "reason": "cell_occupied"}
                    p.position = position
                    p.grid_cell = grid_cell
                    plot.updated_at = _now()
                    self._emit_event(HousingEventKind.FURNITURE_MOVED.value,
                                     plot_id=plot_id, placement_id=placement_id,
                                     details={"position": list(position)})
                    return {"placement_id": placement_id, "success": True}
            return {"success": False, "reason": "placement_not_found"}

    def rotate_placement(self, plot_id: str, placement_id: str, rotation_y: float) -> Dict[str, Any]:
        with self._lock:
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            for p in plot.placements:
                if p.placement_id == placement_id:
                    p.rotation_y = rotation_y
                    plot.updated_at = _now()
                    self._emit_event(HousingEventKind.FURNITURE_ROTATED.value,
                                     plot_id=plot_id, placement_id=placement_id,
                                     details={"rotation_y": rotation_y})
                    return {"placement_id": placement_id, "success": True}
            return {"success": False, "reason": "placement_not_found"}

    def _is_within_bounds(self, plot: HousingPlot, position: Tuple[float, float, float]) -> bool:
        x, _, z = position
        half_w = plot.width / 2.0
        half_d = plot.depth / 2.0
        cx, _, cz = plot.world_position
        return (cx - half_w <= x <= cx + half_w) and (cz - half_d <= z <= cz + half_d)

    # ------------------------------------------------------------------
    # Visitor Management
    # ------------------------------------------------------------------

    def set_permission(self, plot_id: str, permission: str) -> Dict[str, Any]:
        with self._lock:
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            plot.permission = permission
            plot.updated_at = _now()
            self._emit_event(HousingEventKind.PERMISSION_CHANGED.value, plot_id=plot_id,
                             details={"permission": permission})
            return {"plot_id": plot_id, "permission": permission, "success": True}

    def get_permission(self, plot_id: str) -> Dict[str, Any]:
        plot = self._plots.get(plot_id)
        if plot is None:
            return {"found": False, "reason": "plot_not_found"}
        return {"found": True, "plot_id": plot_id, "permission": plot.permission}

    def invite_visitor(self, plot_id: str, visitor_id: str, visitor_name: str = "",
                       granted_by: str = "", duration: float = 3600.0) -> Dict[str, Any]:
        with self._lock:
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            if len(plot.visitors) >= self._config.max_visitors_per_plot:
                return {"success": False, "reason": "max_visitors_reached"}
            for v in plot.visitors:
                if v.visitor_id == visitor_id:
                    return {"success": False, "reason": "already_invited"}
            self._visitor_counter += 1
            pass_obj = VisitorPass(
                pass_id=f"pass_{self._visitor_counter}",
                plot_id=plot_id,
                visitor_id=visitor_id,
                visitor_name=visitor_name,
                expires_at=_now() + duration,
                granted_by=granted_by,
            )
            plot.visitors.append(pass_obj)
            plot.updated_at = _now()
            self._stats.total_visitors = sum(len(p.visitors) for p in self._plots.values())
            self._emit_event(HousingEventKind.VISITOR_INVITED.value, plot_id=plot_id,
                             details={"visitor_id": visitor_id, "pass_id": pass_obj.pass_id})
            return {"pass_id": pass_obj.pass_id, "success": True}

    def revoke_visitor(self, plot_id: str, visitor_id: str) -> Dict[str, Any]:
        with self._lock:
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            for i, v in enumerate(plot.visitors):
                if v.visitor_id == visitor_id:
                    plot.visitors.pop(i)
                    plot.updated_at = _now()
                    self._stats.total_visitors = sum(len(p.visitors) for p in self._plots.values())
                    self._emit_event(HousingEventKind.VISITOR_REVOKED.value, plot_id=plot_id,
                                     details={"visitor_id": visitor_id})
                    return {"visitor_id": visitor_id, "success": True}
            return {"success": False, "reason": "visitor_not_found"}

    def list_visitors(self, plot_id: str, limit: int = 50) -> List[VisitorPass]:
        plot = self._plots.get(plot_id)
        if plot is None:
            return []
        return plot.visitors[:limit]

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def save_template(self, template_id: str, name: str, plot_id: str,
                      description: str = "", created_by: str = "") -> Dict[str, Any]:
        with self._lock:
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            if template_id in self._templates:
                return {"success": False, "reason": "template_id_exists"}
            if len(self._templates) >= self._config.max_templates:
                return {"success": False, "reason": "max_templates_reached"}
            placements_data = [
                {
                    "furniture_id": p.furniture_id,
                    "position": list(p.position),
                    "rotation_y": p.rotation_y,
                    "grid_cell": list(p.grid_cell),
                }
                for p in plot.placements
            ]
            template = HousingTemplate(
                template_id=template_id,
                name=name,
                description=description,
                plot_type=plot.plot_type,
                placements=placements_data,
                wallpaper=plot.wallpaper,
                flooring=plot.flooring,
                exterior_paint=plot.exterior_paint,
                created_by=created_by,
            )
            self._templates[template_id] = template
            self._stats.total_templates = len(self._templates)
            self._emit_event(HousingEventKind.TEMPLATE_SAVED.value, plot_id=plot_id,
                             details={"template_id": template_id})
            return {"template_id": template_id, "saved": True}

    def load_template(self, template_id: str, plot_id: str) -> Dict[str, Any]:
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return {"success": False, "reason": "template_not_found"}
            plot = self._plots.get(plot_id)
            if plot is None:
                return {"success": False, "reason": "plot_not_found"}
            plot.placements.clear()
            for i, pd in enumerate(template.placements):
                self._placement_counter += 1
                pos = pd.get("position", [0.0, 0.0, 0.0])
                gc = pd.get("grid_cell", [0, 0])
                placement = FurniturePlacement(
                    placement_id=f"place_{self._placement_counter}",
                    furniture_id=pd.get("furniture_id", ""),
                    plot_id=plot_id,
                    position=tuple(pos) if isinstance(pos, list) else (0.0, 0.0, 0.0),
                    rotation_y=_safe_float(pd.get("rotation_y")),
                    grid_cell=tuple(gc) if isinstance(gc, list) else (0, 0),
                )
                plot.placements.append(placement)
            plot.wallpaper = template.wallpaper
            plot.flooring = template.flooring
            plot.exterior_paint = template.exterior_paint
            plot.updated_at = _now()
            self._stats.total_placements = sum(len(p.placements) for p in self._plots.values())
            self._emit_event(HousingEventKind.TEMPLATE_LOADED.value, plot_id=plot_id,
                             details={"template_id": template_id})
            return {"template_id": template_id, "plot_id": plot_id, "placements_loaded": len(template.placements), "success": True}

    def remove_template(self, template_id: str) -> Dict[str, Any]:
        with self._lock:
            if template_id not in self._templates:
                return {"removed": False, "reason": "template_not_found"}
            del self._templates[template_id]
            self._stats.total_templates = len(self._templates)
            self._emit_event(HousingEventKind.TEMPLATE_REMOVED.value,
                             details={"template_id": template_id})
            return {"template_id": template_id, "removed": True}

    def list_templates(self, plot_type: Optional[str] = None, limit: int = 100) -> List[HousingTemplate]:
        templates = list(self._templates.values())
        if plot_type:
            templates = [t for t in templates if t.plot_type == plot_type]
        return templates[:limit]

    # ------------------------------------------------------------------
    # Tick, Config, Events, Stats
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        now = _now()
        with self._lock:
            for plot in self._plots.values():
                expired = [v for v in plot.visitors if v.expires_at > 0 and v.expires_at < now]
                for v in expired:
                    plot.visitors.remove(v)
            self._stats.total_visitors = sum(len(p.visitors) for p in self._plots.values())
        self._emit_event(HousingEventKind.TICK.value, details={"delta_time": delta_time})
        return {"tick": self._tick_count, "active_visitors": self._stats.total_visitors}

    def get_config(self) -> HousingConfig:
        return self._config

    def set_config(self, config: HousingConfig) -> Dict[str, Any]:
        with self._lock:
            self._config = config
            self._emit_event(HousingEventKind.CONFIG_UPDATED.value)
            return {"updated": True}

    def _emit_event(self, kind: str, plot_id: Optional[str] = None,
                    furniture_id: Optional[str] = None,
                    placement_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        self._event_counter += 1
        event = HousingEvent(
            event_id=f"he_{self._event_counter}",
            kind=kind,
            timestamp=_now(),
            plot_id=plot_id,
            furniture_id=furniture_id,
            placement_id=placement_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, plot_id: Optional[str] = None, limit: int = 100) -> List[HousingEvent]:
        events = self._events
        if plot_id:
            events = [e for e in events if e.plot_id == plot_id]
        return list(reversed(events[-limit:]))

    def get_stats(self) -> HousingStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_plots": len(self._plots),
            "total_furniture_catalog": len(self._furniture_catalog),
            "total_placements": self._stats.total_placements,
            "total_visitors": self._stats.total_visitors,
            "total_templates": len(self._templates),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> HousingSnapshot:
        return HousingSnapshot(
            plots=[p.to_dict() for p in self._plots.values()],
            furniture_catalog=[f.to_dict() for f in self._furniture_catalog.values()],
            templates=[t.to_dict() for t in self._templates.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._plots.clear()
            self._furniture_catalog.clear()
            self._templates.clear()
            self._events.clear()
            self._stats = HousingStats()
            self._tick_count = 0
            self._event_counter = 0
            self._placement_counter = 0
            self._visitor_counter = 0
            self._initialized = False
            self._seed()
            self._emit_event(HousingEventKind.RESET.value)
            return {"reset": True, "status": self.get_status()}


def get_housing_system() -> HousingSystem:
    return HousingSystem.get_instance()
