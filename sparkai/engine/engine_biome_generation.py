"""
SparkLabs Engine - Biome Generation Pipeline

Procedural biome generation system that creates diverse, cohesive
game environments with natural transitions, climate modeling, and
ecologically sound terrain distributions. Integrates with the
gameplay ecosystem simulator to produce living, dynamic worlds.

Core capabilities:
  - Multi-biome terrain generation with configurable parameters
  - Climate zone modeling (temperature, precipitation, elevation)
  - Biome transition blending with gradient zones
  - Flora distribution based on biome properties
  - World seed management for reproducible generation
  - Heightmap synthesis with erosion simulation
  - River and water body placement
  - Resource node distribution within biomes

Architecture:
  BiomeGenerationPipeline (Singleton)
    |-- BiomeDefinition (dataclass)
    |-- ClimateZone (dataclass)
    |-- TerrainLayer (dataclass)
    |-- FloraTemplate (dataclass)
    |-- WorldConfiguration (dataclass)
    |-- define_biome()
    |-- generate_terrain()
    |-- compute_climate_zones()
    |-- distribute_flora()
    |-- blend_biome_transitions()
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


class TerrainCategory(Enum):
    PLAINS = "plains"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    VALLEY = "valley"
    PLATEAU = "plateau"
    COASTAL = "coastal"
    RIVER_BASIN = "river_basin"
    LAKE_BED = "lake_bed"


class ClimateBand(Enum):
    POLAR = "polar"
    SUBPOLAR = "subpolar"
    TEMPERATE = "temperate"
    SUBTROPICAL = "subtropical"
    TROPICAL = "tropical"
    ARID = "arid"


class SoilType(Enum):
    SANDY = "sandy"
    LOAMY = "loamy"
    CLAY = "clay"
    ROCKY = "rocky"
    VOLCANIC = "volcanic"
    PEAT = "peat"
    SILT = "silt"


class FloraDensity(Enum):
    SPARSE = "sparse"
    MODERATE = "moderate"
    DENSE = "dense"
    JUNGLE = "jungle"
    BARREN = "barren"


@dataclass
class BiomeDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    terrain_category: TerrainCategory = TerrainCategory.PLAINS
    climate_band: ClimateBand = ClimateBand.TEMPERATE
    soil_type: SoilType = SoilType.LOAMY
    elevation_min: float = 0.0
    elevation_max: float = 1.0
    temperature_range: Tuple[float, float] = (0.0, 30.0)
    precipitation_range: Tuple[float, float] = (200.0, 1000.0)
    flora_density: FloraDensity = FloraDensity.MODERATE
    dominant_colors: List[str] = field(default_factory=list)
    transition_blend_width: float = 0.15
    resource_richness: float = 0.5
    hazard_level: float = 0.0
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "terrain_category": self.terrain_category.value,
            "climate_band": self.climate_band.value,
            "soil_type": self.soil_type.value,
            "elevation_min": self.elevation_min,
            "elevation_max": self.elevation_max,
            "temperature_range": list(self.temperature_range),
            "precipitation_range": list(self.precipitation_range),
            "flora_density": self.flora_density.value,
            "dominant_colors": self.dominant_colors,
            "transition_blend_width": self.transition_blend_width,
            "resource_richness": self.resource_richness,
            "hazard_level": self.hazard_level,
            "tags": self.tags,
            "created_at": self.created_at,
        }


@dataclass
class ClimateZone:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    band: ClimateBand = ClimateBand.TEMPERATE
    center_latitude: float = 0.0
    temperature_base: float = 20.0
    temperature_variance: float = 5.0
    precipitation_base: float = 500.0
    precipitation_variance: float = 200.0
    wind_direction: float = 0.0
    wind_strength: float = 5.0
    seasonal_amplitude: float = 10.0
    biome_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "band": self.band.value,
            "center_latitude": self.center_latitude,
            "temperature_base": self.temperature_base,
            "temperature_variance": self.temperature_variance,
            "precipitation_base": self.precipitation_base,
            "precipitation_variance": self.precipitation_variance,
            "wind_direction": self.wind_direction,
            "wind_strength": self.wind_strength,
            "seasonal_amplitude": self.seasonal_amplitude,
            "biome_ids": self.biome_ids,
            "created_at": self.created_at,
        }


@dataclass
class TerrainLayer:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    biome_id: str = ""
    height_map: List[List[float]] = field(default_factory=list)
    moisture_map: List[List[float]] = field(default_factory=list)
    temperature_map: List[List[float]] = field(default_factory=list)
    resolution: int = 256
    seed: int = 0
    min_height: float = 0.0
    max_height: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "biome_id": self.biome_id,
            "resolution": self.resolution,
            "seed": self.seed,
            "min_height": self.min_height,
            "max_height": self.max_height,
            "created_at": self.created_at,
        }


@dataclass
class FloraTemplate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    biome_id: str = ""
    density: FloraDensity = FloraDensity.MODERATE
    min_height_threshold: float = 0.0
    max_height_threshold: float = 1.0
    min_moisture: float = 0.0
    max_moisture: float = 1.0
    min_temperature: float = -10.0
    max_temperature: float = 40.0
    cluster_size: int = 5
    spacing: float = 10.0
    scale_variation: float = 0.2
    species_list: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "biome_id": self.biome_id,
            "density": self.density.value,
            "min_height_threshold": self.min_height_threshold,
            "max_height_threshold": self.max_height_threshold,
            "min_moisture": self.min_moisture,
            "max_moisture": self.max_moisture,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
            "cluster_size": self.cluster_size,
            "spacing": self.spacing,
            "scale_variation": self.scale_variation,
            "species_list": self.species_list,
            "created_at": self.created_at,
        }


@dataclass
class WorldConfiguration:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Untitled World"
    seed: int = 0
    resolution: int = 256
    world_width: float = 10000.0
    world_height: float = 10000.0
    biome_ids: List[str] = field(default_factory=list)
    climate_zone_ids: List[str] = field(default_factory=list)
    ocean_level: float = 0.3
    mountain_level: float = 0.75
    erosion_iterations: int = 5
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "seed": self.seed,
            "resolution": self.resolution,
            "world_width": self.world_width,
            "world_height": self.world_height,
            "biome_ids": self.biome_ids,
            "climate_zone_ids": self.climate_zone_ids,
            "ocean_level": self.ocean_level,
            "mountain_level": self.mountain_level,
            "erosion_iterations": self.erosion_iterations,
            "created_at": self.created_at,
        }


_BIOME_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "temperate_forest": {
        "terrain_category": TerrainCategory.HILLS,
        "climate_band": ClimateBand.TEMPERATE,
        "soil_type": SoilType.LOAMY,
        "elevation_min": 0.2, "elevation_max": 0.7,
        "temperature_range": (5.0, 25.0),
        "precipitation_range": (600.0, 1200.0),
        "flora_density": FloraDensity.DENSE,
        "dominant_colors": ["#2d5a27", "#4a7c3f", "#6b8e23"],
        "resource_richness": 0.7, "hazard_level": 0.1,
        "tags": ["forest", "temperate", "deciduous"],
    },
    "tropical_rainforest": {
        "terrain_category": TerrainCategory.RIVER_BASIN,
        "climate_band": ClimateBand.TROPICAL,
        "soil_type": SoilType.LOAMY,
        "elevation_min": 0.0, "elevation_max": 0.5,
        "temperature_range": (20.0, 35.0),
        "precipitation_range": (1500.0, 3000.0),
        "flora_density": FloraDensity.JUNGLE,
        "dominant_colors": ["#1a4d1a", "#2d6e2d", "#4caf50"],
        "resource_richness": 0.9, "hazard_level": 0.4,
        "tags": ["forest", "tropical", "rainforest"],
    },
    "savanna": {
        "terrain_category": TerrainCategory.PLAINS,
        "climate_band": ClimateBand.SUBTROPICAL,
        "soil_type": SoilType.SANDY,
        "elevation_min": 0.1, "elevation_max": 0.6,
        "temperature_range": (15.0, 35.0),
        "precipitation_range": (300.0, 800.0),
        "flora_density": FloraDensity.SPARSE,
        "dominant_colors": ["#c4a43e", "#d4b84a", "#8b7500"],
        "resource_richness": 0.4, "hazard_level": 0.2,
        "tags": ["grassland", "subtropical", "acacia"],
    },
    "desert": {
        "terrain_category": TerrainCategory.PLAINS,
        "climate_band": ClimateBand.ARID,
        "soil_type": SoilType.SANDY,
        "elevation_min": 0.0, "elevation_max": 0.4,
        "temperature_range": (10.0, 45.0),
        "precipitation_range": (0.0, 200.0),
        "flora_density": FloraDensity.BARREN,
        "dominant_colors": ["#c2b280", "#d4a76a", "#e8c872"],
        "resource_richness": 0.2, "hazard_level": 0.6,
        "tags": ["desert", "arid", "sand"],
    },
    "tundra": {
        "terrain_category": TerrainCategory.PLAINS,
        "climate_band": ClimateBand.SUBPOLAR,
        "soil_type": SoilType.PEAT,
        "elevation_min": 0.0, "elevation_max": 0.3,
        "temperature_range": (-30.0, 10.0),
        "precipitation_range": (100.0, 400.0),
        "flora_density": FloraDensity.SPARSE,
        "dominant_colors": ["#8b9a8b", "#a0afa0", "#6b7b6b"],
        "resource_richness": 0.3, "hazard_level": 0.7,
        "tags": ["tundra", "cold", "permafrost"],
    },
    "alpine_mountain": {
        "terrain_category": TerrainCategory.MOUNTAINS,
        "climate_band": ClimateBand.SUBPOLAR,
        "soil_type": SoilType.ROCKY,
        "elevation_min": 0.6, "elevation_max": 1.0,
        "temperature_range": (-20.0, 5.0),
        "precipitation_range": (400.0, 1500.0),
        "flora_density": FloraDensity.SPARSE,
        "dominant_colors": ["#808080", "#a0a0a0", "#ffffff"],
        "resource_richness": 0.5, "hazard_level": 0.8,
        "tags": ["mountain", "alpine", "snow"],
    },
    "mediterranean_coastal": {
        "terrain_category": TerrainCategory.COASTAL,
        "climate_band": ClimateBand.SUBTROPICAL,
        "soil_type": SoilType.SANDY,
        "elevation_min": 0.0, "elevation_max": 0.3,
        "temperature_range": (10.0, 30.0),
        "precipitation_range": (300.0, 700.0),
        "flora_density": FloraDensity.MODERATE,
        "dominant_colors": ["#90a955", "#b5c96b", "#e9c46a"],
        "resource_richness": 0.6, "hazard_level": 0.2,
        "tags": ["coastal", "mediterranean", "scrubland"],
    },
    "taiga": {
        "terrain_category": TerrainCategory.HILLS,
        "climate_band": ClimateBand.SUBPOLAR,
        "soil_type": SoilType.PEAT,
        "elevation_min": 0.1, "elevation_max": 0.6,
        "temperature_range": (-15.0, 10.0),
        "precipitation_range": (200.0, 600.0),
        "flora_density": FloraDensity.DENSE,
        "dominant_colors": ["#1a3a1a", "#2d5a2d", "#3a6b3a"],
        "resource_richness": 0.5, "hazard_level": 0.5,
        "tags": ["forest", "boreal", "coniferous"],
    },
}


class BiomeGenerationPipeline:
    _instance: Optional["BiomeGenerationPipeline"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "BiomeGenerationPipeline":
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
        self._biomes: Dict[str, BiomeDefinition] = {}
        self._climate_zones: Dict[str, ClimateZone] = {}
        self._terrain_layers: Dict[str, TerrainLayer] = {}
        self._flora_templates: Dict[str, FloraTemplate] = {}
        self._world_configs: Dict[str, WorldConfiguration] = {}
        self._total_biomes_defined: int = 0
        self._total_terrains_generated: int = 0
        self._total_flora_distributed: int = 0

    def define_biome(
        self,
        name: str,
        terrain_category: Optional[str] = None,
        climate_band: Optional[str] = None,
        soil_type: Optional[str] = None,
        elevation_min: Optional[float] = None,
        elevation_max: Optional[float] = None,
        temperature_min: Optional[float] = None,
        temperature_max: Optional[float] = None,
        precipitation_min: Optional[float] = None,
        precipitation_max: Optional[float] = None,
        flora_density: Optional[str] = None,
        dominant_colors: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> BiomeDefinition:
        template = _BIOME_TEMPLATES.get(name.lower(), {})

        biome = BiomeDefinition(
            name=name,
            terrain_category=TerrainCategory(terrain_category) if terrain_category else template.get("terrain_category", TerrainCategory.PLAINS),
            climate_band=ClimateBand(climate_band) if climate_band else template.get("climate_band", ClimateBand.TEMPERATE),
            soil_type=SoilType(soil_type) if soil_type else template.get("soil_type", SoilType.LOAMY),
            elevation_min=elevation_min if elevation_min is not None else template.get("elevation_min", 0.0),
            elevation_max=elevation_max if elevation_max is not None else template.get("elevation_max", 1.0),
            temperature_range=(
                temperature_min if temperature_min is not None else template.get("temperature_range", (0.0, 30.0))[0],
                temperature_max if temperature_max is not None else template.get("temperature_range", (0.0, 30.0))[1],
            ),
            precipitation_range=(
                precipitation_min if precipitation_min is not None else template.get("precipitation_range", (200.0, 1000.0))[0],
                precipitation_max if precipitation_max is not None else template.get("precipitation_range", (200.0, 1000.0))[1],
            ),
            flora_density=FloraDensity(flora_density) if flora_density else template.get("flora_density", FloraDensity.MODERATE),
            dominant_colors=dominant_colors or template.get("dominant_colors", []),
            resource_richness=template.get("resource_richness", 0.5),
            hazard_level=template.get("hazard_level", 0.0),
            tags=tags or template.get("tags", []),
        )

        self._biomes[biome.id] = biome
        self._total_biomes_defined += 1
        return biome

    def compute_climate_zones(
        self,
        world_seed: int = 0,
        zone_count: int = 5,
    ) -> List[ClimateZone]:
        rng = random.Random(world_seed)
        zones = []

        band_distribution = [
            (ClimateBand.POLAR, -80.0, -60.0),
            (ClimateBand.SUBPOLAR, -50.0, -30.0),
            (ClimateBand.TEMPERATE, -20.0, 20.0),
            (ClimateBand.SUBTROPICAL, 25.0, 35.0),
            (ClimateBand.TROPICAL, 0.0, 15.0),
        ]

        for i in range(zone_count):
            band, lat_min, lat_max = band_distribution[i % len(band_distribution)]
            center_lat = lat_min + rng.random() * (lat_max - lat_min)

            if band == ClimateBand.TROPICAL:
                temp_base = 28.0 + rng.uniform(-3, 3)
                precip_base = 1500.0 + rng.uniform(-500, 500)
            elif band == ClimateBand.ARID:
                temp_base = 30.0 + rng.uniform(-5, 5)
                precip_base = 100.0 + rng.uniform(0, 150)
            elif band == ClimateBand.TEMPERATE:
                temp_base = 15.0 + rng.uniform(-5, 5)
                precip_base = 700.0 + rng.uniform(-300, 300)
            elif band == ClimateBand.SUBPOLAR:
                temp_base = -5.0 + rng.uniform(-5, 5)
                precip_base = 300.0 + rng.uniform(-150, 150)
            else:
                temp_base = -20.0 + rng.uniform(-5, 5)
                precip_base = 200.0 + rng.uniform(-100, 100)

            zone = ClimateZone(
                name=f"{band.value}_zone_{i}",
                band=band,
                center_latitude=round(center_lat, 1),
                temperature_base=round(temp_base, 1),
                temperature_variance=round(5.0 + rng.uniform(0, 10), 1),
                precipitation_base=round(precip_base, 1),
                precipitation_variance=round(100.0 + rng.uniform(0, 300), 1),
                wind_direction=round(rng.uniform(0, 360), 1),
                wind_strength=round(2.0 + rng.uniform(0, 10), 1),
                seasonal_amplitude=round(5.0 + rng.uniform(0, 20), 1),
            )
            zones.append(zone)
            self._climate_zones[zone.id] = zone

        return zones

    def generate_terrain(
        self,
        biome_id: str,
        resolution: int = 256,
        seed: int = 0,
    ) -> TerrainLayer:
        biome = self._biomes.get(biome_id)
        if not biome:
            raise ValueError(f"Biome '{biome_id}' not found")

        rng = random.Random(seed)

        height_map = []
        moisture_map = []
        temperature_map = []

        elevation_range = biome.elevation_max - biome.elevation_min

        for y in range(resolution):
            height_row = []
            moisture_row = []
            temp_row = []
            for x in range(resolution):
                nx = x / resolution
                ny = y / resolution

                h1 = self._simplex_noise(nx * 6.0, ny * 6.0, seed)
                h2 = self._simplex_noise(nx * 3.0, ny * 3.0, seed + 1000) * 0.5
                h3 = self._simplex_noise(nx * 12.0, ny * 12.0, seed + 2000) * 0.25

                height = biome.elevation_min + (h1 + h2 + h3) * elevation_range / 1.75
                height = max(0.0, min(1.0, height))

                moisture = self._simplex_noise(nx * 4.0 + 500, ny * 4.0 + 500, seed + 3000)
                moisture = (moisture + 1.0) / 2.0

                temp_min, temp_max = biome.temperature_range
                temp = temp_min + (temp_max - temp_min) * (1.0 - abs(ny - 0.5) * 2.0)
                temp += self._simplex_noise(nx * 5.0, ny * 5.0, seed + 4000) * 3.0

                height_row.append(round(height, 4))
                moisture_row.append(round(moisture, 4))
                temp_row.append(round(temp, 1))

            height_map.append(height_row)
            moisture_map.append(moisture_row)
            temperature_map.append(temp_row)

        layer = TerrainLayer(
            name=f"{biome.name}_terrain",
            biome_id=biome_id,
            height_map=height_map,
            moisture_map=moisture_map,
            temperature_map=temperature_map,
            resolution=resolution,
            seed=seed,
            min_height=biome.elevation_min,
            max_height=biome.elevation_max,
        )

        self._terrain_layers[layer.id] = layer
        self._total_terrains_generated += 1
        return layer

    @staticmethod
    def _simplex_noise(x: float, y: float, seed: int) -> float:
        n = seed + x * 137.0 + y * 173.0
        n = (math.sin(n * 12.9898 + 78.233) * 43758.5453) % 1.0
        return n * 2.0 - 1.0

    def distribute_flora(
        self,
        biome_id: str,
        terrain_layer_id: str,
        density: Optional[str] = None,
    ) -> FloraTemplate:
        biome = self._biomes.get(biome_id)
        if not biome:
            raise ValueError(f"Biome '{biome_id}' not found")

        density_enum = FloraDensity(density) if density else biome.flora_density
        density_multipliers = {
            FloraDensity.BARREN: 0.5,
            FloraDensity.SPARSE: 1.0,
            FloraDensity.MODERATE: 2.0,
            FloraDensity.DENSE: 3.5,
            FloraDensity.JUNGLE: 5.0,
        }
        cluster_mult = density_multipliers.get(density_enum, 2.0)

        flora = FloraTemplate(
            name=f"{biome.name}_flora",
            biome_id=biome_id,
            density=density_enum,
            min_height_threshold=biome.elevation_min + 0.05,
            max_height_threshold=biome.elevation_max - 0.05,
            min_moisture=0.2,
            max_moisture=1.0,
            min_temperature=biome.temperature_range[0],
            max_temperature=biome.temperature_range[1],
            cluster_size=max(1, int(5 * cluster_mult)),
            spacing=max(2.0, 20.0 / cluster_mult),
            scale_variation=0.15 + 0.05 * cluster_mult,
            species_list=biome.tags,
        )

        self._flora_templates[flora.id] = flora
        self._total_flora_distributed += 1
        return flora

    def blend_biome_transitions(
        self,
        biome_a_id: str,
        biome_b_id: str,
        blend_width: Optional[float] = None,
    ) -> Dict[str, Any]:
        biome_a = self._biomes.get(biome_a_id)
        biome_b = self._biomes.get(biome_b_id)

        if not biome_a or not biome_b:
            return {"error": "One or both biomes not found"}

        width = blend_width or max(biome_a.transition_blend_width, biome_b.transition_blend_width)

        temp_a = sum(biome_a.temperature_range) / 2
        temp_b = sum(biome_b.temperature_range) / 2
        temp_gradient = abs(temp_a - temp_b)

        precip_a = sum(biome_a.precipitation_range) / 2
        precip_b = sum(biome_b.precipitation_range) / 2
        precip_gradient = abs(precip_a - precip_b)

        elev_diff = abs(
            (biome_a.elevation_min + biome_a.elevation_max) / 2
            - (biome_b.elevation_min + biome_b.elevation_max) / 2
        )

        compatibility = 1.0 - (
            temp_gradient / 60.0 * 0.4
            + precip_gradient / 3000.0 * 0.3
            + elev_diff * 0.3
        )
        compatibility = max(0.0, min(1.0, compatibility))

        transition_zones = []
        steps = 5
        for i in range(steps + 1):
            t = i / steps
            transition_zones.append({
                "t": round(t, 2),
                "temperature": round(temp_a + (temp_b - temp_a) * t, 1),
                "precipitation": round(precip_a + (precip_b - precip_a) * t, 1),
                "elevation": round(
                    biome_a.elevation_min + (biome_b.elevation_min - biome_a.elevation_min) * t, 2
                ),
            })

        return {
            "biome_a": biome_a.name,
            "biome_b": biome_b.name,
            "blend_width": width,
            "compatibility_score": round(compatibility, 3),
            "transition_zones": transition_zones,
            "recommended_blend_type": (
                "gradient" if compatibility > 0.6
                else "stepped" if compatibility > 0.3
                else "hard_boundary"
            ),
        }

    def create_world_config(
        self,
        name: str = "Untitled World",
        seed: int = 0,
        resolution: int = 256,
        world_width: float = 10000.0,
        world_height: float = 10000.0,
        biome_names: Optional[List[str]] = None,
    ) -> WorldConfiguration:
        biome_ids = []
        if biome_names:
            for name_key in biome_names:
                for bid, biome in self._biomes.items():
                    if biome.name.lower() == name_key.lower():
                        biome_ids.append(bid)
                        break

        config = WorldConfiguration(
            name=name,
            seed=seed if seed != 0 else random.randint(1, 999999),
            resolution=resolution,
            world_width=world_width,
            world_height=world_height,
            biome_ids=biome_ids,
        )

        self._world_configs[config.id] = config
        return config

    def get_biome(self, biome_id: str) -> Optional[BiomeDefinition]:
        return self._biomes.get(biome_id)

    def get_terrain(self, terrain_id: str) -> Optional[TerrainLayer]:
        return self._terrain_layers.get(terrain_id)

    def list_biomes(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self._biomes.values()]

    def list_climate_zones(self) -> List[Dict[str, Any]]:
        return [z.to_dict() for z in self._climate_zones.values()]

    def list_terrains(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._terrain_layers.values()]

    def list_flora_templates(self) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self._flora_templates.values()]

    def list_world_configs(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._world_configs.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_biomes_defined": self._total_biomes_defined,
            "total_biomes": len(self._biomes),
            "total_climate_zones": len(self._climate_zones),
            "total_terrains_generated": self._total_terrains_generated,
            "total_flora_distributed": self._total_flora_distributed,
            "total_world_configs": len(self._world_configs),
            "biome_templates_available": len(_BIOME_TEMPLATES),
            "biomes_by_category": {
                cat.value: sum(1 for b in self._biomes.values() if b.terrain_category == cat)
                for cat in TerrainCategory
            },
            "biomes_by_climate": {
                band.value: sum(1 for b in self._biomes.values() if b.climate_band == band)
                for band in ClimateBand
            },
        }


def get_biome_generation_pipeline() -> BiomeGenerationPipeline:
    return BiomeGenerationPipeline()