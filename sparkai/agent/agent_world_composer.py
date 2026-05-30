"""
SparkLabs Agent - World Composer

A singleton system for AI-driven procedural world generation. Composes
entire game worlds — terrain, biomes, ecosystems, settlements, and
traversal routes — from high-level semantic descriptions and design
constraints.

Architecture:
  WorldComposer (singleton)
    |-- BiomeTemplate (climate, flora, fauna, terrain style definition)
    |-- TerrainLayer (elevation, moisture, temperature raster datasheet)
    |-- WorldRegion (named sub-region with biome, settlements, routes)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class TerrainCategory(Enum):
    OCEAN = "ocean"
    BEACH = "beach"
    PLAINS = "plains"
    HILLS = "hills"
    MOUNTAIN = "mountain"
    PLATEAU = "plateau"
    VALLEY = "valley"
    CANYON = "canyon"
    SWAMP = "swamp"


class ClimateZone(Enum):
    TROPICAL = "tropical"
    ARID = "arid"
    TEMPERATE = "temperate"
    BOREAL = "boreal"
    POLAR = "polar"
    MEDITERRANEAN = "mediterranean"


class SettlementType(Enum):
    VILLAGE = "village"
    TOWN = "town"
    CITY = "city"
    FORTRESS = "fortress"
    OUTPOST = "outpost"
    RUINS = "ruins"
    NOMADIC_CAMP = "nomadic_camp"
    PORT = "port"


class RouteCategory(Enum):
    TRADE_ROAD = "trade_road"
    RIVER_PATH = "river_path"
    MOUNTAIN_PASS = "mountain_pass"
    COASTAL_ROUTE = "coastal_route"
    SECRET_PATH = "secret_path"


class WorldSize(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EPIC = "epic"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class BiomeTemplate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    climate: ClimateZone = ClimateZone.TEMPERATE
    terrain_categories: List[str] = field(default_factory=list)
    flora_density: float = 0.5
    fauna_density: float = 0.5
    elevation_range: Tuple[float, float] = (0.0, 0.3)
    moisture_range: Tuple[float, float] = (0.3, 0.7)
    temperature_range: Tuple[float, float] = (0.0, 30.0)
    dominant_flora: List[str] = field(default_factory=list)
    dominant_fauna: List[str] = field(default_factory=list)
    color_palette: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "climate": self.climate.value,
            "terrain_categories": list(self.terrain_categories),
            "flora_density": self.flora_density,
            "fauna_density": self.fauna_density,
            "elevation_range": list(self.elevation_range),
            "moisture_range": list(self.moisture_range),
            "temperature_range": list(self.temperature_range),
            "dominant_flora": list(self.dominant_flora),
            "dominant_fauna": list(self.dominant_fauna),
            "color_palette": list(self.color_palette),
            "metadata": dict(self.metadata),
        }


@dataclass
class TerrainLayer:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    width: int = 256
    height: int = 256
    elevation_grid: List[List[float]] = field(default_factory=list)
    moisture_grid: List[List[float]] = field(default_factory=list)
    temperature_grid: List[List[float]] = field(default_factory=list)
    terrain_type_grid: List[List[str]] = field(default_factory=list)
    seed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "grid_size": f"{self.width}x{self.height}",
        }


@dataclass
class WorldRegion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    biome: Optional[BiomeTemplate] = None
    terrain_layer: Optional[TerrainLayer] = None
    settlements: List[Dict[str, Any]] = field(default_factory=list)
    routes: List[Dict[str, Any]] = field(default_factory=list)
    position: Tuple[float, float] = (0.0, 0.0)
    radius: float = 100.0
    population: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "biome": self.biome.to_dict() if self.biome else None,
            "terrain_layer": self.terrain_layer.to_dict() if self.terrain_layer else None,
            "settlements": list(self.settlements),
            "routes": list(self.routes),
            "position": list(self.position),
            "radius": self.radius,
            "population": self.population,
            "metadata": dict(self.metadata),
        }


@dataclass
class WorldBlueprint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    world_size: WorldSize = WorldSize.MEDIUM
    regions: List[WorldRegion] = field(default_factory=list)
    biome_templates: List[BiomeTemplate] = field(default_factory=list)
    seed: int = field(default_factory=lambda: random.randint(0, 999999))
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "world_size": self.world_size.value,
            "regions": [r.to_dict() for r in self.regions],
            "biome_templates": [b.to_dict() for b in self.biome_templates],
            "seed": self.seed,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

DEFAULT_GRID_SIZE: int = 256
BIOME_SIMILARITY_THRESHOLD: float = 0.3
SETTLEMENT_MIN_SPACING: float = 30.0


class WorldComposer:
    """AI-driven procedural world generation and composition system.

    Generates complete game worlds from semantic descriptions. Combines
    terrain generation with biome ecology, settlement placement, route
    networks, and population distribution to create cohesive, playable
    game environments from high-level design intent.
    """

    _instance: Optional[WorldComposer] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> WorldComposer:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> WorldComposer:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._blueprints: List[WorldBlueprint] = []
        self._biome_library: List[BiomeTemplate] = []
        self._terrain_layers: List[TerrainLayer] = []
        self._initialize_preset_biomes()

    def _get_or_create_singleton(self) -> WorldComposer:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        total_regions = sum(len(b.regions) for b in self._blueprints)
        total_settlements = sum(
            len(r.settlements) for b in self._blueprints for r in b.regions
        )
        return {
            "blueprints": len(self._blueprints),
            "total_regions": total_regions,
            "biome_templates": len(self._biome_library),
            "terrain_layers": len(self._terrain_layers),
            "total_settlements": total_settlements,
        }

    # --- World Blueprint Operations ---

    def create_blueprint(
        self,
        name: str,
        description: str = "",
        world_size: str = "medium",
        seed: Optional[int] = None,
    ) -> WorldBlueprint:
        blueprint = WorldBlueprint(
            name=name,
            description=description,
            world_size=WorldSize(world_size),
            seed=seed if seed is not None else random.randint(0, 999999),
        )
        self._blueprints.append(blueprint)
        return blueprint

    def get_blueprint(self, blueprint_id: str) -> Optional[WorldBlueprint]:
        for b in self._blueprints:
            if b.id == blueprint_id:
                return b
        return None

    def list_blueprints(self) -> List[WorldBlueprint]:
        return list(self._blueprints)

    # --- Biome Operations ---

    def create_biome(
        self,
        name: str,
        climate: str = "temperate",
        flora_density: float = 0.5,
        fauna_density: float = 0.5,
        elevation_min: float = 0.0,
        elevation_max: float = 0.3,
        moisture_min: float = 0.3,
        moisture_max: float = 0.7,
    ) -> BiomeTemplate:
        biome = BiomeTemplate(
            name=name,
            climate=ClimateZone(climate),
            flora_density=flora_density,
            fauna_density=fauna_density,
            elevation_range=(elevation_min, elevation_max),
            moisture_range=(moisture_min, moisture_max),
            temperature_range=(10.0, 25.0),
        )
        self._biome_library.append(biome)
        return biome

    def list_biomes(self) -> List[BiomeTemplate]:
        return list(self._biome_library)

    def assign_biome_to_region(
        self,
        blueprint_id: str,
        region_name: str,
        biome_id: str,
    ) -> Optional[WorldRegion]:
        blueprint = self.get_blueprint(blueprint_id)
        if not blueprint:
            return None
        biome = None
        for b in self._biome_library:
            if b.id == biome_id:
                biome = b
                break
        if not biome:
            return None

        region = WorldRegion(name=region_name, biome=biome)
        blueprint.regions.append(region)
        return region

    # --- Terrain Operations ---

    def generate_terrain(
        self,
        name: str,
        width: int = DEFAULT_GRID_SIZE,
        height: int = DEFAULT_GRID_SIZE,
        seed: int = 0,
    ) -> TerrainLayer:
        layer = TerrainLayer(
            name=name,
            width=width,
            height=height,
            seed=seed if seed != 0 else random.randint(0, 999999),
        )
        random.seed(layer.seed)
        layer.elevation_grid = self._generate_noise_grid(width, height, 4, 0.5)
        layer.moisture_grid = self._generate_noise_grid(width, height, 3, 0.4)
        layer.temperature_grid = self._generate_noise_grid(width, height, 2, 0.3)
        layer.terrain_type_grid = self._classify_terrain(
            layer.elevation_grid, layer.moisture_grid, width, height
        )
        self._terrain_layers.append(layer)
        return layer

    def get_terrain_layer(self, layer_id: str) -> Optional[TerrainLayer]:
        for t in self._terrain_layers:
            if t.id == layer_id:
                return t
        return None

    def list_terrain_layers(self) -> List[TerrainLayer]:
        return list(self._terrain_layers)

    # --- Settlement & Route Operations ---

    def place_settlement(
        self,
        blueprint_id: str,
        region_name: str,
        settlement_name: str,
        settlement_type: str = "village",
        pos_x: float = 0.0,
        pos_y: float = 0.0,
        population: int = 100,
    ) -> Optional[Dict[str, Any]]:
        blueprint = self.get_blueprint(blueprint_id)
        if not blueprint:
            return None
        region = self._find_region(blueprint, region_name)
        if not region:
            return None

        settlement = {
            "id": uuid.uuid4().hex,
            "name": settlement_name,
            "type": settlement_type,
            "position": [pos_x, pos_y],
            "population": population,
        }
        region.settlements.append(settlement)
        region.population += population
        return settlement

    def create_route(
        self,
        blueprint_id: str,
        from_region: str,
        to_region: str,
        route_category: str = "trade_road",
    ) -> Optional[Dict[str, Any]]:
        blueprint = self.get_blueprint(blueprint_id)
        if not blueprint:
            return None

        route = {
            "id": uuid.uuid4().hex,
            "from_region": from_region,
            "to_region": to_region,
            "category": route_category,
        }

        for region in blueprint.regions:
            if region.name == from_region or region.name == to_region:
                region.routes.append(route)
        return route

    def compose_world_summary(self, blueprint_id: str) -> Dict[str, Any]:
        blueprint = self.get_blueprint(blueprint_id)
        if not blueprint:
            return {"error": "Blueprint not found"}

        total_population = sum(r.population for r in blueprint.regions)
        total_settlements = sum(len(r.settlements) for r in blueprint.regions)
        total_routes = sum(len(r.routes) for r in blueprint.regions)

        return {
            "name": blueprint.name,
            "description": blueprint.description,
            "world_size": blueprint.world_size.value,
            "seed": blueprint.seed,
            "region_count": len(blueprint.regions),
            "total_population": total_population,
            "total_settlements": total_settlements,
            "total_routes": total_routes // 2,
            "climate_diversity": len(
                set(r.biome.climate.value for r in blueprint.regions if r.biome)
            ),
            "regions": [
                {
                    "name": r.name,
                    "biome": r.biome.name if r.biome else "none",
                    "population": r.population,
                    "settlements": len(r.settlements),
                }
                for r in blueprint.regions
            ],
        }

    # --- Internal ---

    def _initialize_preset_biomes(self) -> None:
        presets = [
            ("Temperate Forest", "temperate", 0.8, 0.7, 0.0, 0.3, 0.4, 0.8),
            ("Tropical Rainforest", "tropical", 0.95, 0.9, 0.0, 0.2, 0.7, 1.0),
            ("Desert", "arid", 0.1, 0.1, 0.0, 0.1, 0.0, 0.2),
            ("Taiga", "boreal", 0.6, 0.4, 0.1, 0.3, 0.3, 0.6),
            ("Tundra", "polar", 0.1, 0.05, 0.0, 0.1, 0.2, 0.4),
            ("Mediterranean Scrub", "mediterranean", 0.4, 0.3, 0.1, 0.4, 0.1, 0.4),
            ("Savanna", "arid", 0.3, 0.5, 0.0, 0.2, 0.2, 0.5),
            ("Swamp", "temperate", 0.7, 0.6, 0.0, 0.1, 0.7, 1.0),
        ]
        for name, climate, flora_d, fauna_d, el_min, el_max, mo_min, mo_max in presets:
            biome = BiomeTemplate(
                name=name,
                climate=ClimateZone(climate),
                flora_density=flora_d,
                fauna_density=fauna_d,
                elevation_range=(el_min, el_max),
                moisture_range=(mo_min, mo_max),
                temperature_range=(5.0, 35.0),
            )
            self._biome_library.append(biome)

        biome_names = [
            "Temperate Forest", "Tropical Rainforest", "Desert", "Taiga",
            "Tundra", "Mediterranean Scrub", "Savanna", "Swamp",
        ]
        fauna_lists = [
            ["deer", "fox", "bear", "owl"],
            ["parrot", "jaguar", "monkey", "frog"],
            ["scorpion", "camel", "lizard", "hawk"],
            ["wolf", "moose", "lynx", "eagle"],
            ["polar_bear", "arctic_fox", "seal", "penguin"],
            ["rabbit", "wildcat", "hawk", "lizard"],
            ["lion", "elephant", "giraffe", "vulture"],
            ["alligator", "heron", "snake", "frog"],
        ]
        for i, name in enumerate(biome_names):
            self._biome_library[i].dominant_fauna = fauna_lists[i]
            self._biome_library[i].dominant_flora = [
                f"{name.lower().replace(' ', '_')}_tree",
                f"{name.lower().replace(' ', '_')}_bush",
                f"{name.lower().replace(' ', '_')}_grass",
            ]

    def _generate_noise_grid(
        self,
        width: int,
        height: int,
        octaves: int,
        persistence: float,
    ) -> List[List[float]]:
        grid: List[List[float]] = []
        for y in range(height):
            row: List[float] = []
            for x in range(width):
                value = 0.0
                amplitude = 1.0
                frequency = 1.0
                max_value = 0.0
                for _ in range(octaves):
                    nx = x / width * frequency
                    ny = y / height * frequency
                    value += amplitude * self._simple_noise(nx, ny)
                    max_value += amplitude
                    amplitude *= persistence
                    frequency *= 2.0
                row.append(value / max(max_value, 0.001))
            grid.append(row)
        return grid

    def _simple_noise(self, x: float, y: float) -> float:
        n = math.sin(x * 12.9898 + y * 78.233) * 43758.5453
        return (n - math.floor(n)) * 2.0 - 1.0

    def _classify_terrain(
        self,
        elevation: List[List[float]],
        moisture: List[List[float]],
        width: int,
        height: int,
    ) -> List[List[str]]:
        grid: List[List[str]] = []
        for y in range(height):
            row: List[str] = []
            for x in range(width):
                e = elevation[y][x]
                m = moisture[y][x]
                if e < 0.1:
                    row.append(TerrainCategory.OCEAN.value)
                elif e < 0.15:
                    row.append(TerrainCategory.BEACH.value)
                elif m > 0.7:
                    row.append(TerrainCategory.SWAMP.value)
                elif e < 0.3:
                    row.append(TerrainCategory.PLAINS.value)
                elif e < 0.5:
                    row.append(TerrainCategory.HILLS.value)
                elif e < 0.65:
                    row.append(TerrainCategory.VALLEY.value)
                elif e < 0.8:
                    row.append(TerrainCategory.PLATEAU.value)
                elif e < 0.9:
                    row.append(TerrainCategory.MOUNTAIN.value)
                else:
                    row.append(TerrainCategory.CANYON.value)
            grid.append(row)
        return grid

    def _find_region(self, blueprint: WorldBlueprint, name: str) -> Optional[WorldRegion]:
        for r in blueprint.regions:
            if r.name == name:
                return r
        return None


def get_world_composer() -> WorldComposer:
    return WorldComposer.get_instance()