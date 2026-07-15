"""
SparkLabs Engine - Procedural City Generator

Procedural city generation engine for the SparkLabs AI-native game
engine. Builds coherent urban environments from a seed by laying out
a hierarchical road network, partitioning the area into themed
districts, populating each district with appropriate buildings, and
placing landmark structures (palace, temple, market square).

Core capabilities:
  - Hierarchical road network generation (highways, main roads,
    streets, alleys) using radial and grid patterns
  - District partitioning driven by the road grid with type
    assignment based on distance from the city center
  - Building generation that respects district theme, wealth level,
    and style while avoiding road overlap
  - Landmark placement (palace, temple, market square, barracks,
    watchtower) at strategic positions
  - Optional city walls, river crossing, and port district
  - City analysis covering density, connectivity, and district
    balance metrics

Architecture:
  ProceduralCityEngine (Singleton)
    |-- RoadSegment (dataclass)
    |-- Building (dataclass)
    |-- District (dataclass)
    |-- CityLayout (dataclass)
    |-- CityGenerationConfig (dataclass)
    |-- generate_city()
    |-- generate_road_network()
    |-- generate_districts()
    |-- generate_buildings()
    |-- place_landmark()
    |-- analyze_city()
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DistrictType(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    GOVERNMENT = "government"
    PARK = "park"
    MILITARY = "military"
    SLUM = "slum"
    NOBLE = "noble"


class RoadType(Enum):
    HIGHWAY = "highway"
    MAIN_ROAD = "main_road"
    STREET = "street"
    ALLEY = "alley"
    BRIDGE = "bridge"
    TUNNEL = "tunnel"


class BuildingType(Enum):
    HOUSE = "house"
    SHOP = "shop"
    FACTORY = "factory"
    OFFICE = "office"
    TEMPLE = "temple"
    PALACE = "palace"
    TAVERN = "tavern"
    WAREHOUSE = "warehouse"
    TOWER = "tower"
    BARRACKS = "barracks"


class CityStyle(Enum):
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    INDUSTRIAL = "industrial"
    MODERN = "modern"
    FUTURISTIC = "futuristic"
    FANTASY = "fantasy"


# Mapping from district type to candidate building types and weights.
_DISTRICT_BUILDING_POOL: Dict[DistrictType, List[Tuple[BuildingType, float]]] = {
    DistrictType.RESIDENTIAL: [
        (BuildingType.HOUSE, 0.7),
        (BuildingType.TAVERN, 0.15),
        (BuildingType.SHOP, 0.15),
    ],
    DistrictType.COMMERCIAL: [
        (BuildingType.SHOP, 0.5),
        (BuildingType.OFFICE, 0.25),
        (BuildingType.TAVERN, 0.15),
        (BuildingType.WAREHOUSE, 0.1),
    ],
    DistrictType.INDUSTRIAL: [
        (BuildingType.FACTORY, 0.6),
        (BuildingType.WAREHOUSE, 0.3),
        (BuildingType.HOUSE, 0.1),
    ],
    DistrictType.GOVERNMENT: [
        (BuildingType.OFFICE, 0.5),
        (BuildingType.TOWER, 0.2),
        (BuildingType.HOUSE, 0.3),
    ],
    DistrictType.PARK: [
        (BuildingType.HOUSE, 0.6),
        (BuildingType.TAVERN, 0.2),
        (BuildingType.TEMPLE, 0.2),
    ],
    DistrictType.MILITARY: [
        (BuildingType.BARRACKS, 0.6),
        (BuildingType.TOWER, 0.2),
        (BuildingType.WAREHOUSE, 0.2),
    ],
    DistrictType.SLUM: [
        (BuildingType.HOUSE, 0.85),
        (BuildingType.TAVERN, 0.1),
        (BuildingType.WAREHOUSE, 0.05),
    ],
    DistrictType.NOBLE: [
        (BuildingType.HOUSE, 0.4),
        (BuildingType.TOWER, 0.2),
        (BuildingType.TEMPLE, 0.2),
        (BuildingType.OFFICE, 0.2),
    ],
}

# Style-specific visual property templates applied to buildings.
_STYLE_TEMPLATES: Dict[CityStyle, Dict[str, Any]] = {
    CityStyle.MEDIEVAL: {
        "primary_material": "timber",
        "secondary_material": "thatch",
        "roof_shape": "gabled",
        "color_scheme": ["#6b4f2a", "#8a6a3a", "#3a2a1a"],
        "floor_range": (1, 3),
        "size_range": (4, 9),
    },
    CityStyle.RENAISSANCE: {
        "primary_material": "stone_brick",
        "secondary_material": "slate",
        "roof_shape": "hip",
        "color_scheme": ["#c4a882", "#8a7a5a", "#5a4a3a"],
        "floor_range": (2, 5),
        "size_range": (6, 12),
    },
    CityStyle.INDUSTRIAL: {
        "primary_material": "red_brick",
        "secondary_material": "steel",
        "roof_shape": "flat",
        "color_scheme": ["#7a3a2a", "#4a3a3a", "#3a3a3a"],
        "floor_range": (2, 8),
        "size_range": (6, 14),
    },
    CityStyle.MODERN: {
        "primary_material": "concrete",
        "secondary_material": "glass",
        "roof_shape": "flat",
        "color_scheme": ["#a0a0b0", "#607080", "#3a4a5a"],
        "floor_range": (3, 20),
        "size_range": (8, 18),
    },
    CityStyle.FUTURISTIC: {
        "primary_material": "composite_alloy",
        "secondary_material": "smart_glass",
        "roof_shape": "domed",
        "color_scheme": ["#4a8afa", "#a0c4fa", "#2a3a5a"],
        "floor_range": (5, 60),
        "size_range": (8, 22),
    },
    CityStyle.FANTASY: {
        "primary_material": "white_stone",
        "secondary_material": "magical_crystal",
        "roof_shape": "spired",
        "color_scheme": ["#e8e0d0", "#c4b898", "#8a7a5a"],
        "floor_range": (2, 8),
        "size_range": (6, 14),
    },
}

# Landmark building templates with default sizes and property sets.
_LANDMARK_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "palace": {
        "building_type": BuildingType.PALACE,
        "size": {"width": 30, "height": 30},
        "floors": 5,
        "properties": {"role": "seat_of_power", "garrison": True, "treasury": True},
    },
    "temple": {
        "building_type": BuildingType.TEMPLE,
        "size": {"width": 18, "height": 18},
        "floors": 2,
        "properties": {"role": "worship", "shrine": True, "pilgrimage_site": True},
    },
    "market_square": {
        "building_type": BuildingType.SHOP,
        "size": {"width": 24, "height": 24},
        "floors": 1,
        "properties": {"role": "commerce", "open_air": True, "stall_count": 24},
    },
    "barracks": {
        "building_type": BuildingType.BARRACKS,
        "size": {"width": 20, "height": 16},
        "floors": 2,
        "properties": {"role": "garrison", "training_yard": True, "armory": True},
    },
    "watchtower": {
        "building_type": BuildingType.TOWER,
        "size": {"width": 8, "height": 8},
        "floors": 6,
        "properties": {"role": "surveillance", "beacon": True, "garrison": True},
    },
    "warehouse": {
        "building_type": BuildingType.WAREHOUSE,
        "size": {"width": 22, "height": 14},
        "floors": 1,
        "properties": {"role": "storage", "dock_access": False, "capacity": 1000},
    },
}


@dataclass
class RoadSegment:
    road_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    road_type: RoadType = RoadType.STREET
    start_pos: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    end_pos: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    width: float = 4.0
    length: float = 0.0
    connected_districts: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "road_id": self.road_id,
            "road_type": self.road_type.value,
            "start_pos": dict(self.start_pos),
            "end_pos": dict(self.end_pos),
            "width": self.width,
            "length": self.length,
            "connected_districts": list(self.connected_districts),
            "created_at": self.created_at,
        }


@dataclass
class Building:
    building_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    building_type: BuildingType = BuildingType.HOUSE
    district_id: str = ""
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    size: Dict[str, float] = field(default_factory=lambda: {"width": 6.0, "height": 6.0})
    floors: int = 1
    properties: Dict[str, Any] = field(default_factory=dict)
    style: CityStyle = CityStyle.MEDIEVAL
    is_landmark: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "building_id": self.building_id,
            "building_type": self.building_type.value,
            "district_id": self.district_id,
            "position": dict(self.position),
            "size": dict(self.size),
            "floors": self.floors,
            "properties": dict(self.properties),
            "style": self.style.value,
            "is_landmark": self.is_landmark,
            "created_at": self.created_at,
        }


@dataclass
class District:
    district_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    district_type: DistrictType = DistrictType.RESIDENTIAL
    name: str = ""
    bounds: Dict[str, float] = field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}
    )
    buildings: List[str] = field(default_factory=list)
    population_density: float = 0.5
    wealth_level: float = 0.5
    connected_roads: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "district_id": self.district_id,
            "district_type": self.district_type.value,
            "name": self.name,
            "bounds": dict(self.bounds),
            "buildings": list(self.buildings),
            "population_density": self.population_density,
            "wealth_level": self.wealth_level,
            "connected_roads": list(self.connected_roads),
            "created_at": self.created_at,
        }


@dataclass
class CityLayout:
    city_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    style: CityStyle = CityStyle.MEDIEVAL
    bounds: Dict[str, float] = field(
        default_factory=lambda: {"width": 512.0, "height": 512.0}
    )
    districts: Dict[str, District] = field(default_factory=dict)
    roads: Dict[str, RoadSegment] = field(default_factory=dict)
    buildings: Dict[str, Building] = field(default_factory=dict)
    center: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    generated_at: float = field(default_factory=_time_module.time)
    seed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "city_id": self.city_id,
            "name": self.name,
            "style": self.style.value,
            "bounds": dict(self.bounds),
            "districts": {k: v.to_dict() for k, v in self.districts.items()},
            "roads": {k: v.to_dict() for k, v in self.roads.items()},
            "buildings": {k: v.to_dict() for k, v in self.buildings.items()},
            "center": dict(self.center),
            "generated_at": self.generated_at,
            "seed": self.seed,
            "metadata": dict(self.metadata),
        }


@dataclass
class CityGenerationConfig:
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    style: CityStyle = CityStyle.MEDIEVAL
    target_population: int = 5000
    min_districts: int = 4
    max_districts: int = 12
    road_density: float = 0.5
    building_density: float = 0.6
    has_walls: bool = False
    has_river: bool = False
    has_port: bool = False
    seed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "style": self.style.value,
            "target_population": self.target_population,
            "min_districts": self.min_districts,
            "max_districts": self.max_districts,
            "road_density": self.road_density,
            "building_density": self.building_density,
            "has_walls": self.has_walls,
            "has_river": self.has_river,
            "has_port": self.has_port,
            "seed": self.seed,
        }


class ProceduralCityEngine:
    """
    Procedural city generation engine.

    Generates complete urban layouts from a deterministic seed by
    composing a hierarchical road network, district partitioning,
    building placement, and landmark insertion. Thread-safe through
    a re-entrant lock guarding singleton creation and mutable state.
    """

    _instance: Optional["ProceduralCityEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "ProceduralCityEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._cities: Dict[str, CityLayout] = {}
        self._districts: Dict[str, District] = {}
        self._buildings: Dict[str, Building] = {}
        self._roads: Dict[str, RoadSegment] = {}
        # Reverse indexes for fast lookup by city.
        self._city_districts: Dict[str, List[str]] = {}
        self._city_buildings: Dict[str, List[str]] = {}
        self._city_roads: Dict[str, List[str]] = {}
        self._district_buildings: Dict[str, List[str]] = {}
        # Lifetime counters for stats reporting.
        self._total_cities_generated: int = 0
        self._total_districts_created: int = 0
        self._total_buildings_placed: int = 0
        self._total_roads_laid: int = 0
        self._total_landmarks_placed: int = 0

    # ---- Public API ----

    def generate_city(
        self,
        name: str = "",
        style: Optional[CityStyle] = None,
        config: Optional[CityGenerationConfig] = None,
    ) -> CityLayout:
        """
        Generate a complete procedural city.

        Orchestrates the full pipeline: seed resolution, road network
        generation, district partitioning, building placement, landmark
        insertion, and optional wall/river/port features. The result is
        stored and returned.
        """
        cfg = config or CityGenerationConfig()
        if style is not None:
            cfg.style = style

        seed = cfg.seed if cfg.seed else random.randint(1, 999999)
        rng = random.Random(seed)

        city_style = cfg.style
        bounds_width, bounds_height = self._compute_city_bounds(cfg)
        center = {"x": bounds_width / 2.0, "y": bounds_height / 2.0}

        city_layout = CityLayout(
            name=name or f"city_{seed}",
            style=city_style,
            bounds={"width": bounds_width, "height": bounds_height},
            center=center,
            seed=seed,
            generated_at=_time_module.time(),
            metadata={
                "config": cfg.to_dict(),
                "has_walls": cfg.has_walls,
                "has_river": cfg.has_river,
                "has_port": cfg.has_port,
            },
        )

        # Step 1: lay down the hierarchical road network.
        roads = self.generate_road_network(city_layout, cfg)
        for road in roads:
            city_layout.roads[road.road_id] = road
            self._roads[road.road_id] = road
        self._city_roads[city_layout.city_id] = [r.road_id for r in roads]
        self._total_roads_laid += len(roads)

        # Step 2: partition the area into districts using the road grid.
        districts = self.generate_districts(city_layout, cfg)
        for district in districts:
            city_layout.districts[district.district_id] = district
            self._districts[district.district_id] = district
            self._district_buildings[district.district_id] = []
        self._city_districts[city_layout.city_id] = [d.district_id for d in districts]
        self._total_districts_created += len(districts)

        # Bind roads to the districts they touch so connectivity is queryable.
        self._bind_roads_to_districts(city_layout)

        # Step 3: populate each district with buildings.
        for district in districts:
            buildings = self.generate_buildings(district, city_style)
            for building in buildings:
                city_layout.buildings[building.building_id] = building
                self._buildings[building.building_id] = building
                district.buildings.append(building.building_id)
                self._district_buildings.setdefault(district.district_id, []).append(
                    building.building_id
                )
            self._total_buildings_placed += len(buildings)

        all_building_ids = list(city_layout.buildings.keys())
        self._city_buildings[city_layout.city_id] = all_building_ids

        # Step 4: place landmarks at strategic positions.
        self._place_default_landmarks(city_layout, rng)

        # Step 5: optional walls, river, and port features.
        if cfg.has_walls:
            self._add_city_walls(city_layout, rng)
        if cfg.has_river:
            self._add_river_crossing(city_layout, rng)
        if cfg.has_port:
            self._add_port_district(city_layout, rng)

        # Step 6: finalize metadata with summary stats.
        city_layout.metadata["district_count"] = len(city_layout.districts)
        city_layout.metadata["road_count"] = len(city_layout.roads)
        city_layout.metadata["building_count"] = len(city_layout.buildings)
        city_layout.metadata["landmark_count"] = sum(
            1 for b in city_layout.buildings.values() if b.is_landmark
        )

        self._cities[city_layout.city_id] = city_layout
        self._total_cities_generated += 1
        return city_layout

    def generate_road_network(
        self, city_layout: CityLayout, config: CityGenerationConfig
    ) -> List[RoadSegment]:
        """
        Generate a hierarchical road network.

        Produces four tiers of roads:
          1. Highways radiating from the city center to each edge.
          2. Main roads forming a concentric ring plus a coarse grid.
          3. Streets filling in the grid blocks at a finer resolution.
          4. Alleys as short narrow passages inside larger blocks.
        """
        rng = random.Random(city_layout.seed)
        width = city_layout.bounds["width"]
        height = city_layout.bounds["height"]
        cx, cy = city_layout.center["x"], city_layout.center["y"]

        roads: List[RoadSegment] = []

        # Tier 1: radial highways from center to each cardinal edge.
        edge_points = [
            {"x": 0.0, "y": cy},
            {"x": width, "y": cy},
            {"x": cx, "y": 0.0},
            {"x": cx, "y": height},
        ]
        # Diagonal highways added with probability tied to road density.
        if rng.random() < 0.4 + config.road_density * 0.4:
            edge_points.extend([
                {"x": 0.0, "y": 0.0},
                {"x": width, "y": 0.0},
                {"x": 0.0, "y": height},
                {"x": width, "y": height},
            ])

        for endpoint in edge_points:
            road = self._make_road(
                RoadType.HIGHWAY,
                {"x": cx, "y": cy},
                endpoint,
                width=10.0,
            )
            roads.append(road)

        # Tier 2: concentric ring roads around the center.
        ring_count = max(1, int(2 + config.road_density * 3))
        max_radius = min(width, height) * 0.45
        for ring_idx in range(1, ring_count + 1):
            radius = (ring_idx / ring_count) * max_radius
            segments = self._make_ring_road(cx, cy, radius, rng)
            for seg in segments:
                seg.road_type = RoadType.MAIN_ROAD
                seg.width = 7.0
                roads.append(seg)

        # Tier 2 (cont): coarse grid of main roads aligned to the bounds.
        grid_step = max(
            40.0,
            min(width, height) / (3.0 + config.road_density * 4.0),
        )
        grid_roads = self._make_grid_roads(width, height, grid_step, RoadType.MAIN_ROAD, 6.0)
        roads.extend(grid_roads)

        # Tier 3: streets filling in each grid cell at a finer step.
        street_step = max(12.0, grid_step / max(2.0, 2.5 - config.road_density))
        street_roads = self._make_grid_roads(width, height, street_step, RoadType.STREET, 3.5)
        # Subsample streets based on density to avoid over-saturation.
        keep_chance = 0.4 + config.road_density * 0.5
        streets = [r for r in street_roads if rng.random() < keep_chance]
        roads.extend(streets)

        # Tier 4: alleys as short narrow passages inside large blocks.
        alley_count = int(config.road_density * 40)
        for _ in range(alley_count):
            ax = rng.uniform(grid_step, width - grid_step)
            ay = rng.uniform(grid_step, height - grid_step)
            length = rng.uniform(6.0, 14.0)
            horizontal = rng.random() < 0.5
            end = (
                {"x": ax + length, "y": ay}
                if horizontal
                else {"x": ax, "y": ay + length}
            )
            alley = self._make_road(
                RoadType.ALLEY,
                {"x": ax, "y": ay},
                end,
                width=2.0,
            )
            roads.append(alley)

        # Optional river adds a bridge crossing where it intersects a main road.
        if config.has_river:
            bridge = self._make_road(
                RoadType.BRIDGE,
                {"x": 0.0, "y": cy + rng.uniform(-height * 0.1, height * 0.1)},
                {"x": width, "y": cy + rng.uniform(-height * 0.1, height * 0.1)},
                width=8.0,
            )
            roads.append(bridge)

        return roads

    def generate_districts(
        self, city_layout: CityLayout, config: CityGenerationConfig
    ) -> List[District]:
        """
        Partition the city area into districts using a grid derived from
        the road network, then assign each district a type based on its
        distance from the center and a deterministic roll.
        """
        rng = random.Random(city_layout.seed + 17)
        width = city_layout.bounds["width"]
        height = city_layout.bounds["height"]
        cx, cy = city_layout.center["x"], city_layout.center["y"]

        # District grid resolution driven by config bounds.
        target_count = rng.randint(config.min_districts, config.max_districts)
        cols = max(2, int(round(math.sqrt(target_count * width / max(height, 1.0)))))
        rows = max(2, int(round(target_count / cols)))
        cell_w = width / cols
        cell_h = height / rows

        districts: List[District] = []
        for row in range(rows):
            for col in range(cols):
                x = col * cell_w
                y = row * cell_h
                # Distance from cell center to city center, normalized.
                cell_cx = x + cell_w / 2.0
                cell_cy = y + cell_h / 2.0
                dist = math.hypot(cell_cx - cx, cell_cy - cy)
                max_dist = math.hypot(cx, cy)
                norm_dist = dist / max_dist if max_dist > 0 else 0.0

                district_type = self._pick_district_type(norm_dist, rng)
                wealth = self._wealth_for_district(district_type, norm_dist, rng)
                population = self._population_for_district(district_type, wealth, rng)

                district = District(
                    district_type=district_type,
                    name=self._name_district(district_type, row, col, rng),
                    bounds={
                        "x": x,
                        "y": y,
                        "width": cell_w,
                        "height": cell_h,
                    },
                    population_density=population,
                    wealth_level=wealth,
                )
                districts.append(district)

        # Guarantee at least one government and one noble district near center.
        self._ensure_central_districts(districts, cx, cy, rng)

        return districts

    def generate_buildings(
        self, district: District, style: CityStyle
    ) -> List[Building]:
        """
        Populate a district with buildings. Building type is sampled from
        the district pool, size and floor count scale with wealth, and
        positions are scattered on a sub-grid to avoid overlap with each
        other and with the district boundary.
        """
        rng = random.Random(hash(district.district_id) & 0xFFFFFFFF)
        template = _STYLE_TEMPLATES.get(style, _STYLE_TEMPLATES[CityStyle.MEDIEVAL])
        pool = _DISTRICT_BUILDING_POOL.get(
            district.district_type, _DISTRICT_BUILDING_POOL[DistrictType.RESIDENTIAL]
        )

        bounds = district.bounds
        # Reserve margin so buildings stay clear of the district border
        # (which is typically where roads run).
        margin = 4.0
        usable_w = max(8.0, bounds["width"] - 2 * margin)
        usable_h = max(8.0, bounds["height"] - 2 * margin)

        # Number of buildings scales with district area and density.
        area = usable_w * usable_h
        base_count = int(area / 80.0)
        count = max(2, int(base_count * (0.5 + district.population_density)))

        floor_min, floor_max = template["floor_range"]
        size_min, size_max = template["size_range"]

        buildings: List[Building] = []
        occupied: List[Tuple[float, float, float, float]] = []

        attempts = 0
        max_attempts = count * 8
        while len(buildings) < count and attempts < max_attempts:
            attempts += 1
            building_type = rng.choices(
                [b[0] for b in pool],
                weights=[b[1] for b in pool],
                k=1,
            )[0]

            # Wealth scales the upper bound of size and floors.
            wealth_factor = 0.5 + district.wealth_level
            size_cap = min(size_max, size_min + (size_max - size_min) * wealth_factor)
            floor_cap = min(floor_max, floor_min + (floor_max - floor_min) * wealth_factor)

            bw = rng.uniform(size_min, max(size_min + 1, size_cap))
            bh = rng.uniform(size_min, max(size_min + 1, size_cap))
            bx = bounds["x"] + margin + rng.uniform(0.0, max(0.0, usable_w - bw))
            by = bounds["y"] + margin + rng.uniform(0.0, max(0.0, usable_h - bh))

            # Reject placement if it overlaps an existing building footprint.
            if self._overlaps_any(bx, by, bw, bh, occupied):
                continue

            floors = max(floor_min, int(rng.uniform(floor_min, max(floor_min + 1, floor_cap))))
            building = Building(
                building_type=building_type,
                district_id=district.district_id,
                position={"x": round(bx, 2), "y": round(by, 2)},
                size={"width": round(bw, 2), "height": round(bh, 2)},
                floors=floors,
                properties=self._building_properties(building_type, template, district),
                style=style,
            )
            buildings.append(building)
            occupied.append((bx, by, bw, bh))

        return buildings

    def place_landmark(
        self,
        city_layout: CityLayout,
        landmark_type: str,
        position: Dict[str, float],
    ) -> Building:
        """
        Place a named landmark building at the requested position. The
        landmark is registered in the city layout and tagged so it can
        be filtered from regular buildings.
        """
        template = _LANDMARK_TEMPLATES.get(landmark_type)
        if template is None:
            raise ValueError(f"Unknown landmark type: {landmark_type}")

        # Find the district containing the position so the landmark can
        # be associated with it.
        host_district_id = ""
        for district in city_layout.districts.values():
            b = district.bounds
            if (
                b["x"] <= position["x"] <= b["x"] + b["width"]
                and b["y"] <= position["y"] <= b["y"] + b["height"]
            ):
                host_district_id = district.district_id
                break

        building = Building(
            building_type=template["building_type"],
            district_id=host_district_id,
            position={"x": float(position["x"]), "y": float(position["y"])},
            size=dict(template["size"]),
            floors=template["floors"],
            properties=dict(template["properties"]),
            style=city_layout.style,
            is_landmark=True,
        )

        city_layout.buildings[building.building_id] = building
        self._buildings[building.building_id] = building
        self._city_buildings.setdefault(city_layout.city_id, []).append(
            building.building_id
        )
        if host_district_id:
            host_district = city_layout.districts.get(host_district_id)
            if host_district is not None:
                host_district.buildings.append(building.building_id)
            self._district_buildings.setdefault(host_district_id, []).append(
                building.building_id
            )

        self._total_landmarks_placed += 1
        return building

    def get_city(self, city_id: str) -> Optional[CityLayout]:
        return self._cities.get(city_id)

    def get_district(self, city_id: str, district_id: str) -> Optional[District]:
        city = self._cities.get(city_id)
        if city is None:
            return None
        return city.districts.get(district_id)

    def get_buildings_in_district(
        self, city_id: str, district_id: str
    ) -> List[Building]:
        city = self._cities.get(city_id)
        if city is None:
            return []
        district = city.districts.get(district_id)
        if district is None:
            return []
        result: List[Building] = []
        for building_id in district.buildings:
            building = city.buildings.get(building_id)
            if building is not None:
                result.append(building)
        return result

    def get_road_network(self, city_id: str) -> List[RoadSegment]:
        city = self._cities.get(city_id)
        if city is None:
            return []
        return list(city.roads.values())

    def analyze_city(self, city_id: str) -> Dict[str, Any]:
        """
        Analyze a city layout and return metrics covering density,
        connectivity, and district balance.
        """
        city = self._cities.get(city_id)
        if city is None:
            return {"error": "city_not_found", "city_id": city_id}

        total_area = city.bounds["width"] * city.bounds["height"]
        building_count = len(city.buildings)
        road_count = len(city.roads)
        district_count = len(city.districts)

        # Density metrics.
        building_footprint = sum(
            b.size["width"] * b.size["height"] for b in city.buildings.values()
        )
        building_density = (
            building_footprint / total_area if total_area > 0 else 0.0
        )
        road_length_total = sum(r.length for r in city.roads.values())
        road_density = road_length_total / max(total_area, 1.0)

        # Connectivity metrics derived from the district-road bipartite graph.
        district_degrees = [len(d.connected_roads) for d in city.districts.values()]
        avg_connectivity = (
            sum(district_degrees) / len(district_degrees)
            if district_degrees
            else 0.0
        )
        max_connectivity = max(district_degrees) if district_degrees else 0
        min_connectivity = min(district_degrees) if district_degrees else 0

        # District balance: distribution of district types and wealth spread.
        type_counts: Dict[str, int] = {}
        wealth_values: List[float] = []
        population_values: List[float] = []
        for district in city.districts.values():
            type_counts[district.district_type.value] = (
                type_counts.get(district.district_type.value, 0) + 1
            )
            wealth_values.append(district.wealth_level)
            population_values.append(district.population_density)

        wealth_spread = (
            max(wealth_values) - min(wealth_values) if wealth_values else 0.0
        )
        avg_wealth = sum(wealth_values) / len(wealth_values) if wealth_values else 0.0
        avg_population = (
            sum(population_values) / len(population_values)
            if population_values
            else 0.0
        )

        # Landmark distribution.
        landmark_types: Dict[str, int] = {}
        for building in city.buildings.values():
            if building.is_landmark:
                key = building.building_type.value
                landmark_types[key] = landmark_types.get(key, 0) + 1

        # Road type distribution.
        road_type_counts: Dict[str, int] = {}
        for road in city.roads.values():
            road_type_counts[road.road_type.value] = (
                road_type_counts.get(road.road_type.value, 0) + 1
            )

        return {
            "city_id": city.city_id,
            "name": city.name,
            "style": city.style.value,
            "area": round(total_area, 2),
            "district_count": district_count,
            "building_count": building_count,
            "road_count": road_count,
            "density": {
                "building_density": round(building_density, 4),
                "road_density": round(road_density, 4),
                "avg_population_density": round(avg_population, 4),
            },
            "connectivity": {
                "avg_district_connections": round(avg_connectivity, 2),
                "max_district_connections": max_connectivity,
                "min_district_connections": min_connectivity,
                "total_road_length": round(road_length_total, 2),
            },
            "balance": {
                "district_type_counts": type_counts,
                "wealth_spread": round(wealth_spread, 4),
                "avg_wealth": round(avg_wealth, 4),
                "landmark_counts": landmark_types,
            },
            "road_type_counts": road_type_counts,
        }

    def list_cities(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for city in self._cities.values():
            result.append({
                "city_id": city.city_id,
                "name": city.name,
                "style": city.style.value,
                "seed": city.seed,
                "district_count": len(city.districts),
                "building_count": len(city.buildings),
                "road_count": len(city.roads),
                "generated_at": city.generated_at,
            })
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_cities_generated": self._total_cities_generated,
            "total_districts_created": self._total_districts_created,
            "total_buildings_placed": self._total_buildings_placed,
            "total_roads_laid": self._total_roads_laid,
            "total_landmarks_placed": self._total_landmarks_placed,
            "active_cities": len(self._cities),
            "active_districts": len(self._districts),
            "active_buildings": len(self._buildings),
            "active_roads": len(self._roads),
            "cities_by_style": {
                style.value: sum(
                    1 for c in self._cities.values() if c.style == style
                )
                for style in CityStyle
            },
            "districts_by_type": {
                dt.value: sum(
                    1 for d in self._districts.values() if d.district_type == dt
                )
                for dt in DistrictType
            },
            "buildings_by_type": {
                bt.value: sum(
                    1 for b in self._buildings.values() if b.building_type == bt
                )
                for bt in BuildingType
            },
            "roads_by_type": {
                rt.value: sum(
                    1 for r in self._roads.values() if r.road_type == rt
                )
                for rt in RoadType
            },
        }

    # ---- Internal helpers ----

    def _compute_city_bounds(self, cfg: CityGenerationConfig) -> Tuple[float, float]:
        """Derive city bounds from the target population and config."""
        # Larger populations produce larger city footprints.
        base = 256.0
        scale = math.sqrt(max(cfg.target_population, 100) / 1000.0)
        size = max(base, base * scale)
        size = max(128.0, math.floor(size / 8.0) * 8.0)
        return size, size

    def _make_road(
        self,
        road_type: RoadType,
        start: Dict[str, float],
        end: Dict[str, float],
        width: float,
    ) -> RoadSegment:
        length = math.hypot(end["x"] - start["x"], end["y"] - start["y"])
        return RoadSegment(
            road_type=road_type,
            start_pos={"x": float(start["x"]), "y": float(start["y"])},
            end_pos={"x": float(end["x"]), "y": float(end["y"])},
            width=float(width),
            length=round(length, 2),
        )

    def _make_ring_road(
        self, cx: float, cy: float, radius: float, rng: random.Random
    ) -> List[RoadSegment]:
        """Approximate a ring road with a polygon of segments."""
        segments: List[RoadSegment] = []
        sides = 12
        points: List[Dict[str, float]] = []
        rotation = rng.uniform(0.0, math.pi / sides)
        for i in range(sides):
            angle = rotation + (i / sides) * 2.0 * math.pi
            points.append({
                "x": cx + math.cos(angle) * radius,
                "y": cy + math.sin(angle) * radius,
            })
        for i in range(sides):
            segments.append(
                self._make_road(
                    RoadType.MAIN_ROAD,
                    points[i],
                    points[(i + 1) % sides],
                    width=6.0,
                )
            )
        return segments

    def _make_grid_roads(
        self,
        width: float,
        height: float,
        step: float,
        road_type: RoadType,
        road_width: float,
    ) -> List[RoadSegment]:
        """Build a grid of horizontal and vertical roads covering the bounds."""
        roads: List[RoadSegment] = []
        # Vertical roads.
        x = step
        while x < width:
            roads.append(
                self._make_road(
                    road_type,
                    {"x": x, "y": 0.0},
                    {"x": x, "y": height},
                    width=road_width,
                )
            )
            x += step
        # Horizontal roads.
        y = step
        while y < height:
            roads.append(
                self._make_road(
                    road_type,
                    {"x": 0.0, "y": y},
                    {"x": width, "y": y},
                    width=road_width,
                )
            )
            y += step
        return roads

    def _bind_roads_to_districts(self, city_layout: CityLayout) -> None:
        """Attach road ids to districts whose bounds they cross."""
        for district in city_layout.districts.values():
            b = district.bounds
            for road in city_layout.roads.values():
                if self._road_intersects_bounds(road, b):
                    district.connected_roads.append(road.road_id)
                    road.connected_districts.append(district.district_id)

    def _road_intersects_bounds(
        self, road: RoadSegment, bounds: Dict[str, float]
    ) -> bool:
        """Coarse segment-vs-rectangle intersection test."""
        x1, y1 = road.start_pos["x"], road.start_pos["y"]
        x2, y2 = road.end_pos["x"], road.end_pos["y"]
        rx, ry = bounds["x"], bounds["y"]
        rw, rh = bounds["width"], bounds["height"]
        # Quick reject using bounding box of the segment.
        seg_min_x = min(x1, x2)
        seg_max_x = max(x1, x2)
        seg_min_y = min(y1, y2)
        seg_max_y = max(y1, y2)
        if seg_max_x < rx or seg_min_x > rx + rw:
            return False
        if seg_max_y < ry or seg_min_y > ry + rh:
            return False
        return True

    def _pick_district_type(
        self, norm_dist: float, rng: random.Random
    ) -> DistrictType:
        """
        Choose a district type based on normalized distance from the
        city center. Central cells lean government/noble; mid-ring
        cells lean commercial/residential; outer cells lean industrial,
        military, slum, or park.
        """
        if norm_dist < 0.25:
            choices = [
                (DistrictType.GOVERNMENT, 0.4),
                (DistrictType.NOBLE, 0.3),
                (DistrictType.COMMERCIAL, 0.2),
                (DistrictType.PARK, 0.1),
            ]
        elif norm_dist < 0.55:
            choices = [
                (DistrictType.COMMERCIAL, 0.4),
                (DistrictType.RESIDENTIAL, 0.35),
                (DistrictType.NOBLE, 0.1),
                (DistrictType.PARK, 0.15),
            ]
        elif norm_dist < 0.8:
            choices = [
                (DistrictType.RESIDENTIAL, 0.5),
                (DistrictType.INDUSTRIAL, 0.2),
                (DistrictType.MILITARY, 0.15),
                (DistrictType.SLUM, 0.15),
            ]
        else:
            choices = [
                (DistrictType.INDUSTRIAL, 0.35),
                (DistrictType.SLUM, 0.25),
                (DistrictType.MILITARY, 0.2),
                (DistrictType.RESIDENTIAL, 0.2),
            ]
        return rng.choices(
            [c[0] for c in choices], weights=[c[1] for c in choices], k=1
        )[0]

    def _wealth_for_district(
        self,
        district_type: DistrictType,
        norm_dist: float,
        rng: random.Random,
    ) -> float:
        """Compute a wealth level in [0, 1] for a district."""
        base_by_type = {
            DistrictType.NOBLE: 0.9,
            DistrictType.GOVERNMENT: 0.8,
            DistrictType.COMMERCIAL: 0.65,
            DistrictType.RESIDENTIAL: 0.5,
            DistrictType.PARK: 0.55,
            DistrictType.MILITARY: 0.45,
            DistrictType.INDUSTRIAL: 0.35,
            DistrictType.SLUM: 0.15,
        }
        base = base_by_type.get(district_type, 0.5)
        # Wealth tends to drop toward the city outskirts.
        distance_factor = max(0.0, 1.0 - norm_dist * 0.4)
        value = base * distance_factor + rng.uniform(-0.05, 0.05)
        return round(max(0.05, min(1.0, value)), 3)

    def _population_for_district(
        self,
        district_type: DistrictType,
        wealth: float,
        rng: random.Random,
    ) -> float:
        """Compute a population density in [0, 1] for a district."""
        base_by_type = {
            DistrictType.SLUM: 0.9,
            DistrictType.RESIDENTIAL: 0.75,
            DistrictType.COMMERCIAL: 0.6,
            DistrictType.NOBLE: 0.35,
            DistrictType.GOVERNMENT: 0.4,
            DistrictType.MILITARY: 0.5,
            DistrictType.INDUSTRIAL: 0.45,
            DistrictType.PARK: 0.15,
        }
        base = base_by_type.get(district_type, 0.5)
        value = base + rng.uniform(-0.1, 0.1)
        return round(max(0.05, min(1.0, value)), 3)

    def _name_district(
        self,
        district_type: DistrictType,
        row: int,
        col: int,
        rng: random.Random,
    ) -> str:
        """Produce a deterministic, themed name for a district."""
        prefixes = {
            DistrictType.RESIDENTIAL: ["Old", "Quiet", "Sunken", "Hillside", "Eastgate"],
            DistrictType.COMMERCIAL: ["Market", "Trade", "Merchant", "Coin", "Guildhall"],
            DistrictType.INDUSTRIAL: ["Smoke", "Forge", "Iron", "Soot", "Bellows"],
            DistrictType.GOVERNMENT: ["Crown", "Magistrate", "Council", "Hall", "Judicial"],
            DistrictType.PARK: ["Green", "Garden", "Verdant", "Meadow", "Olive"],
            DistrictType.MILITARY: ["Garrison", "Sentinel", "Bastion", "Drill", "Watch"],
            DistrictType.SLUM: ["Mire", "Rook", "Ashen", "Tangle", "Flood"],
            DistrictType.NOBLE: ["High", "Silver", "Gilded", "Lace", "Marble"],
        }
        suffixes = ["Quarter", "Ward", "District", "Reach", "Ends"]
        prefix = rng.choice(prefixes.get(district_type, ["Inner"]))
        suffix = rng.choice(suffixes)
        return f"{prefix} {suffix}"

    def _ensure_central_districts(
        self,
        districts: List[District],
        cx: float,
        cy: float,
        rng: random.Random,
    ) -> None:
        """Guarantee at least one government and one noble district near center."""
        if not districts:
            return
        # Sort by distance to center.
        sorted_districts = sorted(
            districts,
            key=lambda d: math.hypot(
                d.bounds["x"] + d.bounds["width"] / 2.0 - cx,
                d.bounds["y"] + d.bounds["height"] / 2.0 - cy,
            ),
        )
        # Force the closest district to be government if none exists.
        if not any(d.district_type == DistrictType.GOVERNMENT for d in districts):
            sorted_districts[0].district_type = DistrictType.GOVERNMENT
            sorted_districts[0].wealth_level = max(sorted_districts[0].wealth_level, 0.8)
            sorted_districts[0].name = self._name_district(
                DistrictType.GOVERNMENT, 0, 0, rng
            )
        # Force the second closest to be noble if none exists.
        if not any(d.district_type == DistrictType.NOBLE for d in districts):
            if len(sorted_districts) > 1:
                sorted_districts[1].district_type = DistrictType.NOBLE
                sorted_districts[1].wealth_level = max(
                    sorted_districts[1].wealth_level, 0.85
                )
                sorted_districts[1].name = self._name_district(
                    DistrictType.NOBLE, 0, 1, rng
                )

    def _building_properties(
        self,
        building_type: BuildingType,
        template: Dict[str, Any],
        district: District,
    ) -> Dict[str, Any]:
        """Assemble the visual and functional properties for a building."""
        props: Dict[str, Any] = {
            "primary_material": template["primary_material"],
            "secondary_material": template["secondary_material"],
            "roof_shape": template["roof_shape"],
            "color_scheme": list(template["color_scheme"]),
            "district_wealth": district.wealth_level,
        }
        if building_type == BuildingType.SHOP:
            props["trade_goods"] = "general"
            props["has_storage"] = True
        elif building_type == BuildingType.TAVERN:
            props["has_inn"] = True
            props["rooms"] = 4
        elif building_type == BuildingType.FACTORY:
            props["chimney_count"] = 2
            props["power_source"] = "steam"
        elif building_type == BuildingType.WAREHOUSE:
            props["capacity"] = 500
            props["loading_dock"] = True
        elif building_type == BuildingType.TOWER:
            props["height_bonus"] = True
            props["observation_deck"] = True
        elif building_type == BuildingType.BARRACKS:
            props["garrison_size"] = 50
            props["armory"] = True
        elif building_type == BuildingType.TEMPLE:
            props["shrine"] = True
            props["open_to_public"] = True
        elif building_type == BuildingType.HOUSE:
            props["occupants"] = 4
        return props

    def _overlaps_any(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        occupied: List[Tuple[float, float, float, float]],
    ) -> bool:
        """Axis-aligned overlap test against a list of footprints."""
        for ox, oy, ow, oh in occupied:
            if (
                x < ox + ow
                and x + w > ox
                and y < oy + oh
                and y + h > oy
            ):
                return True
        return False

    def _place_default_landmarks(
        self, city_layout: CityLayout, rng: random.Random
    ) -> None:
        """Place the default set of landmarks for a freshly generated city."""
        cx = city_layout.center["x"]
        cy = city_layout.center["y"]
        width = city_layout.bounds["width"]
        height = city_layout.bounds["height"]

        # Palace near the center.
        self.place_landmark(
            city_layout,
            "palace",
            {
                "x": cx + rng.uniform(-width * 0.05, width * 0.05),
                "y": cy + rng.uniform(-height * 0.05, height * 0.05),
            },
        )

        # Temple offset from the palace.
        self.place_landmark(
            city_layout,
            "temple",
            {
                "x": cx + rng.uniform(width * 0.05, width * 0.15),
                "y": cy + rng.uniform(-height * 0.15, -height * 0.05),
            },
        )

        # Market square in a commercial-leaning district.
        market_district = self._find_district_by_type(
            city_layout, DistrictType.COMMERCIAL
        ) or self._find_district_by_type(city_layout, DistrictType.RESIDENTIAL)
        if market_district is not None:
            b = market_district.bounds
            self.place_landmark(
                city_layout,
                "market_square",
                {
                    "x": b["x"] + b["width"] / 2.0,
                    "y": b["y"] + b["height"] / 2.0,
                },
            )

        # Barracks in a military district if present.
        military = self._find_district_by_type(city_layout, DistrictType.MILITARY)
        if military is not None:
            b = military.bounds
            self.place_landmark(
                city_layout,
                "barracks",
                {
                    "x": b["x"] + b["width"] / 2.0,
                    "y": b["y"] + b["height"] / 2.0,
                },
            )

        # Watchtowers near each corner of the city.
        corner_offset = min(width, height) * 0.08
        for corner in [
            {"x": corner_offset, "y": corner_offset},
            {"x": width - corner_offset, "y": corner_offset},
            {"x": corner_offset, "y": height - corner_offset},
            {"x": width - corner_offset, "y": height - corner_offset},
        ]:
            self.place_landmark(city_layout, "watchtower", corner)

    def _find_district_by_type(
        self, city_layout: CityLayout, district_type: DistrictType
    ) -> Optional[District]:
        for district in city_layout.districts.values():
            if district.district_type == district_type:
                return district
        return None

    def _add_city_walls(
        self, city_layout: CityLayout, rng: random.Random
    ) -> None:
        """Trace a rectangular wall circuit and register it as road segments."""
        width = city_layout.bounds["width"]
        height = city_layout.bounds["height"]
        inset = min(width, height) * 0.05
        corners = [
            {"x": inset, "y": inset},
            {"x": width - inset, "y": inset},
            {"x": width - inset, "y": height - inset},
            {"x": inset, "y": height - inset},
        ]
        for i in range(4):
            road = self._make_road(
                RoadType.MAIN_ROAD,
                corners[i],
                corners[(i + 1) % 4],
                width=5.0,
            )
            city_layout.roads[road.road_id] = road
            self._roads[road.road_id] = road
            self._city_roads.setdefault(city_layout.city_id, []).append(road.road_id)
            self._total_roads_laid += 1
        city_layout.metadata["has_walls"] = True

    def _add_river_crossing(
        self, city_layout: CityLayout, rng: random.Random
    ) -> None:
        """Add a river-like road and a tunnel crossing for variety."""
        width = city_layout.bounds["width"]
        height = city_layout.bounds["height"]
        cy = city_layout.center["y"]
        # River runs horizontally across the map.
        river = self._make_road(
            RoadType.MAIN_ROAD,
            {"x": 0.0, "y": cy + rng.uniform(-height * 0.1, height * 0.1)},
            {"x": width, "y": cy + rng.uniform(-height * 0.1, height * 0.1)},
            width=12.0,
        )
        city_layout.roads[river.road_id] = river
        self._roads[river.road_id] = river
        self._city_roads.setdefault(city_layout.city_id, []).append(river.road_id)
        self._total_roads_laid += 1
        # Tunnel under the river along a vertical axis.
        tunnel = self._make_road(
            RoadType.TUNNEL,
            {"x": city_layout.center["x"], "y": 0.0},
            {"x": city_layout.center["x"], "y": height},
            width=6.0,
        )
        city_layout.roads[tunnel.road_id] = tunnel
        self._roads[tunnel.road_id] = tunnel
        self._city_roads.setdefault(city_layout.city_id, []).append(tunnel.road_id)
        self._total_roads_laid += 1
        city_layout.metadata["has_river"] = True

    def _add_port_district(
        self, city_layout: CityLayout, rng: random.Random
    ) -> None:
        """Add a port-side warehouse landmark and a quay road along an edge."""
        width = city_layout.bounds["width"]
        height = city_layout.bounds["height"]
        # Place the port on the bottom edge.
        port_x = rng.uniform(width * 0.2, width * 0.8)
        port_y = height - min(width, height) * 0.05
        self.place_landmark(
            city_layout,
            "warehouse",
            {"x": port_x, "y": port_y},
        )
        quay = self._make_road(
            RoadType.MAIN_ROAD,
            {"x": width * 0.1, "y": port_y},
            {"x": width * 0.9, "y": port_y},
            width=8.0,
        )
        city_layout.roads[quay.road_id] = quay
        self._roads[quay.road_id] = quay
        self._city_roads.setdefault(city_layout.city_id, []).append(quay.road_id)
        self._total_roads_laid += 1
        city_layout.metadata["has_port"] = True


# Module-level accessor
_procedural_city_engine: Optional[ProceduralCityEngine] = None


def get_procedural_city_engine() -> ProceduralCityEngine:
    global _procedural_city_engine
    if _procedural_city_engine is None:
        _procedural_city_engine = ProceduralCityEngine()
    return _procedural_city_engine
