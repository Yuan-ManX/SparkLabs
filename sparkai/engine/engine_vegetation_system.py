"""
SparkLabs Engine - Vegetation & Foliage Placement System

Procedural vegetation distribution system that manages the placement,
density, and rendering of foliage across game terrain, integrated with the
AI-native SparkLabs engine.

Core capabilities:
  - Species registry for trees, grass, bushes, flowers, rocks, and more
  - Biome-based distribution rules with configurable density
  - Patch management for coherent clusters of vegetation instances
  - Level-of-detail (LOD) selection driven by camera distance
  - Wind animation parameters per species and global gust settings
  - Seasonal variation with smooth transition blending
  - Distribution pattern sampling (clustered, scattered, uniform,
    dense patches, and linear arrangements)
  - Event log for auditing species and patch lifecycle changes

Architecture:
  VegetationSystemEngine (Singleton)
    |-- VegetationSpecies  -- a flora prototype (mesh, biome, density)
    |-- VegetationPatch    -- a placed cluster of instances in the world
    |-- WindSettings       -- global wind direction and gust parameters
    |-- SeasonState        -- current season and transition progress
    |-- VegetationStats    -- aggregate runtime statistics
    |-- VegetationSnapshot -- immutable point-in-time state capture
    |-- VegetationEvent    -- audit record for lifecycle changes

All public methods are thread-safe. Obtain the singleton through
``VegetationSystemEngine.get_instance()`` or the module-level
``get_vegetation_system()`` helper.
"""

from __future__ import annotations

import datetime
import math
import random
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity constants
# ---------------------------------------------------------------------------

_MAX_SPECIES: int = 500
_MAX_PATCHES: int = 5000
_MAX_EVENTS: int = 2000

# LOD distance thresholds (in world units). A patch whose distance from the
# camera falls below a threshold is rendered at the corresponding level.
_LOD_DISTANCE_HIGH: float = 50.0
_LOD_DISTANCE_MEDIUM: float = 150.0
_LOD_DISTANCE_LOW: float = 300.0


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VegetationType(Enum):
    """Broad category of a vegetation species."""

    TREE = "tree"
    BUSH = "bush"
    GRASS = "grass"
    FLOWER = "flower"
    ROCK = "rock"
    MUSHROOM = "mushroom"
    FERN = "fern"
    VINE = "vine"


class BiomeType(Enum):
    """Biome in which a species or patch naturally occurs."""

    FOREST = "forest"
    PLAINS = "plains"
    DESERT = "desert"
    TUNDRA = "tundra"
    JUNGLE = "jungle"
    WETLAND = "wetland"
    MOUNTAIN = "mountain"
    COASTAL = "coastal"


class SeasonType(Enum):
    """Season of the year, used for seasonal variation."""

    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class LODLevel(Enum):
    """Level of detail at which a patch is rendered."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BILLBOARD = "billboard"


class DistributionPattern(Enum):
    """Spatial arrangement used when sampling instance positions."""

    CLUSTERED = "clustered"
    SCATTERED = "scattered"
    UNIFORM = "uniform"
    DENSE_PATCH = "dense_patch"
    LINEAR = "linear"


class VegetationEventKind(Enum):
    """Kind of event emitted by the vegetation engine."""

    SPECIES_REGISTERED = "species_registered"
    PATCH_CREATED = "patch_created"
    PATCH_REMOVED = "patch_removed"
    SEASON_CHANGED = "season_changed"
    DENSITY_UPDATED = "density_updated"
    WIND_UPDATED = "wind_updated"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class VegetationSpecies:
    """Prototype definition for a kind of vegetation.

    A species describes the visual and ecological properties shared by
    every instance: its mesh reference, native biome, target density,
    height range, base color, LOD distance thresholds, and wind
    response. Patches reference a species to inherit these defaults.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable species name.
        vegetation_type: The broad VegetationType category.
        biome: The BiomeType this species naturally inhabits.
        density: Target instances per square meter.
        height_range: ``(min, max)`` height of an instance in meters.
        color: ``(r, g, b)`` base color tint, each in ``[0, 1]``.
        lod_distances: Mapping of LODLevel -> switch distance in meters.
        wind_sensitivity: ``[0, 1]`` responsiveness to wind animation.
        mesh_id: Asset id of the mesh used to render instances.
        metadata: Free-form extension data.
        timestamp: Creation time (UTC, ISO 8601 with ``Z`` suffix).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    vegetation_type: VegetationType = VegetationType.GRASS
    biome: BiomeType = BiomeType.PLAINS
    density: float = 1.0
    height_range: Tuple[float, float] = (0.5, 1.5)
    color: Tuple[float, float, float] = (0.5, 0.7, 0.3)
    lod_distances: Dict[LODLevel, float] = field(default_factory=dict)
    wind_sensitivity: float = 0.5
    mesh_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "vegetation_type": self.vegetation_type.value,
            "biome": self.biome.value,
            "density": self.density,
            "height_range": list(self.height_range),
            "color": list(self.color),
            "lod_distances": {
                lod.value: dist for lod, dist in self.lod_distances.items()
            },
            "wind_sensitivity": self.wind_sensitivity,
            "mesh_id": self.mesh_id,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class VegetationPatch:
    """A placed cluster of vegetation instances in the world.

    A patch is the unit of streaming and LOD selection: it has a center
    point, a radius defining its footprint, a distribution pattern that
    controls how instances are arranged within the patch, and a target
    instance count. The effective density is the species density scaled
    by the patch's ``density_multiplier``.

    Attributes:
        id: Unique identifier (auto-generated).
        species_id: The VegetationSpecies this patch instantiates.
        biome: Override biome for the patch placement.
        center: ``(x, y, z)`` world position of the patch center.
        radius: Radius of the circular patch footprint in meters.
        pattern: DistributionPattern used to sample positions.
        instance_count: Target number of instances in the patch.
        lod_level: Currently assigned LODLevel.
        season: Current SeasonType applied to the patch.
        density_multiplier: Scalar applied to the species density.
        seed: Deterministic seed for position sampling.
        metadata: Free-form extension data.
        timestamp: Creation time (UTC, ISO 8601 with ``Z`` suffix).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    species_id: str = ""
    biome: BiomeType = BiomeType.PLAINS
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 10.0
    pattern: DistributionPattern = DistributionPattern.SCATTERED
    instance_count: int = 0
    lod_level: LODLevel = LODLevel.HIGH
    season: SeasonType = SeasonType.SUMMER
    density_multiplier: float = 1.0
    seed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "species_id": self.species_id,
            "biome": self.biome.value,
            "center": list(self.center),
            "radius": self.radius,
            "pattern": self.pattern.value,
            "instance_count": self.instance_count,
            "lod_level": self.lod_level.value,
            "season": self.season.value,
            "density_multiplier": self.density_multiplier,
            "seed": self.seed,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class WindSettings:
    """Global wind parameters for vegetation animation.

    The wind direction is a 2D vector on the XZ plane (normalized by
    callers when needed). Strength is the steady-state amplitude, while
    gust frequency and amplitude modulate the steady wind with periodic
    gusts.

    Attributes:
        direction: ``(x, z)`` wind direction on the ground plane.
        strength: Steady wind strength in ``[0, 1]``.
        gust_frequency: Gust oscillations per second.
        gust_amplitude: Additional amplitude applied by gusts.
        last_updated: Time of the last wind update (UTC ISO 8601 ``Z``).
    """

    direction: Tuple[float, float] = (1.0, 0.0)
    strength: float = 0.3
    gust_frequency: float = 0.5
    gust_amplitude: float = 0.2
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": list(self.direction),
            "strength": self.strength,
            "gust_frequency": self.gust_frequency,
            "gust_amplitude": self.gust_amplitude,
            "last_updated": self.last_updated,
        }


@dataclass
class SeasonState:
    """Current season and any in-progress transition.

    When ``transition_progress`` is ``0.0`` the season is fully
    ``current_season``; as it advances toward ``1.0`` the visible state
    blends toward ``target_season``. A completed transition collapses
    ``target_season`` back onto ``current_season`` and resets progress.

    Attributes:
        current_season: The active SeasonType.
        transition_progress: Blend factor in ``[0, 1]``.
        target_season: The SeasonType being transitioned toward.
        last_changed: Time of the last season change (UTC ISO 8601 ``Z``).
    """

    current_season: SeasonType = SeasonType.SUMMER
    transition_progress: float = 0.0
    target_season: SeasonType = SeasonType.SUMMER
    last_changed: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_season": self.current_season.value,
            "transition_progress": self.transition_progress,
            "target_season": self.target_season.value,
            "last_changed": self.last_changed,
        }


@dataclass
class VegetationStats:
    """Aggregate runtime statistics for the vegetation engine.

    Attributes:
        total_species: Lifetime count of registered species.
        total_patches: Lifetime count of created patches.
        total_instances: Sum of instance counts across live patches.
        by_type: Live species count keyed by VegetationType value.
        by_biome: Live patch count keyed by BiomeType value.
        last_updated: Time the stats were computed (UTC ISO 8601 ``Z``).
    """

    total_species: int = 0
    total_patches: int = 0
    total_instances: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_biome: Dict[str, int] = field(default_factory=dict)
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_species": self.total_species,
            "total_patches": self.total_patches,
            "total_instances": self.total_instances,
            "by_type": dict(self.by_type),
            "by_biome": dict(self.by_biome),
            "last_updated": self.last_updated,
        }


@dataclass
class VegetationSnapshot:
    """Immutable point-in-time capture of engine state.

    Attributes:
        total_species: Live species count at capture time.
        total_patches: Live patch count at capture time.
        total_instances: Sum of live instance counts at capture time.
        current_season: SeasonType active at capture time.
        stats: A full VegetationStats object.
        timestamp: Capture time (UTC ISO 8601 ``Z``).
    """

    total_species: int = 0
    total_patches: int = 0
    total_instances: int = 0
    current_season: SeasonType = SeasonType.SUMMER
    stats: VegetationStats = field(default_factory=VegetationStats)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_species": self.total_species,
            "total_patches": self.total_patches,
            "total_instances": self.total_instances,
            "current_season": self.current_season.value,
            "stats": self.stats.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class VegetationEvent:
    """Audit record for a vegetation lifecycle event.

    Attributes:
        id: Unique identifier (auto-generated).
        kind: The VegetationEventKind of this event.
        payload: Event-specific data.
        timestamp: Emission time (UTC ISO 8601 ``Z``).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: VegetationEventKind = VegetationEventKind.SPECIES_REGISTERED
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Vegetation System Engine (Singleton)
# ---------------------------------------------------------------------------


class VegetationSystemEngine:
    """Engine-side vegetation and foliage placement system.

    Maintains a registry of vegetation species and patches, computes
    procedural distribution of instances within a patch, selects LOD
    levels based on camera distance, drives wind animation parameters,
    and applies seasonal variation across all patches.

    The class is a thread-safe singleton implemented with double-checked
    locking. Obtain the instance through :meth:`get_instance` or the
    module-level :func:`get_vegetation_system` helper.

    Usage:
        vs = get_vegetation_system()
        oak = vs.register_species(
            name="Oak Tree",
            vegetation_type=VegetationType.TREE,
            biome=BiomeType.FOREST,
            density=0.02,
            height_range=(8.0, 15.0),
            color=(0.4, 0.6, 0.2),
        )
        patch = vs.create_patch(
            species_id=oak.id,
            biome=BiomeType.FOREST,
            center=(100.0, 0.0, 100.0),
            radius=50.0,
            pattern=DistributionPattern.CLUSTERED,
            instance_count=200,
        )
        lod = vs.compute_lod(camera_position=(0.0, 0.0, 0.0),
                             patch_id=patch.id)
    """

    _instance: Optional["VegetationSystemEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "VegetationSystemEngine":
        # Double-checked locking singleton. ``__new__`` allocates the
        # instance and marks it uninitialized; ``__init__`` performs the
        # one-time setup guarded by that flag.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "VegetationSystemEngine":
        """Return the singleton VegetationSystemEngine instance (thread-safe).

        This does not reset ``_initialized``; the one-time setup performed
        by ``__init__`` is therefore idempotent across repeated calls.
        """
        return cls()

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton. The flag is
        # set to True at the very start so a recursive call into __init__
        # during seeding cannot re-enter setup.
        if self._initialized:
            return
        self._initialized: bool = True

        # Primary registries.
        self._species: Dict[str, VegetationSpecies] = {}
        self._patches: Dict[str, VegetationPatch] = {}

        # Wind and season state.
        self._wind: WindSettings = WindSettings()
        self._season: SeasonState = SeasonState()

        # Event log and aggregate counters.
        self._events: List[VegetationEvent] = []
        self._total_species_registered: int = 0
        self._total_patches_created: int = 0
        self._total_events_emitted: int = 0

        # Populate the default seed vegetation data.
        self._seed_default_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        kind: VegetationEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> VegetationEvent:
        """Create, log, and record a vegetation event (internal use only).

        The event log is capped at ``_MAX_EVENTS`` entries; the oldest
        entries are evicted when the cap is exceeded.
        """
        event = VegetationEvent(
            kind=kind,
            payload=payload or {},
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            del self._events[: len(self._events) - _MAX_EVENTS]
        self._total_events_emitted += 1
        return event

    @staticmethod
    def _distance_2d(
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
    ) -> float:
        """Return the Euclidean distance between two 3D points."""
        return math.sqrt(
            (a[0] - b[0]) ** 2
            + (a[1] - b[1]) ** 2
            + (a[2] - b[2]) ** 2
        )

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        """Clamp a float to ``[low, high]``."""
        return max(low, min(high, value))

    def _default_lod_distances(self) -> Dict[LODLevel, float]:
        """Return the default LOD switch distances for a new species."""
        return {
            LODLevel.HIGH: _LOD_DISTANCE_HIGH,
            LODLevel.MEDIUM: _LOD_DISTANCE_MEDIUM,
            LODLevel.LOW: _LOD_DISTANCE_LOW,
            LODLevel.BILLBOARD: _LOD_DISTANCE_LOW * 2.0,
        }

    def _count_total_instances(self) -> int:
        """Return the sum of instance counts across all live patches."""
        return sum(p.instance_count for p in self._patches.values())

    def _compute_stats(self) -> VegetationStats:
        """Compute aggregate statistics from the current state."""
        by_type: Dict[str, int] = {}
        by_biome: Dict[str, int] = {}

        for species in self._species.values():
            key = species.vegetation_type.value
            by_type[key] = by_type.get(key, 0) + 1

        for patch in self._patches.values():
            key = patch.biome.value
            by_biome[key] = by_biome.get(key, 0) + 1

        return VegetationStats(
            total_species=self._total_species_registered,
            total_patches=self._total_patches_created,
            total_instances=self._count_total_instances(),
            by_type=by_type,
            by_biome=by_biome,
            last_updated=datetime.datetime.utcnow().isoformat() + "Z",
        )

    # ------------------------------------------------------------------
    # Species management
    # ------------------------------------------------------------------

    def register_species(
        self,
        name: str,
        vegetation_type: VegetationType,
        biome: BiomeType,
        density: float,
        height_range: Tuple[float, float],
        color: Tuple[float, float, float],
        lod_distances: Optional[Dict[LODLevel, float]] = None,
        wind_sensitivity: float = 0.5,
        mesh_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VegetationSpecies:
        """Register a new vegetation species and return its descriptor.

        Args:
            name: Human-readable species name.
            vegetation_type: The broad VegetationType category.
            biome: The BiomeType this species naturally inhabits.
            density: Target instances per square meter.
            height_range: ``(min, max)`` height of an instance in meters.
            color: ``(r, g, b)`` base color tint, each in ``[0, 1]``.
            lod_distances: Optional override of LOD switch distances.
            wind_sensitivity: ``[0, 1]`` responsiveness to wind.
            mesh_id: Asset id of the mesh used to render instances.
            metadata: Free-form extension data.

        Returns:
            The newly registered VegetationSpecies.

        Raises:
            ValueError: If the species capacity (``_MAX_SPECIES``) has
                been reached.
        """
        with self._lock:
            if len(self._species) >= _MAX_SPECIES:
                raise ValueError(
                    f"Species capacity reached ({_MAX_SPECIES})"
                )

            species = VegetationSpecies(
                name=name,
                vegetation_type=vegetation_type,
                biome=biome,
                density=density,
                height_range=height_range,
                color=color,
                lod_distances=lod_distances
                if lod_distances is not None
                else self._default_lod_distances(),
                wind_sensitivity=self._clamp(wind_sensitivity),
                mesh_id=mesh_id,
                metadata=metadata or {},
            )
            self._species[species.id] = species
            self._total_species_registered += 1
            self._emit_event(
                VegetationEventKind.SPECIES_REGISTERED,
                {
                    "species_id": species.id,
                    "name": species.name,
                    "vegetation_type": species.vegetation_type.value,
                    "biome": species.biome.value,
                },
            )
            return species

    def get_species(self, species_id: str) -> Optional[VegetationSpecies]:
        """Return the species with the given id, or ``None`` if not found."""
        with self._lock:
            return self._species.get(species_id)

    def list_species(
        self,
        vegetation_type: Optional[VegetationType] = None,
        biome: Optional[BiomeType] = None,
    ) -> List[VegetationSpecies]:
        """Return species optionally filtered by type and/or biome.

        Args:
            vegetation_type: When provided, restrict to this type.
            biome: When provided, restrict to this biome.

        Returns:
            A list of matching VegetationSpecies records.
        """
        with self._lock:
            results: List[VegetationSpecies] = []
            for species in self._species.values():
                if vegetation_type is not None and species.vegetation_type != vegetation_type:
                    continue
                if biome is not None and species.biome != biome:
                    continue
                results.append(species)
            return results

    def remove_species(self, species_id: str) -> bool:
        """Remove a species from the registry.

        Patches that reference the removed species are left intact; their
        ``species_id`` will simply no longer resolve via :meth:`get_species`.

        Args:
            species_id: The species to remove.

        Returns:
            True if the species was found and removed, False otherwise.
        """
        with self._lock:
            if species_id not in self._species:
                return False
            del self._species[species_id]
            return True

    # ------------------------------------------------------------------
    # Patch management
    # ------------------------------------------------------------------

    def create_patch(
        self,
        species_id: str,
        biome: BiomeType,
        center: Tuple[float, float, float],
        radius: float,
        pattern: DistributionPattern = DistributionPattern.SCATTERED,
        instance_count: int = 0,
        density_multiplier: float = 1.0,
        seed: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VegetationPatch:
        """Create a new vegetation patch and return its descriptor.

        Args:
            species_id: The species this patch instantiates.
            biome: Override biome for the patch placement.
            center: ``(x, y, z)`` world position of the patch center.
            radius: Radius of the circular patch footprint in meters.
            pattern: DistributionPattern used to sample positions.
            instance_count: Target number of instances in the patch.
            density_multiplier: Scalar applied to the species density.
            seed: Deterministic seed for position sampling.
            metadata: Free-form extension data.

        Returns:
            The newly created VegetationPatch.

        Raises:
            ValueError: If the patch capacity (``_MAX_PATCHES``) has
                been reached.
        """
        with self._lock:
            if len(self._patches) >= _MAX_PATCHES:
                raise ValueError(
                    f"Patch capacity reached ({_MAX_PATCHES})"
                )

            if seed == 0:
                seed = random.randint(1, 2_147_483_647)

            patch = VegetationPatch(
                species_id=species_id,
                biome=biome,
                center=center,
                radius=radius,
                pattern=pattern,
                instance_count=instance_count,
                lod_level=LODLevel.HIGH,
                season=self._season.current_season,
                density_multiplier=density_multiplier,
                seed=seed,
                metadata=metadata or {},
            )
            self._patches[patch.id] = patch
            self._total_patches_created += 1
            self._emit_event(
                VegetationEventKind.PATCH_CREATED,
                {
                    "patch_id": patch.id,
                    "species_id": patch.species_id,
                    "biome": patch.biome.value,
                    "instance_count": patch.instance_count,
                    "pattern": patch.pattern.value,
                },
            )
            return patch

    def get_patch(self, patch_id: str) -> Optional[VegetationPatch]:
        """Return the patch with the given id, or ``None`` if not found."""
        with self._lock:
            return self._patches.get(patch_id)

    def list_patches(
        self,
        species_id: Optional[str] = None,
        biome: Optional[BiomeType] = None,
    ) -> List[VegetationPatch]:
        """Return patches optionally filtered by species and/or biome.

        Args:
            species_id: When provided, restrict to patches of this species.
            biome: When provided, restrict to patches in this biome.

        Returns:
            A list of matching VegetationPatch records.
        """
        with self._lock:
            results: List[VegetationPatch] = []
            for patch in self._patches.values():
                if species_id is not None and patch.species_id != species_id:
                    continue
                if biome is not None and patch.biome != biome:
                    continue
                results.append(patch)
            return results

    def remove_patch(self, patch_id: str) -> bool:
        """Remove a patch from the registry.

        Args:
            patch_id: The patch to remove.

        Returns:
            True if the patch was found and removed, False otherwise.
        """
        with self._lock:
            if patch_id not in self._patches:
                return False
            del self._patches[patch_id]
            self._emit_event(
                VegetationEventKind.PATCH_REMOVED,
                {"patch_id": patch_id},
            )
            return True

    def set_patch_lod(
        self, patch_id: str, lod_level: LODLevel
    ) -> Optional[VegetationPatch]:
        """Assign a new LOD level to a patch.

        Args:
            patch_id: The patch to update.
            lod_level: The new LODLevel.

        Returns:
            The updated VegetationPatch, or ``None`` if not found.
        """
        with self._lock:
            patch = self._patches.get(patch_id)
            if patch is None:
                return None
            patch.lod_level = lod_level
            return patch

    def update_patch_density(
        self, patch_id: str, density_multiplier: float
    ) -> Optional[VegetationPatch]:
        """Update the density multiplier of a patch.

        Args:
            patch_id: The patch to update.
            density_multiplier: The new density multiplier.

        Returns:
            The updated VegetationPatch, or ``None`` if not found.
        """
        with self._lock:
            patch = self._patches.get(patch_id)
            if patch is None:
                return None
            patch.density_multiplier = self._clamp(density_multiplier, 0.0, 10.0)
            self._emit_event(
                VegetationEventKind.DENSITY_UPDATED,
                {
                    "patch_id": patch.id,
                    "density_multiplier": patch.density_multiplier,
                },
            )
            return patch

    # ------------------------------------------------------------------
    # Distribution sampling
    # ------------------------------------------------------------------

    def compute_distribution(
        self,
        species_id: str,
        center: Tuple[float, float, float],
        radius: float,
        pattern: DistributionPattern = DistributionPattern.SCATTERED,
        density_multiplier: float = 1.0,
        seed: int = 0,
    ) -> Dict[str, Any]:
        """Compute instance positions for a hypothetical patch.

        Samples ``instance_count`` positions within the circular footprint
        centered at ``center`` with the given ``radius``, using the
        specified distribution ``pattern``. The instance count is derived
        from the species density, the patch area, and the density
        multiplier.

        Args:
            species_id: The species whose density drives the count.
            center: ``(x, y, z)`` world position of the patch center.
            radius: Radius of the circular patch footprint in meters.
            pattern: DistributionPattern used to sample positions.
            density_multiplier: Scalar applied to the species density.
            seed: Deterministic seed for position sampling.

        Returns:
            A dict with ``positions`` (list of ``(x, y, z)`` tuples),
            ``count`` (int), and ``pattern`` (str).
        """
        with self._lock:
            species = self._species.get(species_id)
            if species is None:
                return {
                    "positions": [],
                    "count": 0,
                    "pattern": pattern.value,
                    "error": "species_not_found",
                }

            area = math.pi * radius * radius
            effective_density = max(
                0.0, species.density * self._clamp(density_multiplier, 0.0, 10.0)
            )
            target_count = int(round(effective_density * area))

            rng = random.Random(seed if seed != 0 else 1)
            positions: List[Tuple[float, float, float]] = []

            cx, cy, cz = center

            if pattern == DistributionPattern.UNIFORM:
                # Grid-based uniform distribution with a jitter for
                # natural variation. Cell size is derived so the grid
                # approximately fills the circle.
                spacing = max(
                    0.5,
                    math.sqrt(area / max(1, target_count))
                    if target_count > 0
                    else radius,
                )
                grid_extent = int(math.ceil(radius / spacing)) + 1
                for ix in range(-grid_extent, grid_extent + 1):
                    for iz in range(-grid_extent, grid_extent + 1):
                        px = cx + ix * spacing + rng.uniform(
                            -spacing * 0.25, spacing * 0.25
                        )
                        pz = cz + iz * spacing + rng.uniform(
                            -spacing * 0.25, spacing * 0.25
                        )
                        dx = px - cx
                        dz = pz - cz
                        if dx * dx + dz * dz <= radius * radius:
                            positions.append((px, cy, pz))
                            if len(positions) >= target_count:
                                break
                    if len(positions) >= target_count:
                        break

            elif pattern == DistributionPattern.CLUSTERED:
                # Pick a handful of cluster centers and scatter points
                # around each, producing natural clumps of vegetation.
                cluster_count = max(1, target_count // 25)
                cluster_centers: List[Tuple[float, float]] = []
                for _ in range(cluster_count):
                    angle = rng.uniform(0.0, 2.0 * math.pi)
                    dist = rng.uniform(0.0, radius * 0.8)
                    cluster_centers.append(
                        (cx + math.cos(angle) * dist, cz + math.sin(angle) * dist)
                    )
                per_cluster = max(1, target_count // cluster_count)
                for ccx, ccz in cluster_centers:
                    for _ in range(per_cluster):
                        if len(positions) >= target_count:
                            break
                        angle = rng.uniform(0.0, 2.0 * math.pi)
                        dist = rng.uniform(0.0, radius * 0.2)
                        px = ccx + math.cos(angle) * dist
                        pz = ccz + math.sin(angle) * dist
                        dx = px - cx
                        dz = pz - cz
                        if dx * dx + dz * dz <= radius * radius:
                            positions.append((px, cy, pz))

            elif pattern == DistributionPattern.DENSE_PATCH:
                # A single tight dense cluster in the center of the
                # patch; instances are packed into a small inner radius.
                inner_radius = max(1.0, radius * 0.35)
                for _ in range(target_count):
                    angle = rng.uniform(0.0, 2.0 * math.pi)
                    # Square-root sampling for uniform area distribution.
                    dist = math.sqrt(rng.random()) * inner_radius
                    px = cx + math.cos(angle) * dist
                    pz = cz + math.sin(angle) * dist
                    positions.append((px, cy, pz))

            elif pattern == DistributionPattern.LINEAR:
                # Distribute instances along a line crossing the patch.
                # The line direction is randomized per seed so each patch
                # has a deterministic but varied orientation.
                line_angle = rng.uniform(0.0, math.pi)
                line_dx = math.cos(line_angle)
                line_dz = math.sin(line_angle)
                line_length = radius * 2.0
                step = line_length / max(1, target_count)
                start = -line_length / 2.0
                for i in range(target_count):
                    offset = start + i * step + rng.uniform(-step * 0.2, step * 0.2)
                    px = cx + line_dx * offset
                    pz = cz + line_dz * offset
                    # Lateral jitter to give the line some thickness.
                    px += rng.uniform(-radius * 0.05, radius * 0.05)
                    pz += rng.uniform(-radius * 0.05, radius * 0.05)
                    positions.append((px, cy, pz))

            else:
                # SCATTERED (default): random uniform points within the
                # circle using polar coordinates with square-root
                # sampling for even area coverage.
                for _ in range(target_count):
                    angle = rng.uniform(0.0, 2.0 * math.pi)
                    dist = math.sqrt(rng.random()) * radius
                    px = cx + math.cos(angle) * dist
                    pz = cz + math.sin(angle) * dist
                    positions.append((px, cy, pz))

            return {
                "positions": positions,
                "count": len(positions),
                "pattern": pattern.value,
            }

    # ------------------------------------------------------------------
    # Season management
    # ------------------------------------------------------------------

    def set_season(self, season: SeasonType) -> SeasonState:
        """Set the active season and propagate it to all patches.

        Any in-progress transition is discarded; the new season becomes
        both the current and target season with progress reset to zero.

        Args:
            season: The new SeasonType to apply.

        Returns:
            The updated SeasonState.
        """
        with self._lock:
            self._season.current_season = season
            self._season.target_season = season
            self._season.transition_progress = 0.0
            self._season.last_changed = (
                datetime.datetime.utcnow().isoformat() + "Z"
            )
            for patch in self._patches.values():
                patch.season = season
            self._emit_event(
                VegetationEventKind.SEASON_CHANGED,
                {
                    "season": season.value,
                    "patch_count": len(self._patches),
                },
            )
            return self._season

    def get_season(self) -> SeasonState:
        """Return the current season state."""
        with self._lock:
            return self._season

    def transition_season(
        self, target_season: SeasonType, progress: float
    ) -> SeasonState:
        """Advance the season transition toward ``target_season``.

        Sets the target season and clamps the progress to ``[0, 1]``.
        When progress reaches ``1.0`` the transition collapses: the
        target becomes the current season and progress resets to zero.

        Args:
            target_season: The SeasonType being transitioned toward.
            progress: Blend factor in ``[0, 1]``.

        Returns:
            The updated SeasonState.
        """
        with self._lock:
            self._season.target_season = target_season
            self._season.transition_progress = self._clamp(progress, 0.0, 1.0)
            if self._season.transition_progress >= 1.0:
                self._season.current_season = target_season
                self._season.transition_progress = 0.0
                self._season.last_changed = (
                    datetime.datetime.utcnow().isoformat() + "Z"
                )
                for patch in self._patches.values():
                    patch.season = target_season
            self._emit_event(
                VegetationEventKind.SEASON_CHANGED,
                {
                    "target_season": target_season.value,
                    "progress": self._season.transition_progress,
                },
            )
            return self._season

    # ------------------------------------------------------------------
    # Wind management
    # ------------------------------------------------------------------

    def set_wind(
        self,
        direction: Tuple[float, float],
        strength: float,
        gust_frequency: float,
        gust_amplitude: float,
    ) -> WindSettings:
        """Update the global wind parameters.

        Args:
            direction: ``(x, z)`` wind direction on the ground plane.
            strength: Steady wind strength in ``[0, 1]``.
            gust_frequency: Gust oscillations per second.
            gust_amplitude: Additional amplitude applied by gusts.

        Returns:
            The updated WindSettings.
        """
        with self._lock:
            self._wind.direction = direction
            self._wind.strength = self._clamp(strength, 0.0, 1.0)
            self._wind.gust_frequency = max(0.0, gust_frequency)
            self._wind.gust_amplitude = self._clamp(gust_amplitude, 0.0, 1.0)
            self._wind.last_updated = (
                datetime.datetime.utcnow().isoformat() + "Z"
            )
            self._emit_event(
                VegetationEventKind.WIND_UPDATED,
                {
                    "strength": self._wind.strength,
                    "gust_frequency": self._wind.gust_frequency,
                    "gust_amplitude": self._wind.gust_amplitude,
                },
            )
            return self._wind

    def get_wind(self) -> WindSettings:
        """Return the current wind settings."""
        with self._lock:
            return self._wind

    # ------------------------------------------------------------------
    # LOD management
    # ------------------------------------------------------------------

    def compute_lod(
        self,
        camera_position: Tuple[float, float, float],
        patch_id: str,
    ) -> LODLevel:
        """Determine the LOD level for a patch based on camera distance.

        Uses the patch's species LOD distance thresholds when available,
        falling back to the engine default thresholds.

        Args:
            camera_position: ``(x, y, z)`` world position of the camera.
            patch_id: The patch whose LOD is being evaluated.

        Returns:
            The recommended LODLevel. Returns BILLBOARD when the patch
            cannot be found (treated as far away).
        """
        with self._lock:
            patch = self._patches.get(patch_id)
            if patch is None:
                return LODLevel.BILLBOARD

            distance = self._distance_2d(camera_position, patch.center)
            species = self._species.get(patch.species_id)
            lod_distances = (
                species.lod_distances if species is not None else {}
            )

            high_d = lod_distances.get(LODLevel.HIGH, _LOD_DISTANCE_HIGH)
            medium_d = lod_distances.get(LODLevel.MEDIUM, _LOD_DISTANCE_MEDIUM)
            low_d = lod_distances.get(LODLevel.LOW, _LOD_DISTANCE_LOW)

            if distance <= high_d:
                return LODLevel.HIGH
            if distance <= medium_d:
                return LODLevel.MEDIUM
            if distance <= low_d:
                return LODLevel.LOW
            return LODLevel.BILLBOARD

    def update_lods(
        self, camera_position: Tuple[float, float, float]
    ) -> Dict[str, LODLevel]:
        """Recompute and apply the LOD level for every live patch.

        Args:
            camera_position: ``(x, y, z)`` world position of the camera.

        Returns:
            A mapping of patch id -> assigned LODLevel.
        """
        with self._lock:
            result: Dict[str, LODLevel] = {}
            for patch_id, patch in self._patches.items():
                lod = self.compute_lod(camera_position, patch_id)
                patch.lod_level = lod
                result[patch_id] = lod
            return result

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def list_events(
        self,
        event_kind: Optional[VegetationEventKind] = None,
        limit: int = 100,
    ) -> List[VegetationEvent]:
        """Return the most recent events, newest last.

        Args:
            event_kind: When provided, restrict the result to events of
                that kind.
            limit: Maximum number of events to return.

        Returns:
            A list of VegetationEvent records (up to ``limit``).
        """
        with self._lock:
            if limit <= 0:
                return []
            events = list(self._events)
            if event_kind is not None:
                events = [e for e in events if e.kind == event_kind]
            return events[-limit:]

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_stats(self) -> VegetationStats:
        """Return aggregate statistic counters as a VegetationStats object."""
        with self._lock:
            return self._compute_stats()

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current engine state."""
        with self._lock:
            stats = self._compute_stats()
            return {
                "initialized": self._initialized,
                "total_species": len(self._species),
                "total_patches": len(self._patches),
                "total_instances": self._count_total_instances(),
                "total_events": len(self._events),
                "current_season": self._season.current_season.value,
                "transition_progress": self._season.transition_progress,
                "wind_strength": self._wind.strength,
                "max_species": _MAX_SPECIES,
                "max_patches": _MAX_PATCHES,
                "max_events": _MAX_EVENTS,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> VegetationSnapshot:
        """Capture an immutable snapshot of the engine state."""
        with self._lock:
            stats = self._compute_stats()
            return VegetationSnapshot(
                total_species=len(self._species),
                total_patches=len(self._patches),
                total_instances=self._count_total_instances(),
                current_season=self._season.current_season,
                stats=stats,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all species, patches, events, and reset wind and season.

        Restores the engine to its initial state, including the default
        seed vegetation data.
        """
        with self._lock:
            self._species.clear()
            self._patches.clear()
            self._wind = WindSettings()
            self._season = SeasonState()
            self._events.clear()
            self._total_species_registered = 0
            self._total_patches_created = 0
            self._total_events_emitted = 0
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate the default species, patches, wind, and season.

        Creates a small starter world: five species (an oak tree, a pine
        tree, wild grass, lavender, and a moss rock), three patches (an
        oak cluster in the forest, a grass field on the plains, and a
        lavender meadow), gentle westerly wind with mild gusts, and the
        season set to midsummer.
        """
        # 1. Species - the foundational flora prototypes.
        oak = VegetationSpecies(
            name="Oak Tree",
            vegetation_type=VegetationType.TREE,
            biome=BiomeType.FOREST,
            density=0.02,
            height_range=(8.0, 15.0),
            color=(0.4, 0.6, 0.2),
            lod_distances=self._default_lod_distances(),
            wind_sensitivity=0.4,
            mesh_id="mesh_tree_oak",
            metadata={"leaf_type": "broadleaf", "lifespan": "long"},
        )
        self._species[oak.id] = oak
        self._total_species_registered += 1
        self._emit_event(
            VegetationEventKind.SPECIES_REGISTERED,
            {
                "species_id": oak.id,
                "name": oak.name,
                "vegetation_type": oak.vegetation_type.value,
                "biome": oak.biome.value,
            },
        )

        pine = VegetationSpecies(
            name="Pine Tree",
            vegetation_type=VegetationType.TREE,
            biome=BiomeType.MOUNTAIN,
            density=0.03,
            height_range=(5.0, 12.0),
            color=(0.2, 0.5, 0.3),
            lod_distances=self._default_lod_distances(),
            wind_sensitivity=0.3,
            mesh_id="mesh_tree_pine",
            metadata={"leaf_type": "needle", "lifespan": "long"},
        )
        self._species[pine.id] = pine
        self._total_species_registered += 1
        self._emit_event(
            VegetationEventKind.SPECIES_REGISTERED,
            {
                "species_id": pine.id,
                "name": pine.name,
                "vegetation_type": pine.vegetation_type.value,
                "biome": pine.biome.value,
            },
        )

        grass = VegetationSpecies(
            name="Wild Grass",
            vegetation_type=VegetationType.GRASS,
            biome=BiomeType.PLAINS,
            density=5.0,
            height_range=(0.3, 0.8),
            color=(0.5, 0.7, 0.3),
            lod_distances=self._default_lod_distances(),
            wind_sensitivity=0.8,
            mesh_id="mesh_grass_wild",
            metadata={"blade_count": 12, "growth": "fast"},
        )
        self._species[grass.id] = grass
        self._total_species_registered += 1
        self._emit_event(
            VegetationEventKind.SPECIES_REGISTERED,
            {
                "species_id": grass.id,
                "name": grass.name,
                "vegetation_type": grass.vegetation_type.value,
                "biome": grass.biome.value,
            },
        )

        lavender = VegetationSpecies(
            name="Lavender",
            vegetation_type=VegetationType.FLOWER,
            biome=BiomeType.PLAINS,
            density=0.5,
            height_range=(0.2, 0.5),
            color=(0.6, 0.4, 0.8),
            lod_distances=self._default_lod_distances(),
            wind_sensitivity=0.6,
            mesh_id="mesh_flower_lavender",
            metadata={"blooms_in": "summer", "aroma": "strong"},
        )
        self._species[lavender.id] = lavender
        self._total_species_registered += 1
        self._emit_event(
            VegetationEventKind.SPECIES_REGISTERED,
            {
                "species_id": lavender.id,
                "name": lavender.name,
                "vegetation_type": lavender.vegetation_type.value,
                "biome": lavender.biome.value,
            },
        )

        moss_rock = VegetationSpecies(
            name="Moss Rock",
            vegetation_type=VegetationType.ROCK,
            biome=BiomeType.TUNDRA,
            density=0.01,
            height_range=(0.5, 2.0),
            color=(0.4, 0.4, 0.4),
            lod_distances=self._default_lod_distances(),
            wind_sensitivity=0.0,
            mesh_id="mesh_rock_moss",
            metadata={"material": "granite", "mossy": True},
        )
        self._species[moss_rock.id] = moss_rock
        self._total_species_registered += 1
        self._emit_event(
            VegetationEventKind.SPECIES_REGISTERED,
            {
                "species_id": moss_rock.id,
                "name": moss_rock.name,
                "vegetation_type": moss_rock.vegetation_type.value,
                "biome": moss_rock.biome.value,
            },
        )

        # 2. Patches - placed clusters of the species above.
        oak_patch = VegetationPatch(
            species_id=oak.id,
            biome=BiomeType.FOREST,
            center=(100.0, 0.0, 100.0),
            radius=50.0,
            pattern=DistributionPattern.CLUSTERED,
            instance_count=200,
            lod_level=LODLevel.HIGH,
            season=SeasonType.SUMMER,
            density_multiplier=1.0,
            seed=42,
            metadata={"region": "north_forest", "streamed": True},
        )
        self._patches[oak_patch.id] = oak_patch
        self._total_patches_created += 1
        self._emit_event(
            VegetationEventKind.PATCH_CREATED,
            {
                "patch_id": oak_patch.id,
                "species_id": oak_patch.species_id,
                "biome": oak_patch.biome.value,
                "instance_count": oak_patch.instance_count,
                "pattern": oak_patch.pattern.value,
            },
        )

        grass_patch = VegetationPatch(
            species_id=grass.id,
            biome=BiomeType.PLAINS,
            center=(0.0, 0.0, 0.0),
            radius=100.0,
            pattern=DistributionPattern.UNIFORM,
            instance_count=5000,
            lod_level=LODLevel.HIGH,
            season=SeasonType.SUMMER,
            density_multiplier=1.0,
            seed=7,
            metadata={"region": "central_plains", "streamed": True},
        )
        self._patches[grass_patch.id] = grass_patch
        self._total_patches_created += 1
        self._emit_event(
            VegetationEventKind.PATCH_CREATED,
            {
                "patch_id": grass_patch.id,
                "species_id": grass_patch.species_id,
                "biome": grass_patch.biome.value,
                "instance_count": grass_patch.instance_count,
                "pattern": grass_patch.pattern.value,
            },
        )

        lavender_patch = VegetationPatch(
            species_id=lavender.id,
            biome=BiomeType.PLAINS,
            center=(50.0, 0.0, 80.0),
            radius=30.0,
            pattern=DistributionPattern.SCATTERED,
            instance_count=300,
            lod_level=LODLevel.HIGH,
            season=SeasonType.SUMMER,
            density_multiplier=1.0,
            seed=99,
            metadata={"region": "lavender_meadow", "streamed": True},
        )
        self._patches[lavender_patch.id] = lavender_patch
        self._total_patches_created += 1
        self._emit_event(
            VegetationEventKind.PATCH_CREATED,
            {
                "patch_id": lavender_patch.id,
                "species_id": lavender_patch.species_id,
                "biome": lavender_patch.biome.value,
                "instance_count": lavender_patch.instance_count,
                "pattern": lavender_patch.pattern.value,
            },
        )

        # 3. Wind - a gentle westerly breeze with mild gusts.
        self._wind = WindSettings(
            direction=(1.0, 0.0),
            strength=0.3,
            gust_frequency=0.5,
            gust_amplitude=0.2,
            last_updated=datetime.datetime.utcnow().isoformat() + "Z",
        )
        self._emit_event(
            VegetationEventKind.WIND_UPDATED,
            {
                "strength": self._wind.strength,
                "gust_frequency": self._wind.gust_frequency,
                "gust_amplitude": self._wind.gust_amplitude,
            },
        )

        # 4. Season - midsummer, no active transition.
        self._season = SeasonState(
            current_season=SeasonType.SUMMER,
            transition_progress=0.0,
            target_season=SeasonType.SUMMER,
            last_changed=datetime.datetime.utcnow().isoformat() + "Z",
        )
        self._emit_event(
            VegetationEventKind.SEASON_CHANGED,
            {
                "season": self._season.current_season.value,
                "patch_count": len(self._patches),
            },
        )


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_vegetation_system() -> VegetationSystemEngine:
    """Return the singleton VegetationSystemEngine instance."""
    return VegetationSystemEngine.get_instance()
