"""
SparkLabs Engine - Player Housing System

Manages player housing plots, house construction, furniture placement,
room customization, visitor management, neighborhood communities, and
housing rating systems. Players acquire plots, build houses, decorate
interiors with furniture, invite visitors, and participate in housing
communities with scoring and leaderboards.

Architecture:
  PlayerHousingSystem (singleton)
    |-- PlotSize, HouseStyle, FurnitureCategory, FurniturePlacement,
       VisitorStatus, PermissionLevel, HousingEventKind
    |-- FurnitureItem, HouseTemplate, HousingPlot, PlacedFurniture,
       RoomCustomization, VisitorEntry, PlayerHousing, Neighborhood,
       HousingConfig, HousingStats, HousingSnapshot, HousingEvent
    |-- get_player_housing_system

Core Capabilities:
  - register_plot_template / remove_plot_template / get_plot_template / list_plot_templates
  - register_house_template / remove_house_template / get_house_template / list_house_templates
  - register_furniture / remove_furniture / get_furniture / list_furniture
  - acquire_plot / release_plot / get_plot / list_player_plots
  - build_house / demolish_house / upgrade_house
  - place_furniture / remove_furniture_from_plot / move_furniture
  - customize_room / get_room_customization
  - invite_visitor / remove_visitor / list_visitors / set_permission
  - register_neighborhood / join_neighborhood / leave_neighborhood
  - rate_housing / get_rating / list_top_rated
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`PlayerHousingSystem.get_instance` or the module-level
:func:`get_player_housing_system` factory.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PLOT_TEMPLATES: int = 200
_MAX_HOUSE_TEMPLATES: int = 500
_MAX_FURNITURE_CATALOG: int = 5000
_MAX_PLAYER_PLOTS: int = 100000
_MAX_PLACED_FURNITURE: int = 500
_MAX_VISITORS: int = 50
_MAX_NEIGHBORHOODS: int = 1000
_MAX_RATINGS: int = 500000
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


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


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
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

class PlotSize(str, Enum):
    """Available plot sizes."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ESTATE = "estate"
    GUILD_HALL = "guild_hall"


class HouseStyle(str, Enum):
    """Architectural styles for houses."""
    COTTAGE = "cottage"
    VILLA = "villa"
    MANOR = "manor"
    TOWER = "tower"
    CASTLE = "castle"
    TREEHOUSE = "treehouse"
    UNDERWATER = "underwater"
    SKY_ISLAND = "sky_island"


class FurnitureCategory(str, Enum):
    """Categories of placeable furniture."""
    SEATING = "seating"
    TABLE = "table"
    BED = "bed"
    STORAGE = "storage"
    DECORATION = "decoration"
    LIGHTING = "lighting"
    APPLIANCE = "appliance"
    OUTDOOR = "outdoor"
    WALL = "wall"
    FLOOR = "floor"
    RUG = "rug"
    PLANT = "plant"


class FurniturePlacement(str, Enum):
    """Where furniture can be placed."""
    FLOOR = "floor"
    WALL = "wall"
    CEILING = "ceiling"
    OUTDOOR = "outdoor"
    ANY = "any"


class VisitorStatus(str, Enum):
    """Status of a visitor invitation."""
    INVITED = "invited"
    VISITING = "visiting"
    LEFT = "left"
    KICKED = "kicked"
    BANNED = "banned"


class PermissionLevel(str, Enum):
    """Permission levels for housing access."""
    OWNER = "owner"
    CO_OWNER = "co_owner"
    EDITOR = "editor"
    VISITOR = "visitor"
    BLOCKED = "blocked"


class HousingEventKind(str, Enum):
    """Audit event types emitted by the housing system."""
    PLOT_TEMPLATE_REGISTERED = "plot_template_registered"
    PLOT_TEMPLATE_REMOVED = "plot_template_removed"
    HOUSE_TEMPLATE_REGISTERED = "house_template_registered"
    HOUSE_TEMPLATE_REMOVED = "house_template_removed"
    FURNITURE_REGISTERED = "furniture_registered"
    FURNITURE_REMOVED = "furniture_removed"
    PLOT_ACQUIRED = "plot_acquired"
    PLOT_RELEASED = "plot_released"
    HOUSE_BUILT = "house_built"
    HOUSE_DEMOLISHED = "house_demolished"
    HOUSE_UPGRADED = "house_upgraded"
    FURNITURE_PLACED = "furniture_placed"
    FURNITURE_REMOVED_FROM_PLOT = "furniture_removed_from_plot"
    FURNITURE_MOVED = "furniture_moved"
    ROOM_CUSTOMIZED = "room_customized"
    VISITOR_INVITED = "visitor_invited"
    VISITOR_REMOVED = "visitor_removed"
    PERMISSION_SET = "permission_set"
    NEIGHBORHOOD_REGISTERED = "neighborhood_registered"
    NEIGHBORHOOD_JOINED = "neighborhood_joined"
    NEIGHBORHOOD_LEFT = "neighborhood_left"
    HOUSING_RATED = "housing_rated"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FurnitureItem:
    """Catalog definition of a placeable furniture item."""
    furniture_id: str
    name: str
    description: str = ""
    category: str = FurnitureCategory.DECORATION.value
    placement: str = FurniturePlacement.FLOOR.value
    rarity: str = "common"
    width: float = 1.0
    height: float = 1.0
    depth: float = 1.0
    color: str = "#888888"
    icon: str = ""
    mesh_id: str = ""
    stat_bonus: Dict[str, float] = field(default_factory=dict)
    craft_cost: float = 0.0
    unlock_level: int = 1
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HouseTemplate:
    """Template for a buildable house."""
    template_id: str
    name: str
    description: str = ""
    style: str = HouseStyle.COTTAGE.value
    plot_size_required: str = PlotSize.SMALL.value
    room_count: int = 3
    floor_count: int = 1
    base_cost: float = 1000.0
    upgrade_cost: float = 2500.0
    max_upgrades: int = 5
    prestige: int = 0
    icon: str = ""
    blueprint_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingPlot:
    """A plot of land that can be owned by a player."""
    plot_id: str
    template_id: str
    name: str = ""
    owner_id: str = ""
    size: str = PlotSize.SMALL.value
    location: str = ""
    neighborhood_id: str = ""
    width: float = 20.0
    depth: float = 20.0
    is_occupied: bool = False
    acquired_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlacedFurniture:
    """A furniture item placed in a player's house."""
    placement_id: str
    furniture_id: str
    room_index: int = 0
    floor_index: int = 0
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    rotation_y: float = 0.0
    scale: float = 1.0
    placed_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RoomCustomization:
    """Visual customization for a room."""
    room_index: int
    wallpaper_id: str = "wp_default"
    wallpaper_color: str = "#F5F5DC"
    floor_id: str = "fl_default"
    floor_color: str = "#8B4513"
    ceiling_id: str = "cl_default"
    ceiling_color: str = "#FFFFFF"
    lighting_id: str = "lt_warm"
    lighting_intensity: float = 1.0
    ambient_color: str = "#FFFFFF"
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VisitorEntry:
    """A visitor record for a player's housing."""
    visitor_id: str
    player_id: str
    status: str = VisitorStatus.INVITED.value
    invited_at: float = field(default_factory=_now)
    visited_at: float = 0.0
    left_at: float = 0.0
    permission: str = PermissionLevel.VISITOR.value

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerHousing:
    """A player's housing instance on a plot."""
    housing_id: str
    plot_id: str
    owner_id: str
    house_template_id: str = ""
    house_name: str = ""
    house_level: int = 0
    placed_furniture: List[PlacedFurniture] = field(default_factory=list)
    room_customizations: Dict[int, RoomCustomization] = field(default_factory=dict)
    visitors: List[VisitorEntry] = field(default_factory=list)
    permissions: Dict[str, str] = field(default_factory=dict)
    rating_sum: float = 0.0
    rating_count: int = 0
    prestige_score: float = 0.0
    is_public: bool = False
    last_visited_at: float = 0.0
    created_at: float = field(default_factory=_now)

    @property
    def average_rating(self) -> float:
        if self.rating_count <= 0:
            return 0.0
        return round(self.rating_sum / self.rating_count, 2)

    @property
    def furniture_count(self) -> int:
        return len(self.placed_furniture)

    @property
    def active_visitor_count(self) -> int:
        return sum(1 for v in self.visitors if v.status == VisitorStatus.VISITING.value)

    def to_dict(self) -> Dict[str, Any]:
        result = _dataclass_to_dict(self)
        result["average_rating"] = self.average_rating
        result["furniture_count"] = self.furniture_count
        result["active_visitor_count"] = self.active_visitor_count
        return result


@dataclass
class Neighborhood:
    """A community of housing plots."""
    neighborhood_id: str
    name: str
    description: str = ""
    founder_id: str = ""
    plot_ids: List[str] = field(default_factory=list)
    member_ids: List[str] = field(default_factory=list)
    is_open: bool = True
    min_prestige: float = 0.0
    icon: str = ""
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingConfig:
    """Global tuning parameters."""
    max_plot_templates: int = 200
    max_house_templates: int = 500
    max_furniture_catalog: int = 5000
    max_player_plots: int = 100000
    max_placed_furniture_per_house: int = 500
    max_visitors_per_house: int = 50
    max_neighborhoods: int = 1000
    base_plot_cost: float = 5000.0
    prestige_decay_rate: float = 0.0
    visitor_timeout_seconds: float = 3600.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingStats:
    """Aggregate statistics."""
    total_plot_templates: int = 0
    total_house_templates: int = 0
    total_furniture: int = 0
    total_plots: int = 0
    occupied_plots: int = 0
    total_houses: int = 0
    total_furniture_placed: int = 0
    total_visitors: int = 0
    active_visitors: int = 0
    total_neighborhoods: int = 0
    total_ratings: int = 0
    average_rating: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingSnapshot:
    """Full state snapshot."""
    plot_templates: List[Dict[str, Any]] = field(default_factory=list)
    house_templates: List[Dict[str, Any]] = field(default_factory=list)
    furniture_catalog: List[Dict[str, Any]] = field(default_factory=list)
    neighborhoods: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HousingEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    plot_id: str = ""
    housing_id: str = ""
    player_id: str = ""
    furniture_id: str = ""
    neighborhood_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Player Housing System
# ---------------------------------------------------------------------------

class PlayerHousingSystem:
    """Manages player housing, furniture, visitors, and neighborhoods."""

    _instance: Optional["PlayerHousingSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._plot_templates: Dict[str, HousingPlot] = {}
        self._house_templates: Dict[str, HouseTemplate] = {}
        self._furniture_catalog: Dict[str, FurnitureItem] = {}
        self._plots: Dict[str, HousingPlot] = {}
        self._player_housings: Dict[str, PlayerHousing] = {}
        self._neighborhoods: Dict[str, Neighborhood] = {}
        self._events: List[HousingEvent] = []
        self._stats = HousingStats()
        self._config = HousingConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "PlayerHousingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            # Plot templates - different sizes
            plot_defs = [
                ("plot_tpl_small_01", "Cozy Corner", PlotSize.SMALL.value,
                 "Meadow Hills", 15.0, 15.0),
                ("plot_tpl_medium_01", "Garden Patch", PlotSize.MEDIUM.value,
                 "Meadow Hills", 25.0, 25.0),
                ("plot_tpl_large_01", "Hillside Estate", PlotSize.LARGE.value,
                 "Highland Ridge", 40.0, 40.0),
                ("plot_tpl_estate_01", "Grand Domain", PlotSize.ESTATE.value,
                 "Royal Valley", 60.0, 60.0),
                ("plot_tpl_guild_01", "Guild Hall Grounds", PlotSize.GUILD_HALL.value,
                 "Guild District", 80.0, 80.0),
            ]
            for pid, name, size, loc, w, d in plot_defs:
                self._plot_templates[pid] = HousingPlot(
                    plot_id=pid, template_id=pid, name=name,
                    size=size, location=loc, width=w, depth=d,
                )

            # House templates - various styles
            house_defs = [
                ("house_tpl_cottage_01", "Forest Cottage", HouseStyle.COTTAGE.value,
                 PlotSize.SMALL.value, 3, 1, 1000.0, 2500.0, 5, 10),
                ("house_tpl_villa_01", "Sunset Villa", HouseStyle.VILLA.value,
                 PlotSize.MEDIUM.value, 5, 1, 5000.0, 5000.0, 5, 25),
                ("house_tpl_manor_01", "Noble Manor", HouseStyle.MANOR.value,
                 PlotSize.LARGE.value, 8, 2, 15000.0, 8000.0, 5, 50),
                ("house_tpl_tower_01", "Wizard Tower", HouseStyle.TOWER.value,
                 PlotSize.MEDIUM.value, 4, 5, 12000.0, 7000.0, 5, 40),
                ("house_tpl_castle_01", "Royal Castle", HouseStyle.CASTLE.value,
                 PlotSize.ESTATE.value, 12, 3, 50000.0, 20000.0, 5, 100),
                ("house_tpl_tree_01", "Ancient Treehouse", HouseStyle.TREEHOUSE.value,
                 PlotSize.MEDIUM.value, 4, 3, 8000.0, 6000.0, 5, 35),
                ("house_tpl_sky_01", "Sky Pavilion", HouseStyle.SKY_ISLAND.value,
                 PlotSize.LARGE.value, 6, 2, 20000.0, 10000.0, 5, 60),
            ]
            for tid, name, style, req_size, rooms, floors, cost, up_cost, max_up, prestige in house_defs:
                self._house_templates[tid] = HouseTemplate(
                    template_id=tid, name=name, style=style,
                    plot_size_required=req_size, room_count=rooms,
                    floor_count=floors, base_cost=cost, upgrade_cost=up_cost,
                    max_upgrades=max_up, prestige=prestige,
                )

            # Furniture catalog
            furniture_defs = [
                ("furn_chair_oak", "Oak Chair", FurnitureCategory.SEATING.value,
                 FurniturePlacement.FLOOR.value, "common", 0.5, 1.0, 0.5, "#8B4513"),
                ("furn_table_dining", "Dining Table", FurnitureCategory.TABLE.value,
                 FurniturePlacement.FLOOR.value, "common", 2.0, 0.8, 1.0, "#A0522D"),
                ("furn_bed_king", "King Bed", FurnitureCategory.BED.value,
                 FurniturePlacement.FLOOR.value, "uncommon", 2.0, 0.8, 2.2, "#DDA0DD"),
                ("furn_chest_storage", "Storage Chest", FurnitureCategory.STORAGE.value,
                 FurniturePlacement.FLOOR.value, "common", 1.0, 0.8, 0.6, "#654321"),
                ("furn_painting_wall", "Wall Painting", FurnitureCategory.WALL.value,
                 FurniturePlacement.WALL.value, "uncommon", 1.2, 0.8, 0.05, "#FFD700"),
                ("furn_lamp_ceiling", "Ceiling Lamp", FurnitureCategory.LIGHTING.value,
                 FurniturePlacement.CEILING.value, "common", 0.3, 0.3, 0.3, "#FFFFE0"),
                ("furn_rug_persian", "Persian Rug", FurnitureCategory.RUG.value,
                 FurniturePlacement.FLOOR.value, "rare", 3.0, 0.05, 4.0, "#DC143C"),
                ("furn_plant_fern", "Fern Plant", FurnitureCategory.PLANT.value,
                 FurniturePlacement.FLOOR.value, "common", 0.5, 1.2, 0.5, "#228B22"),
                ("furn_statue_marble", "Marble Statue", FurnitureCategory.DECORATION.value,
                 FurniturePlacement.FLOOR.value, "epic", 1.0, 2.0, 1.0, "#F5F5F5"),
                ("furn_fountain_outdoor", "Garden Fountain", FurnitureCategory.OUTDOOR.value,
                 FurniturePlacement.OUTDOOR.value, "rare", 2.0, 1.5, 2.0, "#4682B4"),
                ("furn_sofa_velvet", "Velvet Sofa", FurnitureCategory.SEATING.value,
                 FurniturePlacement.FLOOR.value, "uncommon", 2.5, 0.9, 1.0, "#8B0000"),
                ("furn_bookshelf", "Tall Bookshelf", FurnitureCategory.STORAGE.value,
                 FurniturePlacement.FLOOR.value, "common", 1.2, 2.5, 0.4, "#5C4033"),
            ]
            for fid, name, cat, placement, rarity, w, h, d, color in furniture_defs:
                self._furniture_catalog[fid] = FurnitureItem(
                    furniture_id=fid, name=name, category=cat,
                    placement=placement, rarity=rarity,
                    width=w, height=h, depth=d, color=color,
                    craft_cost={"common": 100, "uncommon": 500,
                                "rare": 2000, "epic": 8000,
                                "legendary": 25000}.get(rarity, 100),
                )

            # Actual plots
            self._plots["plot_starter_01"] = HousingPlot(
                plot_id="plot_starter_01", template_id="plot_tpl_small_01",
                name="Starter Cozy Corner", owner_id="player_starter",
                size=PlotSize.SMALL.value, location="Meadow Hills",
                width=15.0, depth=15.0, is_occupied=True,
                acquired_at=_now() - 86400 * 7,
            )
            self._plots["plot_veteran_01"] = HousingPlot(
                plot_id="plot_veteran_01", template_id="plot_tpl_large_01",
                name="Veteran Hillside Estate", owner_id="player_veteran",
                size=PlotSize.LARGE.value, location="Highland Ridge",
                width=40.0, depth=40.0, is_occupied=True,
                acquired_at=_now() - 86400 * 30,
            )
            self._plots["plot_empty_01"] = HousingPlot(
                plot_id="plot_empty_01", template_id="plot_tpl_medium_01",
                name="Available Garden Patch", owner_id="",
                size=PlotSize.MEDIUM.value, location="Meadow Hills",
                width=25.0, depth=25.0, is_occupied=False,
            )

            # Player housings
            ph1 = PlayerHousing(
                housing_id="hous_starter_01", plot_id="plot_starter_01",
                owner_id="player_starter",
                house_template_id="house_tpl_cottage_01",
                house_name="Starter Forest Cottage",
                house_level=1, is_public=True,
            )
            ph1.placed_furniture.append(PlacedFurniture(
                placement_id="place_001", furniture_id="furn_chair_oak",
                room_index=0, position_x=2.0, position_z=2.0,
            ))
            ph1.placed_furniture.append(PlacedFurniture(
                placement_id="place_002", furniture_id="furn_table_dining",
                room_index=0, position_x=3.0, position_z=2.5,
            ))
            ph1.placed_furniture.append(PlacedFurniture(
                placement_id="place_003", furniture_id="furn_bed_king",
                room_index=1, position_x=1.0, position_z=1.0,
            ))
            ph1.room_customizations[0] = RoomCustomization(
                room_index=0, wallpaper_color="#E0FFFF", floor_color="#DEB887",
            )
            ph1.room_customizations[1] = RoomCustomization(
                room_index=1, wallpaper_color="#FFE4E1", floor_color="#8B4513",
            )
            ph1.rating_sum = 12.0
            ph1.rating_count = 3
            ph1.prestige_score = 15.0
            self._player_housings["hous_starter_01"] = ph1

            ph2 = PlayerHousing(
                housing_id="hous_veteran_01", plot_id="plot_veteran_01",
                owner_id="player_veteran",
                house_template_id="house_tpl_manor_01",
                house_name="Veteran Noble Manor",
                house_level=3, is_public=True,
            )
            ph2.placed_furniture.append(PlacedFurniture(
                placement_id="place_101", furniture_id="furn_sofa_velvet",
                room_index=0, position_x=4.0, position_z=3.0,
            ))
            ph2.placed_furniture.append(PlacedFurniture(
                placement_id="place_102", furniture_id="furn_statue_marble",
                room_index=0, position_x=6.0, position_z=2.0,
            ))
            ph2.placed_furniture.append(PlacedFurniture(
                placement_id="place_103", furniture_id="furn_rug_persian",
                room_index=0, position_x=5.0, position_z=3.5,
            ))
            ph2.placed_furniture.append(PlacedFurniture(
                placement_id="place_104", furniture_id="furn_bookshelf",
                room_index=1, position_x=1.0, position_z=0.5,
            ))
            ph2.placed_furniture.append(PlacedFurniture(
                placement_id="place_105", furniture_id="furn_fountain_outdoor",
                room_index=0, floor_index=-1, position_x=10.0, position_z=10.0,
            ))
            ph2.room_customizations[0] = RoomCustomization(
                room_index=0, wallpaper_color="#FFD700", floor_color="#8B0000",
                lighting_intensity=1.2,
            )
            ph2.room_customizations[1] = RoomCustomization(
                room_index=1, wallpaper_color="#F5F5DC", floor_color="#5C4033",
            )
            ph2.visitors.append(VisitorEntry(
                visitor_id="vis_001", player_id="player_starter",
                status=VisitorStatus.VISITING.value,
                invited_at=_now() - 3600, visited_at=_now() - 1800,
                permission=PermissionLevel.VISITOR.value,
            ))
            ph2.rating_sum = 47.0
            ph2.rating_count = 10
            ph2.prestige_score = 85.0
            ph2.last_visited_at = _now() - 1800
            self._player_housings["hous_veteran_01"] = ph2

            # Neighborhoods
            nb1 = Neighborhood(
                neighborhood_id="nb_meadow_hills",
                name="Meadow Hills Community",
                description="A peaceful community in the meadow hills.",
                founder_id="player_starter",
                plot_ids=["plot_starter_01"],
                member_ids=["player_starter"],
                is_open=True, min_prestige=0.0,
            )
            self._neighborhoods["nb_meadow_hills"] = nb1

            nb2 = Neighborhood(
                neighborhood_id="nb_highland_elite",
                name="Highland Elite Estates",
                description="Exclusive estates for distinguished players.",
                founder_id="player_veteran",
                plot_ids=["plot_veteran_01"],
                member_ids=["player_veteran"],
                is_open=False, min_prestige=50.0,
            )
            self._neighborhoods["nb_highland_elite"] = nb2

            self._update_stats()
            self._initialized = True

    def _log_event(self, kind: str, details: Dict[str, Any],
                   plot_id: str = "", housing_id: str = "",
                   player_id: str = "", furniture_id: str = "",
                   neighborhood_id: str = "",
                   description: str = "") -> None:
        self._event_counter += 1
        event = HousingEvent(
            event_id=f"hevt_{self._event_counter:06d}",
            kind=kind, timestamp=_now(),
            plot_id=plot_id, housing_id=housing_id,
            player_id=player_id, furniture_id=furniture_id,
            neighborhood_id=neighborhood_id,
            description=description, details=details,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_stats(self) -> None:
        self._stats.total_plot_templates = len(self._plot_templates)
        self._stats.total_house_templates = len(self._house_templates)
        self._stats.total_furniture = len(self._furniture_catalog)
        self._stats.total_plots = len(self._plots)
        self._stats.occupied_plots = sum(1 for p in self._plots.values() if p.is_occupied)
        self._stats.total_houses = len(self._player_housings)
        self._stats.total_furniture_placed = sum(
            len(ph.placed_furniture) for ph in self._player_housings.values()
        )
        self._stats.total_visitors = sum(
            len(ph.visitors) for ph in self._player_housings.values()
        )
        self._stats.active_visitors = sum(
            ph.active_visitor_count for ph in self._player_housings.values()
        )
        self._stats.total_neighborhoods = len(self._neighborhoods)
        self._stats.total_ratings = sum(
            ph.rating_count for ph in self._player_housings.values()
        )
        total_sum = sum(ph.rating_sum for ph in self._player_housings.values())
        if self._stats.total_ratings > 0:
            self._stats.average_rating = round(
                total_sum / self._stats.total_ratings, 2
            )
        else:
            self._stats.average_rating = 0.0

    # ------------------------------------------------------------------
    # Plot Template Management
    # ------------------------------------------------------------------

    def register_plot_template(self, plot_id: str, name: str, size: str,
                               location: str, width: float = 20.0,
                               depth: float = 20.0
                               ) -> Tuple[bool, str, Optional[HousingPlot]]:
        with _LOCK:
            if plot_id in self._plot_templates:
                return False, "already_exists", self._plot_templates[plot_id]
            if len(self._plot_templates) >= _MAX_PLOT_TEMPLATES:
                return False, "capacity_reached", None
            plot = HousingPlot(
                plot_id=plot_id, template_id=plot_id, name=name,
                size=size, location=location, width=width, depth=depth,
            )
            self._plot_templates[plot_id] = plot
            self._log_event(HousingEventKind.PLOT_TEMPLATE_REGISTERED.value,
                            {"name": name, "size": size},
                            description=plot_id)
            self._update_stats()
            return True, "registered", plot

    def remove_plot_template(self, plot_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if plot_id not in self._plot_templates:
                return False, "not_found"
            del self._plot_templates[plot_id]
            self._log_event(HousingEventKind.PLOT_TEMPLATE_REMOVED.value,
                            {}, description=plot_id)
            self._update_stats()
            return True, "removed"

    def get_plot_template(self, plot_id: str) -> Optional[HousingPlot]:
        with _LOCK:
            return self._plot_templates.get(plot_id)

    def list_plot_templates(self, size: str = "") -> List[HousingPlot]:
        with _LOCK:
            results = list(self._plot_templates.values())
            if size:
                results = [p for p in results if p.size == size]
            return results

    # ------------------------------------------------------------------
    # House Template Management
    # ------------------------------------------------------------------

    def register_house_template(self, template_id: str, name: str,
                                style: str, plot_size_required: str,
                                room_count: int = 3, floor_count: int = 1,
                                base_cost: float = 1000.0,
                                upgrade_cost: float = 2500.0,
                                max_upgrades: int = 5,
                                prestige: int = 0,
                                description: str = ""
                                ) -> Tuple[bool, str, Optional[HouseTemplate]]:
        with _LOCK:
            if template_id in self._house_templates:
                return False, "already_exists", self._house_templates[template_id]
            if len(self._house_templates) >= _MAX_HOUSE_TEMPLATES:
                return False, "capacity_reached", None
            tpl = HouseTemplate(
                template_id=template_id, name=name, style=style,
                plot_size_required=plot_size_required,
                room_count=room_count, floor_count=floor_count,
                base_cost=base_cost, upgrade_cost=upgrade_cost,
                max_upgrades=max_upgrades, prestige=prestige,
                description=description,
            )
            self._house_templates[template_id] = tpl
            self._log_event(HousingEventKind.HOUSE_TEMPLATE_REGISTERED.value,
                            {"name": name, "style": style},
                            description=template_id)
            self._update_stats()
            return True, "registered", tpl

    def remove_house_template(self, template_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if template_id not in self._house_templates:
                return False, "not_found"
            del self._house_templates[template_id]
            self._log_event(HousingEventKind.HOUSE_TEMPLATE_REMOVED.value,
                            {}, description=template_id)
            self._update_stats()
            return True, "removed"

    def get_house_template(self, template_id: str) -> Optional[HouseTemplate]:
        with _LOCK:
            return self._house_templates.get(template_id)

    def list_house_templates(self, style: str = "",
                             plot_size_required: str = ""
                             ) -> List[HouseTemplate]:
        with _LOCK:
            results = list(self._house_templates.values())
            if style:
                results = [t for t in results if t.style == style]
            if plot_size_required:
                results = [t for t in results if t.plot_size_required == plot_size_required]
            return results

    # ------------------------------------------------------------------
    # Furniture Catalog Management
    # ------------------------------------------------------------------

    def register_furniture(self, furniture_id: str, name: str,
                           category: str = FurnitureCategory.DECORATION.value,
                           placement: str = FurniturePlacement.FLOOR.value,
                           rarity: str = "common",
                           width: float = 1.0, height: float = 1.0,
                           depth: float = 1.0, color: str = "#888888",
                           description: str = "",
                           craft_cost: float = 0.0,
                           unlock_level: int = 1
                           ) -> Tuple[bool, str, Optional[FurnitureItem]]:
        with _LOCK:
            if furniture_id in self._furniture_catalog:
                return False, "already_exists", self._furniture_catalog[furniture_id]
            if len(self._furniture_catalog) >= _MAX_FURNITURE_CATALOG:
                return False, "capacity_reached", None
            item = FurnitureItem(
                furniture_id=furniture_id, name=name, description=description,
                category=category, placement=placement, rarity=rarity,
                width=width, height=height, depth=depth, color=color,
                craft_cost=craft_cost, unlock_level=unlock_level,
            )
            self._furniture_catalog[furniture_id] = item
            self._log_event(HousingEventKind.FURNITURE_REGISTERED.value,
                            {"name": name, "category": category},
                            furniture_id=furniture_id)
            self._update_stats()
            return True, "registered", item

    def remove_furniture(self, furniture_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if furniture_id not in self._furniture_catalog:
                return False, "not_found"
            del self._furniture_catalog[furniture_id]
            self._log_event(HousingEventKind.FURNITURE_REMOVED.value,
                            {}, furniture_id=furniture_id)
            self._update_stats()
            return True, "removed"

    def get_furniture(self, furniture_id: str) -> Optional[FurnitureItem]:
        with _LOCK:
            return self._furniture_catalog.get(furniture_id)

    def list_furniture(self, category: str = "",
                       rarity: str = "",
                       placement: str = "") -> List[FurnitureItem]:
        with _LOCK:
            results = list(self._furniture_catalog.values())
            if category:
                results = [f for f in results if f.category == category]
            if rarity:
                results = [f for f in results if f.rarity == rarity]
            if placement:
                results = [f for f in results if f.placement == placement]
            return results

    # ------------------------------------------------------------------
    # Plot Management
    # ------------------------------------------------------------------

    def acquire_plot(self, player_id: str, template_id: str,
                     plot_name: str = ""
                     ) -> Tuple[bool, str, Optional[HousingPlot]]:
        with _LOCK:
            tpl = self._plot_templates.get(template_id)
            if tpl is None:
                return False, "template_not_found", None
            plot_id = _new_id("plot")
            plot = HousingPlot(
                plot_id=plot_id, template_id=template_id,
                name=plot_name or f"{tpl.name} ({player_id})",
                owner_id=player_id, size=tpl.size, location=tpl.location,
                width=tpl.width, depth=tpl.depth,
                is_occupied=True, acquired_at=_now(),
            )
            self._plots[plot_id] = plot
            self._log_event(HousingEventKind.PLOT_ACQUIRED.value,
                            {"player_id": player_id, "template_id": template_id},
                            plot_id=plot_id, player_id=player_id)
            self._update_stats()
            return True, "acquired", plot

    def release_plot(self, plot_id: str) -> Tuple[bool, str]:
        with _LOCK:
            plot = self._plots.get(plot_id)
            if plot is None:
                return False, "not_found"
            if plot.owner_id == "":
                return False, "not_occupied"
            housing = self._find_housing_by_plot(plot_id)
            if housing is not None:
                self._player_housings.pop(housing.housing_id, None)
            plot.owner_id = ""
            plot.is_occupied = False
            plot.name = f"Available {plot.size.title()} Plot"
            self._log_event(HousingEventKind.PLOT_RELEASED.value,
                            {"plot_id": plot_id}, plot_id=plot_id)
            self._update_stats()
            return True, "released"

    def get_plot(self, plot_id: str) -> Optional[HousingPlot]:
        with _LOCK:
            return self._plots.get(plot_id)

    def list_plots(self, owner_id: str = "", size: str = "",
                   location: str = "", available_only: bool = False
                   ) -> List[HousingPlot]:
        with _LOCK:
            results = list(self._plots.values())
            if owner_id:
                results = [p for p in results if p.owner_id == owner_id]
            if size:
                results = [p for p in results if p.size == size]
            if location:
                results = [p for p in results if p.location == location]
            if available_only:
                results = [p for p in results if not p.is_occupied]
            return results

    def _find_housing_by_plot(self, plot_id: str) -> Optional[PlayerHousing]:
        for ph in self._player_housings.values():
            if ph.plot_id == plot_id:
                return ph
        return None

    def get_housing_by_plot(self, plot_id: str) -> Optional[PlayerHousing]:
        with _LOCK:
            return self._find_housing_by_plot(plot_id)

    def get_housing(self, housing_id: str) -> Optional[PlayerHousing]:
        with _LOCK:
            return self._player_housings.get(housing_id)

    def list_housings(self, owner_id: str = "",
                      is_public: Optional[bool] = None
                      ) -> List[PlayerHousing]:
        with _LOCK:
            results = list(self._player_housings.values())
            if owner_id:
                results = [h for h in results if h.owner_id == owner_id]
            if is_public is not None:
                results = [h for h in results if h.is_public == is_public]
            return results

    # ------------------------------------------------------------------
    # House Construction
    # ------------------------------------------------------------------

    def build_house(self, plot_id: str, house_template_id: str,
                    house_name: str = ""
                    ) -> Tuple[bool, str, Optional[PlayerHousing]]:
        with _LOCK:
            plot = self._plots.get(plot_id)
            if plot is None:
                return False, "plot_not_found", None
            if not plot.is_occupied or plot.owner_id == "":
                return False, "plot_not_owned", None
            tpl = self._house_templates.get(house_template_id)
            if tpl is None:
                return False, "template_not_found", None
            if tpl.plot_size_required != plot.size:
                size_order = [PlotSize.SMALL.value, PlotSize.MEDIUM.value,
                              PlotSize.LARGE.value, PlotSize.ESTATE.value,
                              PlotSize.GUILD_HALL.value]
                req_idx = size_order.index(tpl.plot_size_required) if tpl.plot_size_required in size_order else 0
                plot_idx = size_order.index(plot.size) if plot.size in size_order else 0
                if plot_idx < req_idx:
                    return False, "plot_too_small", None
            existing = self._find_housing_by_plot(plot_id)
            if existing is not None:
                return False, "house_already_built", existing
            housing_id = _new_id("hous")
            ph = PlayerHousing(
                housing_id=housing_id, plot_id=plot_id,
                owner_id=plot.owner_id,
                house_template_id=house_template_id,
                house_name=house_name or tpl.name,
                house_level=1,
                prestige_score=float(tpl.prestige),
            )
            for room_idx in range(tpl.room_count):
                ph.room_customizations[room_idx] = RoomCustomization(room_index=room_idx)
            ph.permissions[plot.owner_id] = PermissionLevel.OWNER.value
            self._player_housings[housing_id] = ph
            self._log_event(HousingEventKind.HOUSE_BUILT.value,
                            {"template_id": house_template_id,
                             "house_name": ph.house_name},
                            plot_id=plot_id, housing_id=housing_id,
                            player_id=plot.owner_id)
            self._update_stats()
            return True, "built", ph

    def demolish_house(self, housing_id: str) -> Tuple[bool, str]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "not_found"
            plot_id = ph.plot_id
            del self._player_housings[housing_id]
            self._log_event(HousingEventKind.HOUSE_DEMOLISHED.value,
                            {"house_name": ph.house_name},
                            plot_id=plot_id, housing_id=housing_id,
                            player_id=ph.owner_id)
            self._update_stats()
            return True, "demolished"

    def upgrade_house(self, housing_id: str
                      ) -> Tuple[bool, str, Optional[PlayerHousing]]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "not_found", None
            tpl = self._house_templates.get(ph.house_template_id)
            if tpl is None:
                return False, "template_not_found", None
            if ph.house_level >= tpl.max_upgrades:
                return False, "max_level_reached", ph
            ph.house_level += 1
            ph.prestige_score += float(tpl.prestige) * 0.5
            new_rooms = tpl.room_count + ph.house_level - 1
            for room_idx in range(len(ph.room_customizations), new_rooms):
                ph.room_customizations[room_idx] = RoomCustomization(room_index=room_idx)
            self._log_event(HousingEventKind.HOUSE_UPGRADED.value,
                            {"new_level": ph.house_level,
                             "new_prestige": ph.prestige_score},
                            housing_id=housing_id, player_id=ph.owner_id)
            return True, "upgraded", ph

    # ------------------------------------------------------------------
    # Furniture Placement
    # ------------------------------------------------------------------

    def place_furniture(self, housing_id: str, furniture_id: str,
                        room_index: int = 0, floor_index: int = 0,
                        position_x: float = 0.0, position_y: float = 0.0,
                        position_z: float = 0.0, rotation_y: float = 0.0,
                        scale: float = 1.0
                        ) -> Tuple[bool, str, Optional[PlacedFurniture]]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found", None
            item = self._furniture_catalog.get(furniture_id)
            if item is None:
                return False, "furniture_not_found", None
            if len(ph.placed_furniture) >= self._config.max_placed_furniture_per_house:
                return False, "capacity_reached", None
            if room_index not in ph.room_customizations and room_index >= 0:
                tpl = self._house_templates.get(ph.house_template_id)
                if tpl and room_index >= tpl.room_count + ph.house_level - 1:
                    return False, "room_not_found", None
                ph.room_customizations[room_index] = RoomCustomization(room_index=room_index)
            placement_id = _new_id("place")
            placed = PlacedFurniture(
                placement_id=placement_id, furniture_id=furniture_id,
                room_index=room_index, floor_index=floor_index,
                position_x=position_x, position_y=position_y,
                position_z=position_z, rotation_y=rotation_y, scale=scale,
            )
            ph.placed_furniture.append(placed)
            self._log_event(HousingEventKind.FURNITURE_PLACED.value,
                            {"furniture_id": furniture_id,
                             "room_index": room_index},
                            housing_id=housing_id, furniture_id=furniture_id,
                            player_id=ph.owner_id)
            self._update_stats()
            return True, "placed", placed

    def remove_furniture_from_plot(self, housing_id: str,
                                   placement_id: str) -> Tuple[bool, str]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found"
            for i, pf in enumerate(ph.placed_furniture):
                if pf.placement_id == placement_id:
                    ph.placed_furniture.pop(i)
                    self._log_event(
                        HousingEventKind.FURNITURE_REMOVED_FROM_PLOT.value,
                        {"placement_id": placement_id,
                         "furniture_id": pf.furniture_id},
                        housing_id=housing_id, furniture_id=pf.furniture_id,
                        player_id=ph.owner_id,
                    )
                    self._update_stats()
                    return True, "removed"
            return False, "placement_not_found"

    def move_furniture(self, housing_id: str, placement_id: str,
                       position_x: float = 0.0, position_y: float = 0.0,
                       position_z: float = 0.0, rotation_y: float = 0.0,
                       scale: float = 1.0, room_index: Optional[int] = None
                       ) -> Tuple[bool, str, Optional[PlacedFurniture]]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found", None
            for pf in ph.placed_furniture:
                if pf.placement_id == placement_id:
                    pf.position_x = position_x
                    pf.position_y = position_y
                    pf.position_z = position_z
                    pf.rotation_y = rotation_y
                    pf.scale = scale
                    if room_index is not None:
                        pf.room_index = room_index
                    self._log_event(HousingEventKind.FURNITURE_MOVED.value,
                                    {"placement_id": placement_id,
                                     "x": position_x, "z": position_z},
                                    housing_id=housing_id,
                                    furniture_id=pf.furniture_id,
                                    player_id=ph.owner_id)
                    return True, "moved", pf
            return False, "placement_not_found", None

    def list_placed_furniture(self, housing_id: str,
                              room_index: Optional[int] = None
                              ) -> List[PlacedFurniture]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return []
            results = list(ph.placed_furniture)
            if room_index is not None:
                results = [pf for pf in results if pf.room_index == room_index]
            return results

    # ------------------------------------------------------------------
    # Room Customization
    # ------------------------------------------------------------------

    def customize_room(self, housing_id: str, room_index: int,
                       wallpaper_id: str = "", wallpaper_color: str = "",
                       floor_id: str = "", floor_color: str = "",
                       ceiling_id: str = "", ceiling_color: str = "",
                       lighting_id: str = "", lighting_intensity: float = -1.0,
                       ambient_color: str = ""
                       ) -> Tuple[bool, str, Optional[RoomCustomization]]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found", None
            room = ph.room_customizations.get(room_index)
            if room is None:
                room = RoomCustomization(room_index=room_index)
                ph.room_customizations[room_index] = room
            if wallpaper_id:
                room.wallpaper_id = wallpaper_id
            if wallpaper_color:
                room.wallpaper_color = wallpaper_color
            if floor_id:
                room.floor_id = floor_id
            if floor_color:
                room.floor_color = floor_color
            if ceiling_id:
                room.ceiling_id = ceiling_id
            if ceiling_color:
                room.ceiling_color = ceiling_color
            if lighting_id:
                room.lighting_id = lighting_id
            if lighting_intensity >= 0:
                room.lighting_intensity = _clamp(lighting_intensity, 0.0, 3.0)
            if ambient_color:
                room.ambient_color = ambient_color
            room.updated_at = _now()
            self._log_event(HousingEventKind.ROOM_CUSTOMIZED.value,
                            {"room_index": room_index},
                            housing_id=housing_id, player_id=ph.owner_id)
            return True, "customized", room

    def get_room_customization(self, housing_id: str,
                               room_index: int) -> Optional[RoomCustomization]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return None
            return ph.room_customizations.get(room_index)

    # ------------------------------------------------------------------
    # Visitor Management
    # ------------------------------------------------------------------

    def invite_visitor(self, housing_id: str, player_id: str,
                       permission: str = PermissionLevel.VISITOR.value
                       ) -> Tuple[bool, str, Optional[VisitorEntry]]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found", None
            if any(v.player_id == player_id and v.status in
                   (VisitorStatus.INVITED.value, VisitorStatus.VISITING.value)
                   for v in ph.visitors):
                return False, "already_invited", None
            if len(ph.visitors) >= self._config.max_visitors_per_house:
                return False, "capacity_reached", None
            visitor_id = _new_id("vis")
            entry = VisitorEntry(
                visitor_id=visitor_id, player_id=player_id,
                status=VisitorStatus.INVITED.value,
                permission=permission,
            )
            ph.visitors.append(entry)
            ph.permissions[player_id] = permission
            self._log_event(HousingEventKind.VISITOR_INVITED.value,
                            {"player_id": player_id, "permission": permission},
                            housing_id=housing_id, player_id=player_id)
            self._update_stats()
            return True, "invited", entry

    def remove_visitor(self, housing_id: str, player_id: str
                       ) -> Tuple[bool, str]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found"
            for i, v in enumerate(ph.visitors):
                if v.player_id == player_id:
                    v.status = VisitorStatus.LEFT.value
                    v.left_at = _now()
                    ph.visitors.pop(i)
                    ph.permissions.pop(player_id, None)
                    self._log_event(HousingEventKind.VISITOR_REMOVED.value,
                                    {"player_id": player_id},
                                    housing_id=housing_id, player_id=player_id)
                    self._update_stats()
                    return True, "removed"
            return False, "visitor_not_found"

    def visitor_enter(self, housing_id: str, player_id: str
                      ) -> Tuple[bool, str, Optional[VisitorEntry]]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found", None
            if not ph.is_public:
                invited = any(v.player_id == player_id and
                              v.status == VisitorStatus.INVITED.value
                              for v in ph.visitors)
                if not invited and player_id != ph.owner_id:
                    return False, "not_invited", None
            for v in ph.visitors:
                if v.player_id == player_id:
                    v.status = VisitorStatus.VISITING.value
                    v.visited_at = _now()
                    ph.last_visited_at = _now()
                    self._update_stats()
                    return True, "visiting", v
            visitor_id = _new_id("vis")
            entry = VisitorEntry(
                visitor_id=visitor_id, player_id=player_id,
                status=VisitorStatus.VISITING.value,
                visited_at=_now(),
            )
            ph.visitors.append(entry)
            ph.last_visited_at = _now()
            self._update_stats()
            return True, "visiting", entry

    def visitor_leave(self, housing_id: str, player_id: str
                      ) -> Tuple[bool, str]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found"
            for v in ph.visitors:
                if v.player_id == player_id and v.status == VisitorStatus.VISITING.value:
                    v.status = VisitorStatus.LEFT.value
                    v.left_at = _now()
                    self._update_stats()
                    return True, "left"
            return False, "visitor_not_visiting"

    def list_visitors(self, housing_id: str,
                      status: str = "") -> List[VisitorEntry]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return []
            results = list(ph.visitors)
            if status:
                results = [v for v in results if v.status == status]
            return results

    def set_permission(self, housing_id: str, player_id: str,
                       permission: str) -> Tuple[bool, str]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found"
            ph.permissions[player_id] = permission
            for v in ph.visitors:
                if v.player_id == player_id:
                    v.permission = permission
            self._log_event(HousingEventKind.PERMISSION_SET.value,
                            {"player_id": player_id, "permission": permission},
                            housing_id=housing_id, player_id=player_id)
            return True, "set"

    def get_permissions(self, housing_id: str) -> Dict[str, str]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return {}
            return dict(ph.permissions)

    # ------------------------------------------------------------------
    # Neighborhood Management
    # ------------------------------------------------------------------

    def register_neighborhood(self, neighborhood_id: str, name: str,
                              founder_id: str, description: str = "",
                              is_open: bool = True,
                              min_prestige: float = 0.0
                              ) -> Tuple[bool, str, Optional[Neighborhood]]:
        with _LOCK:
            if neighborhood_id in self._neighborhoods:
                return False, "already_exists", self._neighborhoods[neighborhood_id]
            if len(self._neighborhoods) >= _MAX_NEIGHBORHOODS:
                return False, "capacity_reached", None
            nb = Neighborhood(
                neighborhood_id=neighborhood_id, name=name,
                description=description, founder_id=founder_id,
                is_open=is_open, min_prestige=min_prestige,
            )
            nb.member_ids.append(founder_id)
            self._neighborhoods[neighborhood_id] = nb
            self._log_event(HousingEventKind.NEIGHBORHOOD_REGISTERED.value,
                            {"name": name, "founder_id": founder_id},
                            neighborhood_id=neighborhood_id,
                            player_id=founder_id)
            self._update_stats()
            return True, "registered", nb

    def join_neighborhood(self, neighborhood_id: str, player_id: str,
                          plot_id: str = ""
                          ) -> Tuple[bool, str, Optional[Neighborhood]]:
        with _LOCK:
            nb = self._neighborhoods.get(neighborhood_id)
            if nb is None:
                return False, "not_found", None
            if not nb.is_open:
                ph = self._find_housing_by_plot(plot_id) if plot_id else None
                prestige = ph.prestige_score if ph else 0.0
                if prestige < nb.min_prestige:
                    return False, "prestige_too_low", None
            if player_id in nb.member_ids:
                return False, "already_member", nb
            nb.member_ids.append(player_id)
            if plot_id and plot_id not in nb.plot_ids:
                nb.plot_ids.append(plot_id)
            self._log_event(HousingEventKind.NEIGHBORHOOD_JOINED.value,
                            {"player_id": player_id, "plot_id": plot_id},
                            neighborhood_id=neighborhood_id,
                            player_id=player_id)
            self._update_stats()
            return True, "joined", nb

    def leave_neighborhood(self, neighborhood_id: str,
                           player_id: str) -> Tuple[bool, str]:
        with _LOCK:
            nb = self._neighborhoods.get(neighborhood_id)
            if nb is None:
                return False, "not_found"
            if player_id not in nb.member_ids:
                return False, "not_member"
            nb.member_ids.remove(player_id)
            nb.plot_ids = [
                pid for pid in nb.plot_ids
                if self._plots.get(pid, None) and self._plots[pid].owner_id != player_id
            ]
            self._log_event(HousingEventKind.NEIGHBORHOOD_LEFT.value,
                            {"player_id": player_id},
                            neighborhood_id=neighborhood_id,
                            player_id=player_id)
            self._update_stats()
            return True, "left"

    def get_neighborhood(self, neighborhood_id: str) -> Optional[Neighborhood]:
        with _LOCK:
            return self._neighborhoods.get(neighborhood_id)

    def list_neighborhoods(self, is_open: Optional[bool] = None
                           ) -> List[Neighborhood]:
        with _LOCK:
            results = list(self._neighborhoods.values())
            if is_open is not None:
                results = [n for n in results if n.is_open == is_open]
            return results

    # ------------------------------------------------------------------
    # Rating System
    # ------------------------------------------------------------------

    def rate_housing(self, housing_id: str, rater_id: str,
                     rating: float, comment: str = ""
                     ) -> Tuple[bool, str, Optional[PlayerHousing]]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return False, "housing_not_found", None
            if rater_id == ph.owner_id:
                return False, "cannot_rate_own", None
            rating = _clamp(rating, 0.0, 5.0)
            ph.rating_sum += rating
            ph.rating_count += 1
            self._log_event(HousingEventKind.HOUSING_RATED.value,
                            {"rater_id": rater_id, "rating": rating,
                             "comment": comment},
                            housing_id=housing_id, player_id=rater_id)
            self._update_stats()
            return True, "rated", ph

    def get_rating(self, housing_id: str) -> Dict[str, Any]:
        with _LOCK:
            ph = self._player_housings.get(housing_id)
            if ph is None:
                return {"housing_id": housing_id, "average_rating": 0.0,
                        "rating_count": 0}
            return {
                "housing_id": housing_id,
                "average_rating": ph.average_rating,
                "rating_count": ph.rating_count,
                "rating_sum": ph.rating_sum,
            }

    def list_top_rated(self, limit: int = 10) -> List[Dict[str, Any]]:
        with _LOCK:
            rated = [
                {
                    "housing_id": ph.housing_id,
                    "house_name": ph.house_name,
                    "owner_id": ph.owner_id,
                    "average_rating": ph.average_rating,
                    "rating_count": ph.rating_count,
                    "prestige_score": ph.prestige_score,
                    "furniture_count": ph.furniture_count,
                }
                for ph in self._player_housings.values()
                if ph.rating_count > 0
            ]
            rated.sort(key=lambda x: (-x["average_rating"], -x["rating_count"]))
            return rated[:limit]

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            timeout = self._config.visitor_timeout_seconds
            now = _now()
            for ph in self._player_housings.values():
                for v in ph.visitors:
                    if v.status == VisitorStatus.VISITING.value:
                        if v.visited_at > 0 and (now - v.visited_at) > timeout:
                            v.status = VisitorStatus.LEFT.value
                            v.left_at = now
            if self._tick_count % 60 == 0:
                self._log_event(HousingEventKind.TICK.value,
                                {"tick": self._tick_count, "dt": dt})
            self._update_stats()
            return {"tick_count": self._tick_count}

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, HousingConfig]:
        with _LOCK:
            for k, v in config.items():
                if hasattr(self._config, k):
                    setattr(self._config, k, v)
            self._log_event(HousingEventKind.CONFIG_UPDATED.value,
                            {"keys": list(config.keys())})
            return True, "updated", self._config

    def get_config(self) -> HousingConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[HousingEvent]:
        with _LOCK:
            results = list(self._events)
            if kind:
                results = [e for e in results if e.kind == kind]
            if limit > 0:
                results = results[-limit:]
            return results

    def get_stats(self) -> HousingStats:
        with _LOCK:
            self._update_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "total_plot_templates": len(self._plot_templates),
                "total_house_templates": len(self._house_templates),
                "total_furniture": len(self._furniture_catalog),
                "total_plots": len(self._plots),
                "occupied_plots": sum(1 for p in self._plots.values() if p.is_occupied),
                "total_housings": len(self._player_housings),
                "total_furniture_placed": sum(
                    len(ph.placed_furniture) for ph in self._player_housings.values()
                ),
                "total_visitors": sum(
                    len(ph.visitors) for ph in self._player_housings.values()
                ),
                "active_visitors": sum(
                    ph.active_visitor_count for ph in self._player_housings.values()
                ),
                "total_neighborhoods": len(self._neighborhoods),
                "total_ratings": sum(
                    ph.rating_count for ph in self._player_housings.values()
                ),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> HousingSnapshot:
        with _LOCK:
            return HousingSnapshot(
                plot_templates=[p.to_dict() for p in list(self._plot_templates.values())[:20]],
                house_templates=[t.to_dict() for t in list(self._house_templates.values())[:20]],
                furniture_catalog=[f.to_dict() for f in list(self._furniture_catalog.values())[:20]],
                neighborhoods=[n.to_dict() for n in list(self._neighborhoods.values())[:20]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> None:
        with _LOCK:
            self._plot_templates.clear()
            self._house_templates.clear()
            self._furniture_catalog.clear()
            self._plots.clear()
            self._player_housings.clear()
            self._neighborhoods.clear()
            self._events.clear()
            self._stats = HousingStats()
            self._config = HousingConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._log_event(HousingEventKind.RESET.value, {})
            self._seed()


def get_player_housing_system() -> PlayerHousingSystem:
    """Factory that returns the singleton PlayerHousingSystem instance."""
    return PlayerHousingSystem.get_instance()
