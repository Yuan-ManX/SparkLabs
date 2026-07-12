"""
SparkLabs Engine - Climate and Biome Management System

A comprehensive climate and biome simulation layer for the SparkLabs AI-native
game engine. It models geographic biome regions, the climate data that shapes
them, the flora and fauna that inhabit them, seasonal cycles, gradual or
magical biome transitions, and overall ecosystem health.

Architecture:
  ClimateBiomeSystem (Singleton)
    |-- BiomeType / ClimateZone / Season / FloraType / FaunaType
    |-- BiomeEventKind / TransitionType / BiomeStatus
    |-- TemperatureRange / HumidityRange / ClimateData
    |-- FloraSpecies / FaunaSpecies
    |-- BiomeRegion / BiomeTransition
    |-- SeasonalPattern / EcosystemHealth
    |-- ClimateBiomeConfig / ClimateBiomeStats / ClimateBiomeSnapshot
    |-- BiomeEvent

Design notes:
  - Thread-safe singleton using double-checked locking with an RLock.
  - All public mutating operations return structured tuples so callers can
    branch on success without raising exceptions for expected failures.
  - Data structures serialize to plain dicts via to_dict() so they can be
    handed to the AI narrative layer or persisted to save files.
  - Seed data is loaded on first initialization to give the engine a usable
    starting world out of the box.

Usage:
    system = get_climate_biome_system()
    system.initialize()
    region = system.register_region(
        name="Whispering Vale",
        biome_type=BiomeType.TEMPERATE_FOREST,
        climate_zone=ClimateZone.TEMPERATE,
        area=1200.0,
        center_coord=(100.0, 100.0),
    )
    summary = system.tick(0.1)
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
# Enums
# ---------------------------------------------------------------------------

class BiomeType(str, Enum):
    """Classification of a biome by its dominant ecological character."""
    TROPICAL_RAINFOREST = "tropical_rainforest"
    TEMPERATE_FOREST = "temperate_forest"
    BOREAL_FOREST = "boreal_forest"
    TUNDRA = "tundra"
    DESERT = "desert"
    SAVANNA = "savanna"
    GRASSLAND = "grassland"
    WETLAND = "wetland"
    MOUNTAIN = "mountain"
    OCEAN = "ocean"
    COASTAL = "coastal"
    ARCTIC = "arctic"
    VOLCANIC = "volcanic"
    UNDERGROUND = "underground"
    SKY_ISLAND = "sky_island"
    CORRUPT = "corrupt"
    CRYSTAL = "crystal"
    SHADOW = "shadow"
    FUNGAL = "fungal"
    ETHEREAL = "ethereal"


class ClimateZone(str, Enum):
    """Latitudinal or magical band that drives baseline climate behavior."""
    EQUATORIAL = "equatorial"
    TROPICAL = "tropical"
    SUBTROPICAL = "subtropical"
    TEMPERATE = "temperate"
    CONTINENTAL = "continental"
    POLAR = "polar"
    ALPINE = "alpine"
    MAGICAL = "magical"
    VOID = "void"


class Season(str, Enum):
    """A seasonal phase that modifies climate and life-cycle multipliers."""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    MONSOON = "monsoon"
    DRY = "dry"
    WET = "wet"
    ECLIPSE = "eclipse"
    HARVEST = "harvest"
    FROST = "frost"


class FloraType(str, Enum):
    """Functional category of a plant species."""
    TREE = "tree"
    SHRUB = "shrub"
    GRASS = "grass"
    FLOWER = "flower"
    FUNGUS = "fungus"
    MOSS = "moss"
    CACTUS = "cactus"
    VINE = "vine"
    ALGAE = "algae"
    MAGICAL_PLANT = "magical_plant"


class FaunaType(str, Enum):
    """Functional category of an animal species."""
    MAMMAL = "mammal"
    BIRD = "bird"
    REPTILE = "reptile"
    AMPHIBIAN = "amphibian"
    FISH = "fish"
    INSECT = "insect"
    MAGICAL_CREATURE = "magical_creature"
    UNDEAD = "undead"
    ELEMENTAL = "elemental"
    MYTHICAL = "mythical"


class BiomeEventKind(str, Enum):
    """Kind of event emitted by the climate and biome system."""
    BIOME_CREATED = "biome_created"
    BIOME_TRANSITION = "biome_transition"
    SEASON_CHANGED = "season_changed"
    CLIMATE_SHIFT = "climate_shift"
    FLORA_SPAWNED = "flora_spawned"
    FAUNA_MIGRATED = "fauna_migrated"
    ECOSYSTEM_COLLAPSE = "ecosystem_collapse"
    ECOSYSTEM_RECOVER = "ecosystem_recover"


class TransitionType(str, Enum):
    """How a biome transition unfolds over time."""
    GRADUAL = "gradual"
    ABRUPT = "abrupt"
    MAGICAL = "magical"
    SEASONAL = "seasonal"


class BiomeStatus(str, Enum):
    """Operational health state of a biome region."""
    STABLE = "stable"
    TRANSITIONING = "transitioning"
    DEGRADED = "degraded"
    FLOURISHING = "flourishing"
    CORRUPTED = "corrupted"
    FROZEN = "frozen"


# ---------------------------------------------------------------------------
# Climate default lookup tables
# ---------------------------------------------------------------------------
# Each entry provides baseline climate values for a biome type. Values are
# intentionally coarse; callers can override per region via set_climate.

_BIOME_CLIMATE_DEFAULTS: Dict[BiomeType, Dict[str, float]] = {
    BiomeType.TROPICAL_RAINFOREST: {"t_min": 22.0, "t_max": 32.0, "h_min": 75.0, "h_max": 95.0, "rainfall": 2400.0, "wind": 1.5, "sun": 8.0, "pressure": 101.0, "magic": 0.15},
    BiomeType.TEMPERATE_FOREST: {"t_min": 5.0, "t_max": 22.0, "h_min": 50.0, "h_max": 70.0, "rainfall": 800.0, "wind": 3.0, "sun": 7.0, "pressure": 101.3, "magic": 0.05},
    BiomeType.BOREAL_FOREST: {"t_min": -10.0, "t_max": 18.0, "h_min": 40.0, "h_max": 65.0, "rainfall": 500.0, "wind": 3.5, "sun": 6.0, "pressure": 101.0, "magic": 0.08},
    BiomeType.TUNDRA: {"t_min": -25.0, "t_max": 8.0, "h_min": 30.0, "h_max": 55.0, "rainfall": 250.0, "wind": 5.0, "sun": 5.0, "pressure": 101.2, "magic": 0.04},
    BiomeType.DESERT: {"t_min": 5.0, "t_max": 45.0, "h_min": 5.0, "h_max": 25.0, "rainfall": 50.0, "wind": 4.0, "sun": 11.0, "pressure": 101.5, "magic": 0.03},
    BiomeType.SAVANNA: {"t_min": 18.0, "t_max": 34.0, "h_min": 40.0, "h_max": 65.0, "rainfall": 700.0, "wind": 3.0, "sun": 9.0, "pressure": 101.2, "magic": 0.05},
    BiomeType.GRASSLAND: {"t_min": 0.0, "t_max": 26.0, "h_min": 40.0, "h_max": 60.0, "rainfall": 600.0, "wind": 4.5, "sun": 8.0, "pressure": 101.3, "magic": 0.04},
    BiomeType.WETLAND: {"t_min": 8.0, "t_max": 26.0, "h_min": 70.0, "h_max": 92.0, "rainfall": 1200.0, "wind": 2.0, "sun": 6.5, "pressure": 101.1, "magic": 0.10},
    BiomeType.MOUNTAIN: {"t_min": -10.0, "t_max": 12.0, "h_min": 40.0, "h_max": 70.0, "rainfall": 900.0, "wind": 6.0, "sun": 7.0, "pressure": 85.0, "magic": 0.12},
    BiomeType.OCEAN: {"t_min": 5.0, "t_max": 26.0, "h_min": 80.0, "h_max": 100.0, "rainfall": 0.0, "wind": 5.5, "sun": 7.0, "pressure": 101.3, "magic": 0.07},
    BiomeType.COASTAL: {"t_min": 10.0, "t_max": 26.0, "h_min": 70.0, "h_max": 88.0, "rainfall": 900.0, "wind": 4.5, "sun": 7.5, "pressure": 101.3, "magic": 0.08},
    BiomeType.ARCTIC: {"t_min": -40.0, "t_max": 2.0, "h_min": 30.0, "h_max": 55.0, "rainfall": 150.0, "wind": 6.5, "sun": 3.0, "pressure": 101.0, "magic": 0.06},
    BiomeType.VOLCANIC: {"t_min": 20.0, "t_max": 60.0, "h_min": 10.0, "h_max": 35.0, "rainfall": 300.0, "wind": 3.5, "sun": 8.0, "pressure": 100.5, "magic": 0.45},
    BiomeType.UNDERGROUND: {"t_min": 10.0, "t_max": 18.0, "h_min": 60.0, "h_max": 85.0, "rainfall": 0.0, "wind": 0.5, "sun": 0.0, "pressure": 110.0, "magic": 0.30},
    BiomeType.SKY_ISLAND: {"t_min": 0.0, "t_max": 18.0, "h_min": 50.0, "h_max": 70.0, "rainfall": 800.0, "wind": 7.0, "sun": 9.0, "pressure": 70.0, "magic": 0.55},
    BiomeType.CORRUPT: {"t_min": 5.0, "t_max": 25.0, "h_min": 40.0, "h_max": 60.0, "rainfall": 400.0, "wind": 2.5, "sun": 4.0, "pressure": 101.0, "magic": 0.65},
    BiomeType.CRYSTAL: {"t_min": 0.0, "t_max": 20.0, "h_min": 30.0, "h_max": 50.0, "rainfall": 200.0, "wind": 2.0, "sun": 7.0, "pressure": 99.0, "magic": 0.80},
    BiomeType.SHADOW: {"t_min": -5.0, "t_max": 15.0, "h_min": 50.0, "h_max": 70.0, "rainfall": 300.0, "wind": 3.0, "sun": 2.0, "pressure": 100.0, "magic": 0.60},
    BiomeType.FUNGAL: {"t_min": 12.0, "t_max": 22.0, "h_min": 80.0, "h_max": 95.0, "rainfall": 1000.0, "wind": 1.0, "sun": 1.5, "pressure": 103.0, "magic": 0.35},
    BiomeType.ETHEREAL: {"t_min": 10.0, "t_max": 25.0, "h_min": 50.0, "h_max": 70.0, "rainfall": 500.0, "wind": 2.0, "sun": 8.0, "pressure": 90.0, "magic": 0.90},
}

# Temperature offset applied on top of biome defaults based on climate zone.
_CLIMATE_ZONE_TEMP_OFFSET: Dict[ClimateZone, float] = {
    ClimateZone.EQUATORIAL: 6.0,
    ClimateZone.TROPICAL: 4.0,
    ClimateZone.SUBTROPICAL: 2.0,
    ClimateZone.TEMPERATE: 0.0,
    ClimateZone.CONTINENTAL: -2.0,
    ClimateZone.POLAR: -12.0,
    ClimateZone.ALPINE: -6.0,
    ClimateZone.MAGICAL: 0.0,
    ClimateZone.VOID: -3.0,
}

# Base corruption tendency per biome type, in the range [0, 1].
_BIOME_CORRUPTION_BASE: Dict[BiomeType, float] = {
    BiomeType.CORRUPT: 0.8,
    BiomeType.SHADOW: 0.6,
    BiomeType.VOLCANIC: 0.4,
    BiomeType.FUNGAL: 0.3,
    BiomeType.UNDERGROUND: 0.25,
    BiomeType.ETHEREAL: 0.1,
    BiomeType.CRYSTAL: 0.05,
}
for _b in BiomeType:
    _BIOME_CORRUPTION_BASE.setdefault(_b, 0.05)

# Default season progression order for the standard temperate cycle.
_DEFAULT_SEASON_ORDER: List[Season] = [
    Season.SPRING,
    Season.SUMMER,
    Season.AUTUMN,
    Season.WINTER,
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TemperatureRange:
    """A bounded temperature span with an average value.

    The average is computed automatically from min and max when not supplied.
    """
    min: float = 0.0
    max: float = 0.0
    average: Optional[float] = None

    def __post_init__(self) -> None:
        if self.average is None:
            self.average = (self.min + self.max) / 2.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min": round(self.min, 4),
            "max": round(self.max, 4),
            "average": round(float(self.average), 4),
        }


@dataclass
class HumidityRange:
    """A bounded humidity span (percent) with an average value.

    The average is computed automatically from min and max when not supplied.
    """
    min: float = 0.0
    max: float = 0.0
    average: Optional[float] = None

    def __post_init__(self) -> None:
        if self.average is None:
            self.average = (self.min + self.max) / 2.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min": round(self.min, 4),
            "max": round(self.max, 4),
            "average": round(float(self.average), 4),
        }


@dataclass
class ClimateData:
    """The full set of atmospheric values for a region."""
    temperature: TemperatureRange = field(default_factory=TemperatureRange)
    humidity: HumidityRange = field(default_factory=HumidityRange)
    rainfall: float = 0.0
    wind_speed: float = 0.0
    sunlight_hours: float = 0.0
    air_pressure: float = 101.3
    magical_density: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature.to_dict(),
            "humidity": self.humidity.to_dict(),
            "rainfall": round(self.rainfall, 4),
            "wind_speed": round(self.wind_speed, 4),
            "sunlight_hours": round(self.sunlight_hours, 4),
            "air_pressure": round(self.air_pressure, 4),
            "magical_density": round(self.magical_density, 4),
        }


@dataclass
class FloraSpecies:
    """A plant species definition and its growth traits."""
    species_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    flora_type: FloraType = FloraType.GRASS
    preferred_biomes: List[BiomeType] = field(default_factory=list)
    growth_rate: float = 0.1
    rarity: float = 0.5
    magical_properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "species_id": self.species_id,
            "name": self.name,
            "flora_type": self.flora_type.value,
            "preferred_biomes": [b.value for b in self.preferred_biomes],
            "growth_rate": round(self.growth_rate, 6),
            "rarity": round(self.rarity, 6),
            "magical_properties": dict(self.magical_properties),
        }


@dataclass
class FaunaSpecies:
    """An animal species definition and its behavioral traits."""
    species_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    fauna_type: FaunaType = FaunaType.MAMMAL
    preferred_biomes: List[BiomeType] = field(default_factory=list)
    population: int = 0
    migration_pattern: Dict[str, Any] = field(default_factory=dict)
    danger_level: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "species_id": self.species_id,
            "name": self.name,
            "fauna_type": self.fauna_type.value,
            "preferred_biomes": [b.value for b in self.preferred_biomes],
            "population": int(self.population),
            "migration_pattern": dict(self.migration_pattern),
            "danger_level": round(self.danger_level, 6),
        }


@dataclass
class BiomeRegion:
    """A geographic region with a biome type, climate, and inhabitant lists."""
    region_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    biome_type: BiomeType = BiomeType.GRASSLAND
    climate_zone: ClimateZone = ClimateZone.TEMPERATE
    area: float = 100.0
    center_coord: Tuple[float, float] = (0.0, 0.0)
    border_coords: List[Tuple[float, float]] = field(default_factory=list)
    climate: ClimateData = field(default_factory=ClimateData)
    flora_list: List[str] = field(default_factory=list)
    fauna_list: List[str] = field(default_factory=list)
    status: BiomeStatus = BiomeStatus.STABLE
    transition_progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "name": self.name,
            "biome_type": self.biome_type.value,
            "climate_zone": self.climate_zone.value,
            "area": round(self.area, 4),
            "center_coord": [float(self.center_coord[0]), float(self.center_coord[1])],
            "border_coords": [[float(c[0]), float(c[1])] for c in self.border_coords],
            "climate": self.climate.to_dict(),
            "flora_list": list(self.flora_list),
            "fauna_list": list(self.fauna_list),
            "status": self.status.value,
            "transition_progress": round(self.transition_progress, 6),
        }


@dataclass
class BiomeTransition:
    """An ongoing transition of a region from one biome type to another."""
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    region_id: str = ""
    from_biome: BiomeType = BiomeType.GRASSLAND
    to_biome: BiomeType = BiomeType.GRASSLAND
    transition_type: TransitionType = TransitionType.GRADUAL
    duration: float = 100.0
    progress: float = 0.0
    trigger_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "region_id": self.region_id,
            "from_biome": self.from_biome.value,
            "to_biome": self.to_biome.value,
            "transition_type": self.transition_type.value,
            "duration": round(self.duration, 4),
            "progress": round(self.progress, 6),
            "trigger_reason": self.trigger_reason,
        }


@dataclass
class SeasonalPattern:
    """Climate and life-cycle multipliers for a single season."""
    season: Season = Season.SPRING
    duration_days: float = 30.0
    temperature_modifier: float = 0.0
    humidity_modifier: float = 0.0
    flora_multiplier: float = 1.0
    fauna_multiplier: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "season": self.season.value,
            "duration_days": round(self.duration_days, 4),
            "temperature_modifier": round(self.temperature_modifier, 6),
            "humidity_modifier": round(self.humidity_modifier, 6),
            "flora_multiplier": round(self.flora_multiplier, 6),
            "fauna_multiplier": round(self.fauna_multiplier, 6),
        }


@dataclass
class EcosystemHealth:
    """Aggregate health metrics for a region's ecosystem."""
    biodiversity_index: float = 0.0
    stability_score: float = 0.5
    resource_abundance: float = 0.5
    pollution_level: float = 0.0
    corruption_level: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "biodiversity_index": round(self.biodiversity_index, 6),
            "stability_score": round(self.stability_score, 6),
            "resource_abundance": round(self.resource_abundance, 6),
            "pollution_level": round(self.pollution_level, 6),
            "corruption_level": round(self.corruption_level, 6),
        }


@dataclass
class ClimateBiomeConfig:
    """Tunable configuration for the climate and biome system."""
    season_duration_base: float = 30.0
    transition_speed: float = 1.0
    enable_magical_biomes: bool = True
    enable_seasonal_cycles: bool = True
    flora_spawn_rate: float = 0.05
    fauna_migration_rate: float = 0.03

    def to_dict(self) -> Dict[str, Any]:
        return {
            "season_duration_base": self.season_duration_base,
            "transition_speed": self.transition_speed,
            "enable_magical_biomes": self.enable_magical_biomes,
            "enable_seasonal_cycles": self.enable_seasonal_cycles,
            "flora_spawn_rate": self.flora_spawn_rate,
            "fauna_migration_rate": self.fauna_migration_rate,
        }


@dataclass
class ClimateBiomeStats:
    """Roll-up statistics describing the current system state."""
    total_regions: int = 0
    total_transitions: int = 0
    total_flora_species: int = 0
    total_fauna_species: int = 0
    active_seasons: int = 0
    ecosystem_health_avg: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_regions": self.total_regions,
            "total_transitions": self.total_transitions,
            "total_flora_species": self.total_flora_species,
            "total_fauna_species": self.total_fauna_species,
            "active_seasons": self.active_seasons,
            "ecosystem_health_avg": round(self.ecosystem_health_avg, 6),
        }


@dataclass
class ClimateBiomeSnapshot:
    """A point-in-time snapshot of regions, transitions, and season."""
    regions: List[BiomeRegion] = field(default_factory=list)
    transitions: List[BiomeTransition] = field(default_factory=list)
    season: Season = Season.SPRING
    ecosystem_health: EcosystemHealth = field(default_factory=EcosystemHealth)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regions": [r.to_dict() for r in self.regions],
            "transitions": [t.to_dict() for t in self.transitions],
            "season": self.season.value,
            "ecosystem_health": self.ecosystem_health.to_dict(),
        }


@dataclass
class BiomeEvent:
    """An event record emitted by the system for logging or narration."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: BiomeEventKind = BiomeEventKind.BIOME_CREATED
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


# ---------------------------------------------------------------------------
# ClimateBiomeSystem Singleton
# ---------------------------------------------------------------------------

class ClimateBiomeSystem:
    """Central registry and simulator for climate, biomes, and ecosystems.

    The system owns the canonical collections of regions, species, seasonal
    patterns, and transitions. It exposes a tick() method that advances time
    across all subsystems and a collection of query helpers used by the AI
    director and gameplay layers.

    Usage:
        system = get_climate_biome_system()
        system.initialize()
        summary = system.tick(0.1)
    """

    _instance: Optional["ClimateBiomeSystem"] = None
    _init_lock: threading.RLock = threading.RLock()

    # -- internal constants ------------------------------------------------
    EPSILON: float = 1e-9
    MAX_EVENTS: int = 500
    COLLAPSE_STABILITY_THRESHOLD: float = 0.2
    COLLAPSE_BIODIVERSITY_THRESHOLD: float = 0.05

    def __init__(self) -> None:
        # Double-checked initialization guard so repeated construction is safe.
        if getattr(self, "_initialized", False):
            return
        with self._init_lock:
            if getattr(self, "_initialized", False):
                return
            self._regions: Dict[str, BiomeRegion] = {}
            self._flora_species: Dict[str, FloraSpecies] = {}
            self._fauna_species: Dict[str, FaunaSpecies] = {}
            self._transitions: Dict[str, BiomeTransition] = {}
            self._seasonal_patterns: Dict[Season, SeasonalPattern] = {}
            self._ecosystem_health: Dict[str, EcosystemHealth] = {}
            self._events: List[BiomeEvent] = []

            self._current_season: Season = Season.SPRING
            self._season_elapsed: float = 0.0
            self._season_counter: int = 0

            self._config: ClimateBiomeConfig = ClimateBiomeConfig()
            self._tick_count: int = 0
            self._total_transitions_started: int = 0
            self._total_transitions_completed: int = 0
            self._total_flora_spawned: int = 0
            self._total_fauna_migrated: int = 0
            self._total_ecosystem_collapses: int = 0
            self._total_ecosystem_recoveries: int = 0
            self._seeded: bool = False
            self._initialized: bool = True

    # ------------------------------------------------------------------
    # Singleton lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ClimateBiomeSystem":
        """Return the singleton ClimateBiomeSystem, creating it if needed."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Tear down the singleton so a fresh instance can be built."""
        with cls._init_lock:
            cls._instance = None

    def initialize(self) -> Tuple[bool, str]:
        """Load seed data and default seasonal patterns.

        Idempotent: calling initialize() multiple times is safe and will not
        duplicate seed entries.
        """
        if self._seeded:
            return True, "Already initialized"
        self._load_default_seasonal_patterns()
        self._load_seed_data()
        self._seeded = True
        self._emit(
            BiomeEventKind.BIOME_CREATED,
            {"action": "initialize", "regions": len(self._regions),
             "flora": len(self._flora_species), "fauna": len(self._fauna_species)},
        )
        return True, (
            f"Initialized with {len(self._regions)} regions, "
            f"{len(self._flora_species)} flora species, "
            f"{len(self._fauna_species)} fauna species"
        )

    # ------------------------------------------------------------------
    # Region management
    # ------------------------------------------------------------------

    def register_region(
        self,
        name: str,
        biome_type: BiomeType,
        climate_zone: ClimateZone,
        area: float,
        center_coord: Tuple[float, float],
        border_coords: Optional[List[Tuple[float, float]]] = None,
        climate: Optional[ClimateData] = None,
    ) -> Tuple[bool, str, Optional[BiomeRegion]]:
        """Register a new biome region with the given attributes."""
        if not name:
            return False, "Region name must not be empty", None
        if area <= 0:
            return False, "Region area must be positive", None
        if climate is None:
            climate = self._build_default_climate(biome_type, climate_zone)
        if border_coords is None:
            border_coords = self._build_default_polygon(center_coord, area)

        region = BiomeRegion(
            name=name,
            biome_type=biome_type,
            climate_zone=climate_zone,
            area=area,
            center_coord=tuple(center_coord),
            border_coords=[tuple(c) for c in border_coords],
            climate=climate,
            status=BiomeStatus.STABLE,
        )
        self._regions[region.region_id] = region
        self._ecosystem_health[region.region_id] = EcosystemHealth()
        self.calculate_ecosystem_health(region.region_id)
        self._emit(
            BiomeEventKind.BIOME_CREATED,
            {"region_id": region.region_id, "name": name, "biome_type": biome_type.value},
        )
        return True, f"Region '{name}' registered", region

    def remove_region(self, region_id: str) -> Tuple[bool, str]:
        """Remove a region and its associated ecosystem health record."""
        if region_id not in self._regions:
            return False, f"Region '{region_id}' not found"
        region = self._regions.pop(region_id)
        self._ecosystem_health.pop(region_id, None)
        # Cancel any transitions tied to this region.
        dead_transitions = [
            tid for tid, tr in self._transitions.items() if tr.region_id == region_id
        ]
        for tid in dead_transitions:
            self._transitions.pop(tid, None)
        self._emit(
            BiomeEventKind.BIOME_CREATED,
            {"action": "remove", "region_id": region_id, "name": region.name},
        )
        return True, f"Region '{region.name}' removed"

    def get_region(self, region_id: str) -> Optional[BiomeRegion]:
        """Return the region with the given id, or None."""
        return self._regions.get(region_id)

    def list_regions(self) -> List[BiomeRegion]:
        """Return all registered regions."""
        return list(self._regions.values())

    def find_region_at_coord(self, coord: Tuple[float, float]) -> Optional[BiomeRegion]:
        """Return the region whose polygon contains the given coordinate."""
        for region in self._regions.values():
            if self._point_in_polygon(coord, region.border_coords):
                return region
        # Fall back to nearest center if no polygon encloses the point.
        nearest: Optional[BiomeRegion] = None
        nearest_dist = float("inf")
        for region in self._regions.values():
            dx = region.center_coord[0] - coord[0]
            dy = region.center_coord[1] - coord[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = region
        return nearest

    # ------------------------------------------------------------------
    # Flora and Fauna management
    # ------------------------------------------------------------------

    def register_flora_species(
        self,
        name: str,
        flora_type: FloraType,
        preferred_biomes: List[BiomeType],
        growth_rate: float = 0.1,
        rarity: float = 0.5,
        magical_properties: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FloraSpecies]]:
        """Register a new flora species definition."""
        if not name:
            return False, "Flora name must not be empty", None
        if growth_rate < 0:
            return False, "Growth rate must be non-negative", None
        if not 0.0 <= rarity <= 1.0:
            return False, "Rarity must be between 0 and 1", None
        species = FloraSpecies(
            name=name,
            flora_type=flora_type,
            preferred_biomes=list(preferred_biomes),
            growth_rate=growth_rate,
            rarity=rarity,
            magical_properties=dict(magical_properties or {}),
        )
        self._flora_species[species.species_id] = species
        self._emit(
            BiomeEventKind.FLORA_SPAWNED,
            {"species_id": species.species_id, "name": name, "flora_type": flora_type.value},
        )
        return True, f"Flora species '{name}' registered", species

    def register_fauna_species(
        self,
        name: str,
        fauna_type: FaunaType,
        preferred_biomes: List[BiomeType],
        population: int = 0,
        migration_pattern: Optional[Dict[str, Any]] = None,
        danger_level: float = 0.0,
    ) -> Tuple[bool, str, Optional[FaunaSpecies]]:
        """Register a new fauna species definition."""
        if not name:
            return False, "Fauna name must not be empty", None
        if population < 0:
            return False, "Population must be non-negative", None
        if not 0.0 <= danger_level <= 1.0:
            return False, "Danger level must be between 0 and 1", None
        species = FaunaSpecies(
            name=name,
            fauna_type=fauna_type,
            preferred_biomes=list(preferred_biomes),
            population=population,
            migration_pattern=dict(migration_pattern or {}),
            danger_level=danger_level,
        )
        self._fauna_species[species.species_id] = species
        self._emit(
            BiomeEventKind.FAUNA_MIGRATED,
            {"species_id": species.species_id, "name": name, "fauna_type": fauna_type.value},
        )
        return True, f"Fauna species '{name}' registered", species

    def remove_flora_species(self, species_id: str) -> Tuple[bool, str]:
        """Remove a flora species and detach it from all regions."""
        if species_id not in self._flora_species:
            return False, f"Flora species '{species_id}' not found"
        species = self._flora_species.pop(species_id)
        for region in self._regions.values():
            if species_id in region.flora_list:
                region.flora_list.remove(species_id)
        return True, f"Flora species '{species.name}' removed"

    def remove_fauna_species(self, species_id: str) -> Tuple[bool, str]:
        """Remove a fauna species and detach it from all regions."""
        if species_id not in self._fauna_species:
            return False, f"Fauna species '{species_id}' not found"
        species = self._fauna_species.pop(species_id)
        for region in self._regions.values():
            if species_id in region.fauna_list:
                region.fauna_list.remove(species_id)
        return True, f"Fauna species '{species.name}' removed"

    def list_flora(self) -> List[FloraSpecies]:
        """Return all registered flora species."""
        return list(self._flora_species.values())

    def list_fauna(self) -> List[FaunaSpecies]:
        """Return all registered fauna species."""
        return list(self._fauna_species.values())

    def spawn_flora_in_region(
        self,
        region_id: str,
        species_id: str,
        count: int = 1,
    ) -> Tuple[bool, str, Optional[BiomeRegion]]:
        """Attach a flora species to a region, marking it as present there."""
        region = self._regions.get(region_id)
        if region is None:
            return False, f"Region '{region_id}' not found", None
        if species_id not in self._flora_species:
            return False, f"Flora species '{species_id}' not found", None
        if count <= 0:
            return False, "Spawn count must be positive", None
        species = self._flora_species[species_id]
        # Species not suited to the biome still spawn but mark region degraded.
        if region.biome_type not in species.preferred_biomes:
            if region.status == BiomeStatus.STABLE:
                region.status = BiomeStatus.DEGRADED
        for _ in range(count):
            if species_id not in region.flora_list:
                region.flora_list.append(species_id)
        self._total_flora_spawned += count
        self._emit(
            BiomeEventKind.FLORA_SPAWNED,
            {"region_id": region_id, "species_id": species_id, "count": count},
        )
        self.calculate_ecosystem_health(region_id)
        return True, f"Spawned {count} flora '{species.name}' in '{region.name}'", region

    def migrate_fauna(
        self,
        species_id: str,
        from_region_id: str,
        to_region_id: str,
        count: int = 1,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Move a fauna species population between two regions."""
        if species_id not in self._fauna_species:
            return False, f"Fauna species '{species_id}' not found", None
        from_region = self._regions.get(from_region_id)
        to_region = self._regions.get(to_region_id)
        if from_region is None:
            return False, f"Source region '{from_region_id}' not found", None
        if to_region is None:
            return False, f"Target region '{to_region_id}' not found", None
        if count <= 0:
            return False, "Migration count must be positive", None
        species = self._fauna_species[species_id]
        if species_id not in from_region.fauna_list:
            return False, (
                f"Fauna '{species.name}' is not present in '{from_region.name}'"
            ), None
        if species_id not in to_region.fauna_list:
            to_region.fauna_list.append(species_id)
        # If the source region loses all species presence, remove it from list.
        if species.population <= count:
            from_region.fauna_list.remove(species_id)
        species.population = max(0, species.population - count)
        self._total_fauna_migrated += count
        migration_record: Dict[str, Any] = {
            "species_id": species_id,
            "species_name": species.name,
            "from_region": from_region_id,
            "to_region": to_region_id,
            "count": count,
        }
        self._emit(BiomeEventKind.FAUNA_MIGRATED, migration_record)
        self.calculate_ecosystem_health(from_region_id)
        self.calculate_ecosystem_health(to_region_id)
        return True, (
            f"Migrated {count} '{species.name}' from '{from_region.name}' "
            f"to '{to_region.name}'"
        ), migration_record

    # ------------------------------------------------------------------
    # Climate management
    # ------------------------------------------------------------------

    def set_climate(
        self,
        region_id: str,
        climate: ClimateData,
    ) -> Tuple[bool, str, Optional[ClimateData]]:
        """Replace the climate data for a region."""
        region = self._regions.get(region_id)
        if region is None:
            return False, f"Region '{region_id}' not found", None
        region.climate = climate
        self._emit(
            BiomeEventKind.CLIMATE_SHIFT,
            {"region_id": region_id, "climate": climate.to_dict()},
        )
        self.calculate_ecosystem_health(region_id)
        return True, f"Climate set for '{region.name}'", climate

    def get_climate(self, region_id: str) -> Optional[ClimateData]:
        """Return the climate data for a region, or None."""
        region = self._regions.get(region_id)
        if region is None:
            return None
        return region.climate

    def adjust_temperature(
        self,
        region_id: str,
        delta: float,
    ) -> Tuple[bool, str, Optional[ClimateData]]:
        """Shift the temperature range of a region by delta degrees."""
        region = self._regions.get(region_id)
        if region is None:
            return False, f"Region '{region_id}' not found", None
        temp = region.climate.temperature
        temp.min += delta
        temp.max += delta
        temp.average = (temp.min + temp.max) / 2.0
        self._emit(
            BiomeEventKind.CLIMATE_SHIFT,
            {"region_id": region_id, "temperature_delta": delta},
        )
        self.calculate_ecosystem_health(region_id)
        return True, f"Temperature adjusted by {delta} for '{region.name}'", region.climate

    def adjust_humidity(
        self,
        region_id: str,
        delta: float,
    ) -> Tuple[bool, str, Optional[ClimateData]]:
        """Shift the humidity range of a region by delta percent."""
        region = self._regions.get(region_id)
        if region is None:
            return False, f"Region '{region_id}' not found", None
        hum = region.climate.humidity
        hum.min = max(0.0, min(100.0, hum.min + delta))
        hum.max = max(0.0, min(100.0, hum.max + delta))
        hum.average = (hum.min + hum.max) / 2.0
        self._emit(
            BiomeEventKind.CLIMATE_SHIFT,
            {"region_id": region_id, "humidity_delta": delta},
        )
        self.calculate_ecosystem_health(region_id)
        return True, f"Humidity adjusted by {delta} for '{region.name}'", region.climate

    def apply_magical_density(
        self,
        region_id: str,
        density: float,
    ) -> Tuple[bool, str, Optional[ClimateData]]:
        """Set the magical density of a region, clamped to [0, 1]."""
        region = self._regions.get(region_id)
        if region is None:
            return False, f"Region '{region_id}' not found", None
        density = max(0.0, min(1.0, density))
        region.climate.magical_density = density
        if density > 0.5 and not self._config.enable_magical_biomes:
            region.status = BiomeStatus.CORRUPTED
        self._emit(
            BiomeEventKind.CLIMATE_SHIFT,
            {"region_id": region_id, "magical_density": density},
        )
        self.calculate_ecosystem_health(region_id)
        return True, f"Magical density set to {density} for '{region.name}'", region.climate

    # ------------------------------------------------------------------
    # Seasons
    # ------------------------------------------------------------------

    def set_season(self, season: Season) -> Tuple[bool, str, Season]:
        """Set the current season and reset elapsed time for it."""
        self._current_season = season
        self._season_elapsed = 0.0
        self._season_counter += 1
        self._apply_seasonal_modifiers(season)
        self._emit(
            BiomeEventKind.SEASON_CHANGED,
            {"season": season.value, "counter": self._season_counter},
        )
        return True, f"Season set to {season.value}", season

    def advance_season(self) -> Tuple[bool, str, Season]:
        """Advance to the next season in the configured cycle."""
        if not self._config.enable_seasonal_cycles:
            return False, "Seasonal cycles are disabled", self._current_season
        order = self._season_order_for(self._current_season)
        if not order:
            order = _DEFAULT_SEASON_ORDER
        try:
            idx = order.index(self._current_season)
        except ValueError:
            idx = -1
        next_season = order[(idx + 1) % len(order)]
        return self.set_season(next_season)

    def get_season(self) -> Season:
        """Return the current season."""
        return self._current_season

    def get_seasonal_pattern(self, season: Season) -> Optional[SeasonalPattern]:
        """Return the seasonal pattern for a season, or None if unset."""
        return self._seasonal_patterns.get(season)

    def register_seasonal_pattern(
        self,
        season: Season,
        duration_days: float,
        temperature_modifier: float,
        humidity_modifier: float,
        flora_multiplier: float,
        fauna_multiplier: float,
    ) -> Tuple[bool, str, Optional[SeasonalPattern]]:
        """Register or replace a seasonal pattern for a season."""
        if duration_days <= 0:
            return False, "Duration must be positive", None
        pattern = SeasonalPattern(
            season=season,
            duration_days=duration_days,
            temperature_modifier=temperature_modifier,
            humidity_modifier=humidity_modifier,
            flora_multiplier=flora_multiplier,
            fauna_multiplier=fauna_multiplier,
        )
        self._seasonal_patterns[season] = pattern
        return True, f"Seasonal pattern registered for {season.value}", pattern

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def start_transition(
        self,
        region_id: str,
        to_biome: BiomeType,
        transition_type: TransitionType = TransitionType.GRADUAL,
        duration: Optional[float] = None,
        trigger_reason: str = "",
    ) -> Tuple[bool, str, Optional[BiomeTransition]]:
        """Begin a biome transition for a region."""
        region = self._regions.get(region_id)
        if region is None:
            return False, f"Region '{region_id}' not found", None
        if region.biome_type == to_biome:
            return False, "Region is already that biome type", None
        # Reject if a transition is already in progress for this region.
        for tr in self._transitions.values():
            if tr.region_id == region_id and tr.progress < 1.0:
                return False, "Region already has an active transition", None
        if duration is None or duration <= 0:
            duration = 100.0
            if transition_type == TransitionType.ABRUPT:
                duration = 5.0
            elif transition_type == TransitionType.MAGICAL:
                duration = 20.0
            elif transition_type == TransitionType.SEASONAL:
                duration = self._config.season_duration_base
        transition = BiomeTransition(
            region_id=region_id,
            from_biome=region.biome_type,
            to_biome=to_biome,
            transition_type=transition_type,
            duration=duration,
            progress=0.0,
            trigger_reason=trigger_reason,
        )
        self._transitions[transition.transition_id] = transition
        region.status = BiomeStatus.TRANSITIONING
        self._total_transitions_started += 1
        self._emit(
            BiomeEventKind.BIOME_TRANSITION,
            {"transition_id": transition.transition_id, "region_id": region_id,
             "from": region.biome_type.value, "to": to_biome.value,
             "type": transition_type.value},
        )
        return True, f"Transition started for '{region.name}'", transition

    def advance_transition(
        self,
        transition_id: str,
        dt: float,
    ) -> Tuple[bool, str, Optional[BiomeTransition]]:
        """Advance a single transition by dt seconds of simulated time."""
        transition = self._transitions.get(transition_id)
        if transition is None:
            return False, f"Transition '{transition_id}' not found", None
        if transition.progress >= 1.0:
            return True, "Transition already complete", transition
        if dt <= 0:
            return True, "No time advanced", transition
        step = (dt / max(transition.duration, self.EPSILON)) * self._config.transition_speed
        transition.progress = min(1.0, transition.progress + step)
        region = self._regions.get(transition.region_id)
        if region is not None:
            region.transition_progress = transition.progress
            self.calculate_ecosystem_health(transition.region_id)
        if transition.progress >= 1.0:
            self._finalize_transition(transition)
        return True, f"Transition advanced to {transition.progress:.3f}", transition

    def complete_transition(
        self,
        transition_id: str,
    ) -> Tuple[bool, str, Optional[BiomeRegion]]:
        """Force a transition to completion immediately."""
        transition = self._transitions.get(transition_id)
        if transition is None:
            return False, f"Transition '{transition_id}' not found", None
        transition.progress = 1.0
        region = self._finalize_transition(transition)
        return True, f"Transition '{transition_id}' completed", region

    def cancel_transition(self, transition_id: str) -> Tuple[bool, str]:
        """Cancel an in-progress transition, leaving the region unchanged."""
        transition = self._transitions.get(transition_id)
        if transition is None:
            return False, f"Transition '{transition_id}' not found"
        region = self._regions.get(transition.region_id)
        if region is not None and region.status == BiomeStatus.TRANSITIONING:
            region.status = BiomeStatus.STABLE
            region.transition_progress = 0.0
        self._transitions.pop(transition_id, None)
        self._emit(
            BiomeEventKind.BIOME_TRANSITION,
            {"action": "cancel", "transition_id": transition_id},
        )
        return True, f"Transition '{transition_id}' cancelled"

    def list_transitions(self) -> List[BiomeTransition]:
        """Return all transitions (active and completed)."""
        return list(self._transitions.values())

    # ------------------------------------------------------------------
    # Ecosystem
    # ------------------------------------------------------------------

    def calculate_ecosystem_health(self, region_id: str) -> Optional[EcosystemHealth]:
        """Compute and store ecosystem health for a region."""
        region = self._regions.get(region_id)
        if region is None:
            return None
        flora_count = len(region.flora_list)
        fauna_count = len(region.fauna_list)

        biodiversity = min(1.0, (flora_count * 0.12) + (fauna_count * 0.10))

        status_stability: Dict[BiomeStatus, float] = {
            BiomeStatus.FLOURISHING: 0.9,
            BiomeStatus.STABLE: 0.7,
            BiomeStatus.FROZEN: 0.5,
            BiomeStatus.TRANSITIONING: 0.4,
            BiomeStatus.DEGRADED: 0.3,
            BiomeStatus.CORRUPTED: 0.2,
        }
        stability = status_stability.get(region.status, 0.5)
        # Penalize stability when biodiversity is critically low.
        if biodiversity < self.COLLAPSE_BIODIVERSITY_THRESHOLD:
            stability *= 0.5

        climate = region.climate
        abundance = (
            min(1.0, climate.rainfall / 2000.0) * 0.4
            + min(1.0, climate.sunlight_hours / 12.0) * 0.3
            + (1.0 - min(1.0, climate.magical_density)) * 0.3
        )
        abundance = max(0.0, min(1.0, abundance))

        pollution = max(0.0, min(1.0, (1.0 - stability) * 0.6 + max(0.0, 0.5 - abundance)))

        corruption_base = _BIOME_CORRUPTION_BASE.get(region.biome_type, 0.05)
        corruption = max(0.0, min(1.0, corruption_base * 0.5 + climate.magical_density * 0.5))

        health = EcosystemHealth(
            biodiversity_index=biodiversity,
            stability_score=stability,
            resource_abundance=abundance,
            pollution_level=pollution,
            corruption_level=corruption,
        )
        previous = self._ecosystem_health.get(region_id)
        self._ecosystem_health[region_id] = health

        # Emit collapse or recovery events when thresholds are crossed.
        if previous is not None:
            was_collapsed = (
                previous.stability_score < self.COLLAPSE_STABILITY_THRESHOLD
                or previous.biodiversity_index < self.COLLAPSE_BIODIVERSITY_THRESHOLD
            )
            is_collapsed = (
                health.stability_score < self.COLLAPSE_STABILITY_THRESHOLD
                or health.biodiversity_index < self.COLLAPSE_BIODIVERSITY_THRESHOLD
            )
            if is_collapsed and not was_collapsed:
                self._total_ecosystem_collapses += 1
                region.status = BiomeStatus.DEGRADED
                self._emit(
                    BiomeEventKind.ECOSYSTEM_COLLAPSE,
                    {"region_id": region_id, "health": health.to_dict()},
                )
            elif not is_collapsed and was_collapsed:
                self._total_ecosystem_recoveries += 1
                if region.status == BiomeStatus.DEGRADED:
                    region.status = BiomeStatus.STABLE
                self._emit(
                    BiomeEventKind.ECOSYSTEM_RECOVER,
                    {"region_id": region_id, "health": health.to_dict()},
                )
        return health

    def degrade_ecosystem(
        self,
        region_id: str,
        amount: float = 0.1,
    ) -> Tuple[bool, str, Optional[EcosystemHealth]]:
        """Reduce ecosystem stability and increase pollution for a region."""
        region = self._regions.get(region_id)
        if region is None:
            return False, f"Region '{region_id}' not found", None
        health = self._ecosystem_health.get(region_id) or EcosystemHealth()
        health.stability_score = max(0.0, health.stability_score - amount)
        health.pollution_level = min(1.0, health.pollution_level + amount * 0.5)
        health.corruption_level = min(1.0, health.corruption_level + amount * 0.3)
        self._ecosystem_health[region_id] = health
        if health.stability_score < 0.4 and region.status == BiomeStatus.STABLE:
            region.status = BiomeStatus.DEGRADED
        self._emit(
            BiomeEventKind.ECOSYSTEM_COLLAPSE,
            {"action": "degrade", "region_id": region_id, "amount": amount},
        )
        return True, f"Ecosystem degraded by {amount} for '{region.name}'", health

    def restore_ecosystem(
        self,
        region_id: str,
        amount: float = 0.1,
    ) -> Tuple[bool, str, Optional[EcosystemHealth]]:
        """Improve ecosystem stability and reduce pollution for a region."""
        region = self._regions.get(region_id)
        if region is None:
            return False, f"Region '{region_id}' not found", None
        health = self._ecosystem_health.get(region_id) or EcosystemHealth()
        health.stability_score = min(1.0, health.stability_score + amount)
        health.pollution_level = max(0.0, health.pollution_level - amount * 0.5)
        health.corruption_level = max(0.0, health.corruption_level - amount * 0.3)
        self._ecosystem_health[region_id] = health
        if health.stability_score > 0.8:
            region.status = BiomeStatus.FLOURISHING
        elif health.stability_score > 0.5 and region.status == BiomeStatus.DEGRADED:
            region.status = BiomeStatus.STABLE
        self._emit(
            BiomeEventKind.ECOSYSTEM_RECOVER,
            {"action": "restore", "region_id": region_id, "amount": amount},
        )
        return True, f"Ecosystem restored by {amount} for '{region.name}'", health

    def detect_ecosystem_collapse(self) -> Dict[str, Any]:
        """Scan all regions and return those whose ecosystem has collapsed."""
        collapsed: List[Dict[str, Any]] = []
        for region_id, region in self._regions.items():
            health = self.calculate_ecosystem_health(region_id)
            if health is None:
                continue
            if (
                health.stability_score < self.COLLAPSE_STABILITY_THRESHOLD
                or health.biodiversity_index < self.COLLAPSE_BIODIVERSITY_THRESHOLD
            ):
                collapsed.append({
                    "region_id": region_id,
                    "name": region.name,
                    "biome_type": region.biome_type.value,
                    "health": health.to_dict(),
                })
        return {
            "collapsed_count": len(collapsed),
            "collapsed_regions": collapsed,
            "total_regions": len(self._regions),
        }

    # ------------------------------------------------------------------
    # Queries and helpers
    # ------------------------------------------------------------------

    def get_biome_distribution(self) -> Dict[str, Any]:
        """Return the area-weighted distribution of biome types."""
        totals: Dict[str, float] = {}
        total_area = 0.0
        for region in self._regions.values():
            key = region.biome_type.value
            totals[key] = totals.get(key, 0.0) + region.area
            total_area += region.area
        distribution: Dict[str, Dict[str, float]] = {}
        for key, area in totals.items():
            fraction = (area / total_area) if total_area > 0 else 0.0
            distribution[key] = {
                "area": round(area, 4),
                "fraction": round(fraction, 6),
            }
        return {
            "distribution": distribution,
            "total_area": round(total_area, 4),
            "region_count": len(self._regions),
        }

    def get_climate_summary(self) -> Dict[str, Any]:
        """Return aggregate climate statistics across all regions."""
        if not self._regions:
            return {"region_count": 0, "averages": {}}
        temps: List[float] = []
        humids: List[float] = []
        rainfalls: List[float] = []
        winds: List[float] = []
        sunlights: List[float] = []
        pressures: List[float] = []
        magics: List[float] = []
        for region in self._regions.values():
            c = region.climate
            temps.append(float(c.temperature.average))
            humids.append(float(c.humidity.average))
            rainfalls.append(c.rainfall)
            winds.append(c.wind_speed)
            sunlights.append(c.sunlight_hours)
            pressures.append(c.air_pressure)
            magics.append(c.magical_density)

        def _avg(values: List[float]) -> float:
            return round(sum(values) / len(values), 4) if values else 0.0

        return {
            "region_count": len(self._regions),
            "averages": {
                "temperature": _avg(temps),
                "humidity": _avg(humids),
                "rainfall": _avg(rainfalls),
                "wind_speed": _avg(winds),
                "sunlight_hours": _avg(sunlights),
                "air_pressure": _avg(pressures),
                "magical_density": _avg(magics),
            },
            "current_season": self._current_season.value,
        }

    def suggest_biome_for_coords(self, coord: Tuple[float, float]) -> BiomeType:
        """Deterministically suggest a biome type for a coordinate.

        Uses latitude (the y component) and a sinusoidal elevation term so
        that the same coordinate always yields the same suggestion.
        """
        x, y = coord
        abs_y = abs(y)
        elevation = (math.sin(x * 0.1) + math.cos(y * 0.1)) * 50.0
        magical_hash = (math.sin((x + y) * 0.07) + 1.0) / 2.0

        if magical_hash > 0.92 and self._config.enable_magical_biomes:
            return BiomeType.ETHEREAL
        if elevation > 40.0:
            return BiomeType.MOUNTAIN
        if abs_y > 80.0:
            return BiomeType.ARCTIC
        if abs_y > 60.0:
            return BiomeType.TUNDRA
        if abs_y > 38.0:
            return BiomeType.TEMPERATE_FOREST
        if abs_y > 25.0:
            if magical_hash > 0.5:
                return BiomeType.GRASSLAND
            return BiomeType.SAVANNA
        return BiomeType.TROPICAL_RAINFOREST

    def auto_generate_region(
        self,
        coord: Tuple[float, float],
        name: Optional[str] = None,
        biome_type: Optional[BiomeType] = None,
        area: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[BiomeRegion]]:
        """Generate and register a region centered on a coordinate."""
        if biome_type is None:
            biome_type = self.suggest_biome_for_coords(coord)
        if area is None or area <= 0:
            area = 800.0
        climate_zone = self._climate_zone_for_coord(coord)
        if name is None:
            short_id = uuid.uuid4().hex[:6]
            name = f"Auto {biome_type.value.title()} {short_id}"
        border_coords = self._build_default_polygon(coord, area)
        return self.register_region(
            name=name,
            biome_type=biome_type,
            climate_zone=climate_zone,
            area=area,
            center_coord=coord,
            border_coords=border_coords,
            climate=None,
        )

    def optimize_biome_layout(self) -> Dict[str, Any]:
        """Detect overlapping regions and nudge them apart.

        Returns a report describing how many overlaps were found and how
        many regions were adjusted. This is a lightweight pass intended to
        keep generated layouts sane rather than a full packing solver.
        """
        regions = list(self._regions.values())
        overlaps: List[Dict[str, Any]] = []
        adjustments = 0
        # Compare each pair of regions by distance between centers.
        for i in range(len(regions)):
            for j in range(i + 1, len(regions)):
                a = regions[i]
                b = regions[j]
                dx = b.center_coord[0] - a.center_coord[0]
                dy = b.center_coord[1] - a.center_coord[1]
                dist = math.sqrt(dx * dx + dy * dy)
                # Approximate minimum separation from area-derived radii.
                radius_a = math.sqrt(max(a.area, self.EPSILON) / math.pi)
                radius_b = math.sqrt(max(b.area, self.EPSILON) / math.pi)
                min_dist = (radius_a + radius_b) * 0.6
                if dist < min_dist and dist > self.EPSILON:
                    overlaps.append({
                        "region_a": a.region_id,
                        "region_b": b.region_id,
                        "distance": round(dist, 4),
                        "min_distance": round(min_dist, 4),
                    })
                    # Nudge region b away from region a.
                    push = (min_dist - dist) / 2.0
                    nx = dx / dist
                    ny = dy / dist
                    new_x = b.center_coord[0] + nx * push
                    new_y = b.center_coord[1] + ny * push
                    b.center_coord = (new_x, new_y)
                    b.border_coords = self._build_default_polygon(b.center_coord, b.area)
                    adjustments += 1
        return {
            "region_count": len(regions),
            "overlap_count": len(overlaps),
            "adjustments": adjustments,
            "overlaps": overlaps,
        }

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    def tick(self, dt: float = 0.1) -> Dict[str, Any]:
        """Advance the whole system by dt seconds of simulated time."""
        if dt <= 0:
            return {"tick": self._tick_count, "skipped": True, "reason": "dt <= 0"}
        self._tick_count += 1

        # Advance seasonal clock.
        season_advanced = False
        if self._config.enable_seasonal_cycles:
            self._season_elapsed += dt
            pattern = self._seasonal_patterns.get(self._current_season)
            duration = (
                pattern.duration_days if pattern else self._config.season_duration_base
            )
            if self._season_elapsed >= duration:
                self.advance_season()
                season_advanced = True

        # Advance transitions.
        transitions_advanced = 0
        transitions_completed = 0
        for transition_id in list(self._transitions.keys()):
            transition = self._transitions.get(transition_id)
            if transition is None or transition.progress >= 1.0:
                continue
            step = (dt / max(transition.duration, self.EPSILON)) * self._config.transition_speed
            transition.progress = min(1.0, transition.progress + step)
            region = self._regions.get(transition.region_id)
            if region is not None:
                region.transition_progress = transition.progress
            transitions_advanced += 1
            if transition.progress >= 1.0:
                self._finalize_transition(transition)
                transitions_completed += 1

        # Spawn flora and migrate fauna probabilistically.
        flora_spawned = self._tick_flora_spawns(dt)
        fauna_migrated = self._tick_fauna_migrations(dt)

        # Recalculate ecosystem health for all regions.
        for region_id in list(self._regions.keys()):
            self.calculate_ecosystem_health(region_id)

        collapse_report = self.detect_ecosystem_collapse()

        return {
            "tick": self._tick_count,
            "dt": dt,
            "season": self._current_season.value,
            "season_advanced": season_advanced,
            "transitions_advanced": transitions_advanced,
            "transitions_completed": transitions_completed,
            "flora_spawned": flora_spawned,
            "fauna_migrated": fauna_migrated,
            "ecosystem_collapses": collapse_report["collapsed_count"],
            "region_count": len(self._regions),
        }

    def get_status(self) -> Dict[str, Any]:
        """Return a concise status report for monitoring."""
        active_transitions = sum(
            1 for t in self._transitions.values() if t.progress < 1.0
        )
        return {
            "initialized": self._seeded,
            "tick_count": self._tick_count,
            "current_season": self._current_season.value,
            "season_elapsed": round(self._season_elapsed, 4),
            "region_count": len(self._regions),
            "flora_species_count": len(self._flora_species),
            "fauna_species_count": len(self._fauna_species),
            "active_transitions": active_transitions,
            "total_transitions_started": self._total_transitions_started,
            "total_transitions_completed": self._total_transitions_completed,
            "total_flora_spawned": self._total_flora_spawned,
            "total_fauna_migrated": self._total_fauna_migrated,
            "total_ecosystem_collapses": self._total_ecosystem_collapses,
            "total_ecosystem_recoveries": self._total_ecosystem_recoveries,
        }

    def get_stats(self) -> ClimateBiomeStats:
        """Return rolled-up statistics for the system."""
        health_scores = [
            h.stability_score for h in self._ecosystem_health.values()
        ]
        avg_health = (
            sum(health_scores) / len(health_scores) if health_scores else 0.0
        )
        active_seasons = 1 if self._config.enable_seasonal_cycles else 0
        return ClimateBiomeStats(
            total_regions=len(self._regions),
            total_transitions=len(self._transitions),
            total_flora_species=len(self._flora_species),
            total_fauna_species=len(self._fauna_species),
            active_seasons=active_seasons,
            ecosystem_health_avg=avg_health,
        )

    def get_snapshot(self) -> ClimateBiomeSnapshot:
        """Return a point-in-time snapshot of the whole system."""
        global_health = EcosystemHealth()
        scores = list(self._ecosystem_health.values())
        if scores:
            global_health.biodiversity_index = sum(
                s.biodiversity_index for s in scores
            ) / len(scores)
            global_health.stability_score = sum(
                s.stability_score for s in scores
            ) / len(scores)
            global_health.resource_abundance = sum(
                s.resource_abundance for s in scores
            ) / len(scores)
            global_health.pollution_level = sum(
                s.pollution_level for s in scores
            ) / len(scores)
            global_health.corruption_level = sum(
                s.corruption_level for s in scores
            ) / len(scores)
        return ClimateBiomeSnapshot(
            regions=list(self._regions.values()),
            transitions=list(self._transitions.values()),
            season=self._current_season,
            ecosystem_health=global_health,
        )

    def get_config(self) -> ClimateBiomeConfig:
        """Return the current configuration."""
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, ClimateBiomeConfig]:
        """Update one or more configuration fields by keyword."""
        valid_fields = {
            "season_duration_base",
            "transition_speed",
            "enable_magical_biomes",
            "enable_seasonal_cycles",
            "flora_spawn_rate",
            "fauna_migration_rate",
        }
        unknown = [k for k in kwargs if k not in valid_fields]
        if unknown:
            return False, f"Unknown config fields: {', '.join(unknown)}", self._config
        for key, value in kwargs.items():
            setattr(self._config, key, value)
        return True, f"Config updated: {len(kwargs)} field(s)", self._config

    def list_events(self) -> List[BiomeEvent]:
        """Return all recorded events, oldest first."""
        return list(self._events)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: BiomeEventKind, payload: Optional[Dict[str, Any]] = None) -> None:
        """Record an event, capping the total stored to MAX_EVENTS."""
        event = BiomeEvent(kind=kind, payload=dict(payload or {}))
        self._events.append(event)
        if len(self._events) > self.MAX_EVENTS:
            # Drop the oldest entries to stay within the cap.
            overflow = len(self._events) - self.MAX_EVENTS
            del self._events[:overflow]

    def _build_default_climate(
        self,
        biome_type: BiomeType,
        climate_zone: ClimateZone,
    ) -> ClimateData:
        """Construct a baseline ClimateData from the lookup tables."""
        defaults = _BIOME_CLIMATE_DEFAULTS.get(biome_type, {
            "t_min": 5.0, "t_max": 25.0, "h_min": 40.0, "h_max": 60.0,
            "rainfall": 500.0, "wind": 3.0, "sun": 7.0, "pressure": 101.3,
            "magic": 0.05,
        })
        zone_offset = _CLIMATE_ZONE_TEMP_OFFSET.get(climate_zone, 0.0)
        temp = TemperatureRange(
            min=defaults["t_min"] + zone_offset,
            max=defaults["t_max"] + zone_offset,
        )
        humidity = HumidityRange(
            min=defaults["h_min"],
            max=defaults["h_max"],
        )
        magical = defaults["magic"]
        if climate_zone == ClimateZone.MAGICAL:
            magical = min(1.0, magical + 0.2)
        elif climate_zone == ClimateZone.VOID:
            magical = min(1.0, magical + 0.4)
        return ClimateData(
            temperature=temp,
            humidity=humidity,
            rainfall=defaults["rainfall"],
            wind_speed=defaults["wind"],
            sunlight_hours=defaults["sun"],
            air_pressure=defaults["pressure"],
            magical_density=magical,
        )

    def _build_default_polygon(
        self,
        center: Tuple[float, float],
        area: float,
    ) -> List[Tuple[float, float]]:
        """Build a roughly circular octagonal polygon for a region."""
        radius = math.sqrt(max(area, self.EPSILON) / math.pi)
        polygon: List[Tuple[float, float]] = []
        for i in range(8):
            angle = (2.0 * math.pi * i) / 8.0
            px = center[0] + radius * math.cos(angle)
            py = center[1] + radius * math.sin(angle)
            polygon.append((px, py))
        return polygon

    def _point_in_polygon(
        self,
        point: Tuple[float, float],
        polygon: List[Tuple[float, float]],
    ) -> bool:
        """Ray-casting point-in-polygon test."""
        if len(polygon) < 3:
            return False
        x, y = point
        inside = False
        n = len(polygon)
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersect = (
                (yi > y) != (yj > y)
            ) and (
                x < (xj - xi) * (y - yi) / (yj - yi + self.EPSILON) + xi
            )
            if intersect:
                inside = not inside
            j = i
        return inside

    def _climate_zone_for_coord(self, coord: Tuple[float, float]) -> ClimateZone:
        """Pick a climate zone from the latitude (y) of a coordinate."""
        abs_y = abs(coord[1])
        if abs_y > 80.0:
            return ClimateZone.POLAR
        if abs_y > 60.0:
            return ClimateZone.CONTINENTAL
        if abs_y > 38.0:
            return ClimateZone.TEMPERATE
        if abs_y > 25.0:
            return ClimateZone.SUBTROPICAL
        if abs_y > 10.0:
            return ClimateZone.TROPICAL
        return ClimateZone.EQUATORIAL

    def _season_order_for(self, season: Season) -> List[Season]:
        """Return the cycle order containing the given season."""
        tropical_cycle = [Season.WET, Season.DRY]
        monsoon_cycle = [Season.MONSOON, Season.DRY]
        frost_cycle = [Season.FROST, Season.SPRING, Season.SUMMER, Season.AUTUMN]
        harvest_cycle = [Season.HARVEST, Season.SPRING, Season.SUMMER, Season.WINTER]
        eclipse_cycle = [Season.ECLIPSE, Season.SPRING, Season.SUMMER]
        cycles = [
            _DEFAULT_SEASON_ORDER,
            tropical_cycle,
            monsoon_cycle,
            frost_cycle,
            harvest_cycle,
            eclipse_cycle,
        ]
        for cycle in cycles:
            if season in cycle:
                return cycle
        return _DEFAULT_SEASON_ORDER

    def _apply_seasonal_modifiers(self, season: Season) -> None:
        """Apply the seasonal pattern modifiers to every region's climate."""
        pattern = self._seasonal_patterns.get(season)
        if pattern is None:
            return
        for region in self._regions.values():
            temp = region.climate.temperature
            hum = region.climate.humidity
            temp.min += pattern.temperature_modifier
            temp.max += pattern.temperature_modifier
            temp.average = (temp.min + temp.max) / 2.0
            hum.min = max(0.0, min(100.0, hum.min + pattern.humidity_modifier))
            hum.max = max(0.0, min(100.0, hum.max + pattern.humidity_modifier))
            hum.average = (hum.min + hum.max) / 2.0
            self.calculate_ecosystem_health(region.region_id)

    def _finalize_transition(self, transition: BiomeTransition) -> Optional[BiomeRegion]:
        """Apply the target biome type to the region and refresh its climate."""
        region = self._regions.get(transition.region_id)
        if region is None:
            return None
        region.biome_type = transition.to_biome
        region.transition_progress = 1.0
        region.status = BiomeStatus.STABLE
        # Refresh climate to match the new biome type.
        region.climate = self._build_default_climate(
            transition.to_biome, region.climate_zone
        )
        self._total_transitions_completed += 1
        self._emit(
            BiomeEventKind.BIOME_TRANSITION,
            {"action": "complete", "transition_id": transition.transition_id,
             "region_id": region.region_id, "new_biome": transition.to_biome.value},
        )
        self.calculate_ecosystem_health(region.region_id)
        return region

    def _tick_flora_spawns(self, dt: float) -> int:
        """Probabilistically spawn flora into suitable regions each tick."""
        spawned = 0
        rate = self._config.flora_spawn_rate * dt
        if rate <= 0 or not self._flora_species:
            return 0
        species_list = list(self._flora_species.values())
        for region in self._regions.values():
            for species in species_list:
                # Only spawn where the biome suits the species.
                if region.biome_type not in species.preferred_biomes:
                    continue
                # Deterministic-ish spawn probability from a coordinate hash
                # so results are stable for a given region and tick count.
                spawn_roll = (
                    math.sin(
                        (hash(region.region_id) & 0xFFFF) * 0.001
                        + self._tick_count * 0.05
                        + len(species.species_id) * 0.1
                    )
                    + 1.0
                ) / 2.0
                if spawn_roll < rate * 10.0:
                    if species.species_id not in region.flora_list:
                        region.flora_list.append(species.species_id)
                        spawned += 1
                        self._total_flora_spawned += 1
        if spawned:
            self._emit(
                BiomeEventKind.FLORA_SPAWNED,
                {"action": "tick", "count": spawned},
            )
        return spawned

    def _tick_fauna_migrations(self, dt: float) -> int:
        """Probabilistically migrate fauna between neighboring regions."""
        migrated = 0
        rate = self._config.fauna_migration_rate * dt
        if rate <= 0 or len(self._regions) < 2:
            return 0
        regions = list(self._regions.values())
        for region in regions:
            for species_id in list(region.fauna_list):
                species = self._fauna_species.get(species_id)
                if species is None:
                    continue
                migrate_roll = (
                    math.sin(
                        (hash(species_id) & 0xFFFF) * 0.001
                        + self._tick_count * 0.07
                    )
                    + 1.0
                ) / 2.0
                if migrate_roll >= rate * 10.0:
                    continue
                # Find a nearby region whose biome suits the species.
                best_target: Optional[BiomeRegion] = None
                best_dist = float("inf")
                for other in regions:
                    if other.region_id == region.region_id:
                        continue
                    if other.biome_type not in species.preferred_biomes:
                        continue
                    dx = other.center_coord[0] - region.center_coord[0]
                    dy = other.center_coord[1] - region.center_coord[1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < best_dist:
                        best_dist = dist
                        best_target = other
                if best_target is None:
                    continue
                if species_id not in best_target.fauna_list:
                    best_target.fauna_list.append(species_id)
                migrated += 1
                self._total_fauna_migrated += 1
        if migrated:
            self._emit(
                BiomeEventKind.FAUNA_MIGRATED,
                {"action": "tick", "count": migrated},
            )
        return migrated

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _load_default_seasonal_patterns(self) -> None:
        """Populate seasonal patterns for every season."""
        defaults = [
            (Season.SPRING, 30.0, 2.0, 5.0, 1.3, 1.2),
            (Season.SUMMER, 30.0, 6.0, -5.0, 1.1, 1.1),
            (Season.AUTUMN, 30.0, -3.0, -2.0, 0.8, 0.9),
            (Season.WINTER, 30.0, -10.0, -8.0, 0.4, 0.6),
            (Season.MONSOON, 45.0, -1.0, 25.0, 1.4, 0.8),
            (Season.DRY, 45.0, 4.0, -20.0, 0.6, 0.7),
            (Season.WET, 60.0, 0.0, 20.0, 1.5, 1.0),
            (Season.ECLIPSE, 15.0, -8.0, 0.0, 0.3, 0.4),
            (Season.HARVEST, 40.0, -2.0, -3.0, 1.2, 1.3),
            (Season.FROST, 35.0, -12.0, -5.0, 0.3, 0.5),
        ]
        for season, dur, temp_mod, hum_mod, flora_mul, fauna_mul in defaults:
            self._seasonal_patterns[season] = SeasonalPattern(
                season=season,
                duration_days=dur,
                temperature_modifier=temp_mod,
                humidity_modifier=hum_mod,
                flora_multiplier=flora_mul,
                fauna_multiplier=fauna_mul,
            )

    def _load_seed_data(self) -> None:
        """Create the starting set of regions, flora, and fauna species."""
        # -- Flora species -------------------------------------------------
        flora_defs = [
            ("Oakheart Tree", FloraType.TREE,
             [BiomeType.TEMPERATE_FOREST, BiomeType.GRASSLAND],
             0.08, 0.3, {"wood_quality": 0.8, "lifespan_years": 200}),
            ("Sunbarrel Cactus", FloraType.CACTUS,
             [BiomeType.DESERT, BiomeType.SAVANNA],
             0.05, 0.4, {"water_storage": 0.9}),
            ("Mosswhisper Moss", FloraType.MOSS,
             [BiomeType.BOREAL_FOREST, BiomeType.MOUNTAIN, BiomeType.WETLAND],
             0.12, 0.5, {"insulation": 0.6}),
            ("Lotusveil Flower", FloraType.FLOWER,
             [BiomeType.WETLAND, BiomeType.TROPICAL_RAINFOREST],
             0.15, 0.6, {"fragrance": 0.9, "medicinal": 0.7}),
            ("Emberroot Fungus", FloraType.FUNGUS,
             [BiomeType.VOLCANIC, BiomeType.UNDERGROUND],
             0.2, 0.7, {"heat_resistance": 1.0, "glow": 0.8}),
            ("Crystalsong Vine", FloraType.VINE,
             [BiomeType.CRYSTAL, BiomeType.ETHEREAL],
             0.1, 0.85, {"resonance": 0.95, "magical_conductivity": 0.9}),
            ("Managrass", FloraType.GRASS,
             [BiomeType.GRASSLAND, BiomeType.ETHEREAL, BiomeType.SKY_ISLAND],
             0.18, 0.65, {"mana_yield": 0.8}),
            ("Glowcap", FloraType.FUNGUS,
             [BiomeType.UNDERGROUND, BiomeType.FUNGAL],
             0.22, 0.5, {"glow": 1.0, "spore_radius": 5.0}),
            ("Skypetal Blossom", FloraType.MAGICAL_PLANT,
             [BiomeType.SKY_ISLAND, BiomeType.ETHEREAL],
             0.14, 0.9, {"levitation": 0.85, "wind_ride": 0.7}),
            ("Shadowthorn Shrub", FloraType.SHRUB,
             [BiomeType.SHADOW, BiomeType.CORRUPT],
             0.09, 0.75, {"thorns": 0.9, "curse_ward": 0.6}),
        ]
        flora_ids: Dict[str, str] = {}
        for name, ftype, biomes, growth, rarity, magic in flora_defs:
            ok, _, species = self.register_flora_species(
                name=name,
                flora_type=ftype,
                preferred_biomes=biomes,
                growth_rate=growth,
                rarity=rarity,
                magical_properties=magic,
            )
            if ok and species is not None:
                flora_ids[name] = species.species_id

        # -- Fauna species -------------------------------------------------
        fauna_defs = [
            ("Forest Stag", FaunaType.MAMMAL,
             [BiomeType.TEMPERATE_FOREST, BiomeType.GRASSLAND],
             120, {"seasonal": True, "distance": 50.0}, 0.1),
            ("Sandrunner Lizard", FaunaType.REPTILE,
             [BiomeType.DESERT, BiomeType.SAVANNA],
             200, {"seasonal": False, "distance": 10.0}, 0.2),
            ("Mountain Hawk", FaunaType.BIRD,
             [BiomeType.MOUNTAIN, BiomeType.GRASSLAND],
             60, {"seasonal": True, "distance": 120.0}, 0.3),
            ("Marshfrog", FaunaType.AMPHIBIAN,
             [BiomeType.WETLAND, BiomeType.TROPICAL_RAINFOREST],
             400, {"seasonal": True, "distance": 5.0}, 0.05),
            ("Lavascale Drake", FaunaType.MAGICAL_CREATURE,
             [BiomeType.VOLCANIC, BiomeType.MOUNTAIN],
             15, {"seasonal": False, "distance": 80.0}, 0.8),
            ("Crystalwing Moth", FaunaType.INSECT,
             [BiomeType.CRYSTAL, BiomeType.ETHEREAL],
             300, {"seasonal": True, "distance": 30.0}, 0.15),
            ("River Otter", FaunaType.MAMMAL,
             [BiomeType.WETLAND, BiomeType.COASTAL],
             80, {"seasonal": False, "distance": 20.0}, 0.1),
            ("Voidstalker", FaunaType.UNDEAD,
             [BiomeType.SHADOW, BiomeType.CORRUPT],
             25, {"nocturnal": True, "distance": 60.0}, 0.9),
            ("Storm Elemental", FaunaType.ELEMENTAL,
             [BiomeType.SKY_ISLAND, BiomeType.MOUNTAIN],
             10, {"storm_bound": True, "distance": 200.0}, 0.7),
            ("Phoenix", FaunaType.MYTHICAL,
             [BiomeType.VOLCANIC, BiomeType.SKY_ISLAND],
             3, {"rebirth": True, "distance": 500.0}, 1.0),
        ]
        fauna_ids: Dict[str, str] = {}
        for name, atype, biomes, pop, pattern, danger in fauna_defs:
            ok, _, species = self.register_fauna_species(
                name=name,
                fauna_type=atype,
                preferred_biomes=biomes,
                population=pop,
                migration_pattern=pattern,
                danger_level=danger,
            )
            if ok and species is not None:
                fauna_ids[name] = species.species_id

        # -- Regions -------------------------------------------------------
        region_defs = [
            ("Whispering Vale", BiomeType.TEMPERATE_FOREST, ClimateZone.TEMPERATE,
             1500.0, (100.0, 100.0),
             ["Oakheart Tree", "Mosswhisper Moss", "Managrass"],
             ["Forest Stag", "Mountain Hawk"]),
            ("Sunscorch Wastes", BiomeType.DESERT, ClimateZone.SUBTROPICAL,
             2200.0, (320.0, 80.0),
             ["Sunbarrel Cactus"],
             ["Sandrunner Lizard"]),
            ("Ironpeak Range", BiomeType.MOUNTAIN, ClimateZone.ALPINE,
             1800.0, (200.0, 260.0),
             ["Mosswhisper Moss", "Skypetal Blossom"],
             ["Mountain Hawk", "Storm Elemental"]),
            ("Mistfen Marsh", BiomeType.WETLAND, ClimateZone.TEMPERATE,
             900.0, (150.0, 180.0),
             ["Lotusveil Flower", "Mosswhisper Moss"],
             ["Marshfrog", "River Otter"]),
            ("Embercore Caldera", BiomeType.VOLCANIC, ClimateZone.MAGICAL,
             1100.0, (420.0, 320.0),
             ["Emberroot Fungus"],
             ["Lavascale Drake", "Phoenix"]),
            ("Prism Caverns", BiomeType.CRYSTAL, ClimateZone.MAGICAL,
             800.0, (360.0, 210.0),
             ["Crystalsong Vine", "Glowcap"],
             ["Crystalwing Moth"]),
            ("Verdant Reach", BiomeType.TROPICAL_RAINFOREST, ClimateZone.TROPICAL,
             2600.0, (80.0, 30.0),
             ["Lotusveil Flower", "Managrass"],
             ["Marshfrog", "Forest Stag"]),
        ]
        for name, btype, zone, area, coord, flora_names, fauna_names in region_defs:
            ok, _, region = self.register_region(
                name=name,
                biome_type=btype,
                climate_zone=zone,
                area=area,
                center_coord=coord,
            )
            if not ok or region is None:
                continue
            for fname in flora_names:
                sid = flora_ids.get(fname)
                if sid:
                    region.flora_list.append(sid)
            for aname in fauna_names:
                sid = fauna_ids.get(aname)
                if sid:
                    region.fauna_list.append(sid)
            self.calculate_ecosystem_health(region.region_id)


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------

def get_climate_biome_system() -> ClimateBiomeSystem:
    """Return the singleton ClimateBiomeSystem instance, seeding on first use."""
    inst = ClimateBiomeSystem.get_instance()
    if not getattr(inst, "_seeded", False):
        inst.initialize()
    return inst
