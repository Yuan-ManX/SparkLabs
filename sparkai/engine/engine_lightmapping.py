"""
SparkLabs Engine - Lightmapping & Baked Global Illumination

A comprehensive lightmapping and baked global illumination system for the
AI-native game engine. Provides lightmap atlas packing, light probe volume
placement, baked light registration, and multi-algorithm GI baking with
asynchronous job execution.

Architecture:
  LightmappingEngine (Singleton)
    |-- LightmapAtlas       — packed atlas of lightmap regions
    |-- LightmapRegion      — a single mesh's lightmap UV region
    |-- LightProbe          — single irradiance probe with SH coefficients
    |-- LightProbeVolume    — 3D grid of light probes
    |-- BakedLight          — a registered light source for baking
    |-- BakeSettings        — configuration for the bake process
    |-- BakedScene          — complete scene with atlas, probes, lights, settings

Baking Pipeline:
  1. create_settings() to define bake quality and parameters
  2. create_bake_scene() to initialize the scene container
  3. add_baked_light() and add_mesh_to_bake() to populate the scene
  4. place_light_probes() to position irradiance probes
  5. start_bake() to run the selected GI algorithm asynchronously
  6. sample_lighting() / sample_probe_lighting() for runtime queries
  7. export_lightmap() to write baked results to disk

Supported GI Algorithms:
  - PATH_TRACER                — Monte Carlo path tracing with indirect bounces
  - PHOTON_MAPPING             — two-pass photon emission and gathering
  - RADIOSITY                  — finite-element form-factor computation
  - AMBIENT_OCCLUSION_ONLY     — hemisphere sampling for AO only
"""

from __future__ import annotations

import json
import math
import os
import random
import struct
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BakeStatus(Enum):
    """Lifecycle state of a scene bake operation."""
    NOT_BAKED = "not_baked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class LightType(Enum):
    """Classification of a light source for baking."""
    POINT = "point"
    SPOT = "spot"
    DIRECTIONAL = "directional"
    AREA = "area"
    EMISSIVE_SURFACE = "emissive_surface"


class BakeQuality(Enum):
    """Quality presets controlling sample counts and resolution."""
    PREVIEW = "preview"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class GIAlgorithm(Enum):
    """Global illumination algorithm to use during baking."""
    PATH_TRACER = "path_tracer"
    PHOTON_MAPPING = "photon_mapping"
    RADIOSITY = "radiosity"
    AMBIENT_OCCLUSION_ONLY = "ambient_occlusion_only"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class LightmapRegion:
    """A single mesh's allocated region within a lightmap atlas.

    Stores the UV offset and scale that map the region within the atlas
    texture, the resolution of the region in texels, the baked texel data
    as a 2D grid of RGB float triples, and the current bake status.
    """

    region_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mesh_name: str = ""
    uv_offset: Tuple[float, float] = (0.0, 0.0)
    uv_scale: Tuple[float, float] = (1.0, 1.0)
    resolution: Tuple[int, int] = (64, 64)
    texel_data: List[List[Tuple[float, float, float]]] = field(
        default_factory=list
    )
    status: BakeStatus = BakeStatus.NOT_BAKED

    def __post_init__(self) -> None:
        if self.resolution[0] <= 0 or self.resolution[1] <= 0:
            raise ValueError("resolution dimensions must be positive")
        if not self.texel_data:
            self._initialize_texel_data()

    def _initialize_texel_data(self) -> None:
        w, h = self.resolution
        self.texel_data = [
            [(0.0, 0.0, 0.0) for _ in range(w)]
            for _ in range(h)
        ]

    @property
    def texel_count(self) -> int:
        return self.resolution[0] * self.resolution[1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "mesh_name": self.mesh_name,
            "uv_offset": list(self.uv_offset),
            "uv_scale": list(self.uv_scale),
            "resolution": list(self.resolution),
            "texel_count": self.texel_count,
            "status": self.status.value,
        }


@dataclass
class LightmapAtlas:
    """A packed atlas containing multiple lightmap regions.

    The atlas holds a collection of LightmapRegion objects packed into
    a single texture of the given resolution. Tracks total and occupied
    texel counts for utilization reporting. The format field specifies
    the pixel encoding used when exporting.
    """

    atlas_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "LightmapAtlas"
    resolution: Tuple[int, int] = (1024, 1024)
    lightmaps: List[LightmapRegion] = field(default_factory=list)
    format: str = "RGB8"

    @property
    def total_texels(self) -> int:
        return self.resolution[0] * self.resolution[1]

    @property
    def occupied_texels(self) -> int:
        return sum(region.texel_count for region in self.lightmaps)

    @property
    def utilization(self) -> float:
        if self.total_texels <= 0:
            return 0.0
        return self.occupied_texels / self.total_texels

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atlas_id": self.atlas_id,
            "name": self.name,
            "resolution": list(self.resolution),
            "total_texels": self.total_texels,
            "occupied_texels": self.occupied_texels,
            "utilization": round(self.utilization, 4),
            "format": self.format,
            "region_count": len(self.lightmaps),
            "regions": [region.to_dict() for region in self.lightmaps],
        }


@dataclass
class LightProbe:
    """A single irradiance probe storing spherical harmonics coefficients.

    Contains 9 SH coefficients (2nd-order, L=0,1,2) for each RGB channel
    totaling 27 values. The influence_radius defines the spherical region
    where this probe contributes to runtime interpolation.
    """

    probe_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    spherical_harmonics: List[float] = field(
        default_factory=lambda: [0.0] * 27
    )
    influence_radius: float = 2.0
    bake_status: BakeStatus = BakeStatus.NOT_BAKED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.spherical_harmonics) != 27:
            raise ValueError(
                "spherical_harmonics must contain exactly 27 values "
                "(9 coefficients x 3 RGB channels)"
            )
        if self.influence_radius <= 0.0:
            raise ValueError("influence_radius must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "position": list(self.position),
            "spherical_harmonics": list(self.spherical_harmonics),
            "influence_radius": self.influence_radius,
            "bake_status": self.bake_status.value,
            "metadata": dict(self.metadata),
        }


@dataclass
class LightProbeVolume:
    """A 3D grid of light probes covering a scene volume.

    Probes are placed on a regular grid defined by bounds and spacing.
    The density field reports the number of probes per cubic unit.
    """

    volume_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "LightProbeVolume"
    probes: List[LightProbe] = field(default_factory=list)
    bounds: Tuple[float, float, float, float, float, float] = (
        -10.0, -10.0, -10.0, 10.0, 10.0, 10.0
    )
    probe_spacing: float = 2.0

    @property
    def density(self) -> float:
        if self.probe_spacing <= 0.0:
            return 0.0
        volume_size = (
            (self.bounds[3] - self.bounds[0])
            * (self.bounds[4] - self.bounds[1])
            * (self.bounds[5] - self.bounds[2])
        )
        if volume_size <= 0.0:
            return 0.0
        return len(self.probes) / volume_size

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volume_id": self.volume_id,
            "name": self.name,
            "probe_count": len(self.probes),
            "bounds": list(self.bounds),
            "probe_spacing": self.probe_spacing,
            "density": round(self.density, 4),
            "probes": [probe.to_dict() for probe in self.probes],
        }


@dataclass
class BakedLight:
    """A light source registered for baking into the scene.

    Supports point, spot, directional, area, and emissive surface types.
    Shadow settings control the number of shadow rays cast during baking.
    bake_quality overrides the global setting for this specific light.
    """

    light_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    light_type: LightType = LightType.POINT
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    cast_shadows: bool = True
    shadow_samples: int = 32
    bake_quality: BakeQuality = BakeQuality.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.intensity < 0.0:
            raise ValueError("intensity must be non-negative")
        if self.shadow_samples < 0:
            raise ValueError("shadow_samples must be non-negative")
        for channel in self.color:
            if not (0.0 <= channel <= 1.0):
                raise ValueError("color channels must be in [0.0, 1.0]")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_id": self.light_id,
            "light_type": self.light_type.value,
            "position": list(self.position),
            "color": list(self.color),
            "intensity": self.intensity,
            "cast_shadows": self.cast_shadows,
            "shadow_samples": self.shadow_samples,
            "bake_quality": self.bake_quality.value,
            "metadata": dict(self.metadata),
        }


@dataclass
class BakeSettings:
    """Configuration for a global illumination bake operation.

    Controls resolution scaling, indirect bounce count, ambient occlusion
    parameters, shadow softness, denoising, and photon mapping density.
    """

    settings_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "DefaultBakeSettings"
    resolution_scale: float = 1.0
    indirect_bounces: int = 2
    ambient_occlusion: bool = True
    ao_radius: float = 1.0
    ao_samples: int = 16
    shadow_softness: float = 0.5
    denoise_enabled: bool = True
    denoise_strength: float = 0.75
    photon_count: int = 100000

    def __post_init__(self) -> None:
        if not (0.1 <= self.resolution_scale <= 4.0):
            raise ValueError("resolution_scale must be in [0.1, 4.0]")
        if self.indirect_bounces < 0:
            raise ValueError("indirect_bounces must be non-negative")
        if self.ao_radius <= 0.0:
            raise ValueError("ao_radius must be positive")
        if self.ao_samples <= 0:
            raise ValueError("ao_samples must be positive")
        if not (0.0 <= self.shadow_softness <= 1.0):
            raise ValueError("shadow_softness must be in [0.0, 1.0]")
        if not (0.0 <= self.denoise_strength <= 1.0):
            raise ValueError("denoise_strength must be in [0.0, 1.0]")
        if self.photon_count < 0:
            raise ValueError("photon_count must be non-negative")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "settings_id": self.settings_id,
            "name": self.name,
            "resolution_scale": self.resolution_scale,
            "indirect_bounces": self.indirect_bounces,
            "ambient_occlusion": self.ambient_occlusion,
            "ao_radius": self.ao_radius,
            "ao_samples": self.ao_samples,
            "shadow_softness": self.shadow_softness,
            "denoise_enabled": self.denoise_enabled,
            "denoise_strength": self.denoise_strength,
            "photon_count": self.photon_count,
        }


@dataclass
class BakedScene:
    """A complete scene container for lightmapping.

    Bundles the lightmap atlas, probe volume, registered baked lights,
    bake settings, and bake timing/status into a single unit.
    """

    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "BakedScene"
    lightmap_atlas: Optional[LightmapAtlas] = None
    probe_volume: Optional[LightProbeVolume] = None
    baked_lights: List[BakedLight] = field(default_factory=list)
    bake_settings: Optional[BakeSettings] = None
    bake_time: float = 0.0
    bake_status: BakeStatus = BakeStatus.NOT_BAKED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "lightmap_atlas": (
                self.lightmap_atlas.to_dict()
                if self.lightmap_atlas else None
            ),
            "probe_volume": (
                self.probe_volume.to_dict()
                if self.probe_volume else None
            ),
            "baked_lights": [light.to_dict() for light in self.baked_lights],
            "bake_settings": (
                self.bake_settings.to_dict()
                if self.bake_settings else None
            ),
            "bake_time": round(self.bake_time, 4),
            "bake_status": self.bake_status.value,
        }


# ---------------------------------------------------------------------------
# Lightmapping Engine
# ---------------------------------------------------------------------------

class LightmappingEngine:
    """Singleton manager for lightmapping and baked global illumination.

    Maintains registries of bake settings, scenes, and active bake jobs.
    Supports asynchronous baking via background threads with progress
    tracking. Provides runtime sampling of baked lighting and probe
    irradiance, lightmap denoising, and export to disk.

    Use get_lightmapping() to obtain the singleton instance.
    """

    _instance: Optional["LightmappingEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "LightmappingEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LightmappingEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._scenes: Dict[str, BakedScene] = {}
        self._settings: Dict[str, BakeSettings] = {}
        self._bake_jobs: Dict[str, Dict[str, Any]] = {}
        self._bake_threads: Dict[str, threading.Thread] = {}
        self._cancel_flags: Dict[str, bool] = {}
        self._mesh_geometry: Dict[str, Dict[str, Any]] = {}

        self._stats: Dict[str, Any] = {
            "total_scenes_created": 0,
            "total_bakes_started": 0,
            "total_bakes_completed": 0,
            "total_bakes_failed": 0,
            "total_bakes_cancelled": 0,
            "total_lights_registered": 0,
            "total_regions_created": 0,
            "total_probes_placed": 0,
            "total_lightmaps_exported": 0,
            "total_bake_time_seconds": 0.0,
        }

    # ------------------------------------------------------------------
    # Internal: Vector Math
    # ------------------------------------------------------------------

    @staticmethod
    def _dot3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _sub3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    @staticmethod
    def _add3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
        return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

    @staticmethod
    def _mul3(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
        return (v[0] * s, v[1] * s, v[2] * s)

    @staticmethod
    def _length3(v: Tuple[float, float, float]) -> float:
        return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])

    @classmethod
    def _normalize3(cls, v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        length = cls._length3(v)
        if length < 1e-9:
            return (0.0, 0.0, 0.0)
        inv = 1.0 / length
        return (v[0] * inv, v[1] * inv, v[2] * inv)

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        if value < low:
            return low
        if value > high:
            return high
        return value

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    # ------------------------------------------------------------------
    # Internal: Spherical Harmonics
    # ------------------------------------------------------------------

    @staticmethod
    def _sh_basis(direction: Tuple[float, float, float]) -> List[float]:
        x, y, z = direction
        return [
            0.28209479177387814,
            0.4886025119029199 * y,
            0.4886025119029199 * z,
            0.4886025119029199 * x,
            1.0925484305920792 * x * y,
            1.0925484305920792 * y * z,
            0.31539156525252005 * (3.0 * z * z - 1.0),
            1.0925484305920792 * x * z,
            0.5462742152960396 * (x * x - y * y),
        ]

    # ------------------------------------------------------------------
    # Internal: Hemisphere Sampling
    # ------------------------------------------------------------------

    @staticmethod
    def _hemisphere_sample(normal: Tuple[float, float, float], seed: int) -> Tuple[float, float, float]:
        rng = random.Random(seed)
        u1 = rng.random()
        u2 = rng.random()
        theta = 2.0 * math.pi * u1
        phi = math.acos(u2)
        sx = math.sin(phi) * math.cos(theta)
        sy = math.sin(phi) * math.sin(theta)
        sz = math.cos(phi)
        sample = (sx, sy, sz)
        if LightmappingEngine._dot3(sample, normal) < 0.0:
            sample = (-sx, -sy, -sz)
        return sample

    # ------------------------------------------------------------------
    # Public API: Settings
    # ------------------------------------------------------------------

    def create_settings(
        self,
        name: str,
        resolution_scale: float = 1.0,
        indirect_bounces: int = 2,
        ambient_occlusion: bool = True,
        ao_radius: float = 1.0,
        ao_samples: int = 16,
        shadow_softness: float = 0.5,
        denoise_enabled: bool = True,
        photon_count: int = 100000,
    ) -> BakeSettings:
        """Create a new BakeSettings configuration.

        Args:
            name: Human-readable name for these settings.
            resolution_scale: Scale factor for lightmap resolution (0.1-4.0).
            indirect_bounces: Number of indirect light bounces (0+).
            ambient_occlusion: Whether to compute ambient occlusion.
            ao_radius: AO sampling radius in world units.
            ao_samples: Number of hemisphere rays for AO.
            shadow_softness: Softness of shadow penumbras (0.0-1.0).
            denoise_enabled: Whether to apply denoising after bake.
            photon_count: Number of photons for photon mapping.

        Returns:
            The created BakeSettings instance.
        """
        with self._lock:
            settings = BakeSettings(
                name=name,
                resolution_scale=resolution_scale,
                indirect_bounces=indirect_bounces,
                ambient_occlusion=ambient_occlusion,
                ao_radius=ao_radius,
                ao_samples=ao_samples,
                shadow_softness=shadow_softness,
                denoise_enabled=denoise_enabled,
                photon_count=photon_count,
            )
            self._settings[settings.settings_id] = settings
            return settings

    # ------------------------------------------------------------------
    # Public API: Scene Management
    # ------------------------------------------------------------------

    def create_bake_scene(
        self, name: str, settings: BakeSettings
    ) -> BakedScene:
        """Create a new BakedScene with the given settings.

        Args:
            name: Human-readable scene name.
            settings: The BakeSettings to use for this scene.

        Returns:
            The created BakedScene instance.
        """
        with self._lock:
            scene = BakedScene(
                name=name,
                bake_settings=settings,
                lightmap_atlas=LightmapAtlas(
                    name=f"{name}_Atlas"
                ),
            )
            self._scenes[scene.scene_id] = scene
            self._stats["total_scenes_created"] += 1
            return scene

    def get_scene(self, scene_id: str) -> Optional[BakedScene]:
        """Retrieve a BakedScene by its ID.

        Args:
            scene_id: The unique scene identifier.

        Returns:
            The BakedScene if found, None otherwise.
        """
        with self._lock:
            return self._scenes.get(scene_id)

    def remove_scene(self, scene_id: str) -> bool:
        """Remove a BakedScene and cancel any active bake job.

        Args:
            scene_id: The unique scene identifier.

        Returns:
            True if the scene was removed, False if not found.
        """
        with self._lock:
            if scene_id in self._scenes:
                self.cancel_bake(scene_id)
                del self._scenes[scene_id]
                self._bake_jobs.pop(scene_id, None)
                return True
            return False

    # ------------------------------------------------------------------
    # Public API: Lights
    # ------------------------------------------------------------------

    def add_baked_light(
        self,
        scene_id: str,
        light_type: LightType,
        position: Tuple[float, float, float],
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
        cast_shadows: bool = True,
        bake_quality: BakeQuality = BakeQuality.MEDIUM,
    ) -> BakedLight:
        """Add a baked light source to a scene.

        Args:
            scene_id: The target scene identifier.
            light_type: Classification of the light source.
            position: World-space position as (x, y, z).
            color: RGB color with channels in [0.0, 1.0].
            intensity: Brightness multiplier (non-negative).
            cast_shadows: Whether this light casts shadows.
            bake_quality: Quality preset for this light.

        Returns:
            The created BakedLight instance.

        Raises:
            ValueError: If the scene is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"Scene not found: {scene_id}")

            shadow_samples = {
                BakeQuality.PREVIEW: 8,
                BakeQuality.LOW: 16,
                BakeQuality.MEDIUM: 32,
                BakeQuality.HIGH: 64,
                BakeQuality.ULTRA: 128,
            }.get(bake_quality, 32)

            light = BakedLight(
                light_type=light_type,
                position=position,
                color=color,
                intensity=intensity,
                cast_shadows=cast_shadows,
                shadow_samples=shadow_samples,
                bake_quality=bake_quality,
            )
            scene.baked_lights.append(light)
            self._stats["total_lights_registered"] += 1
            return light

    def add_emissive_surface(
        self,
        scene_id: str,
        mesh_name: str,
        emission_color: Tuple[float, float, float],
        emission_intensity: float = 1.0,
    ) -> BakedLight:
        """Register an emissive surface as a light source for baking.

        Emissive surfaces contribute indirect lighting during GI bakes
        by acting as area light sources on the mesh surface.

        Args:
            scene_id: The target scene identifier.
            mesh_name: Name of the mesh with emissive material.
            emission_color: RGB emission color in [0.0, 1.0].
            emission_intensity: Emission strength multiplier.

        Returns:
            The created BakedLight with EMISSIVE_SURFACE type.

        Raises:
            ValueError: If the scene is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"Scene not found: {scene_id}")

            light = BakedLight(
                light_type=LightType.EMISSIVE_SURFACE,
                position=(0.0, 0.0, 0.0),
                color=emission_color,
                intensity=emission_intensity,
                cast_shadows=False,
                shadow_samples=0,
                metadata={
                    "mesh_name": mesh_name,
                    "is_emissive": True,
                },
            )
            scene.baked_lights.append(light)
            self._stats["total_lights_registered"] += 1
            return light

    # ------------------------------------------------------------------
    # Public API: Mesh Registration
    # ------------------------------------------------------------------

    def add_mesh_to_bake(
        self,
        scene_id: str,
        mesh_name: str,
        geometry_data: Dict[str, Any],
        uv_channels: List[Dict[str, Any]],
    ) -> str:
        """Add a mesh to the scene for lightmap baking.

        Creates a LightmapRegion in the scene's atlas and stores the
        geometry data for use during ray tracing and AO computation.

        Args:
            scene_id: The target scene identifier.
            mesh_name: Name of the mesh to bake.
            geometry_data: Dictionary with 'vertices', 'normals', 'triangles'.
            uv_channels: List of UV channel descriptors.

        Returns:
            The region_id of the created LightmapRegion.

        Raises:
            ValueError: If the scene is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"Scene not found: {scene_id}")

            resolution_scale = 1.0
            if scene.bake_settings:
                resolution_scale = scene.bake_settings.resolution_scale

            base_res = 64
            res_w = max(1, int(base_res * resolution_scale))
            res_h = max(1, int(base_res * resolution_scale))

            region = LightmapRegion(
                mesh_name=mesh_name,
                resolution=(res_w, res_h),
            )

            if scene.lightmap_atlas is None:
                scene.lightmap_atlas = LightmapAtlas(
                    name=f"{scene.name}_Atlas"
                )

            offset_x = len(scene.lightmap_atlas.lightmaps) * 0.1
            region.uv_offset = (offset_x, 0.0)
            region.uv_scale = (0.1, 1.0)

            scene.lightmap_atlas.lightmaps.append(region)
            self._stats["total_regions_created"] += 1

            mesh_key = f"{scene_id}:{mesh_name}"
            self._mesh_geometry[mesh_key] = {
                "geometry": geometry_data,
                "uv_channels": uv_channels,
                "region_id": region.region_id,
            }

            return region.region_id

    # ------------------------------------------------------------------
    # Public API: Probe Placement
    # ------------------------------------------------------------------

    def place_light_probes(
        self,
        scene_id: str,
        bounds: Tuple[float, float, float, float, float, float],
        spacing: float = 2.0,
    ) -> LightProbeVolume:
        """Place a grid of light probes within a bounding volume.

        Probes are placed on a uniform 3D grid defined by the bounds and
        spacing. Each probe is initialized with zeroed SH coefficients
        and NOT_BAKED status.

        Args:
            scene_id: The target scene identifier.
            bounds: (min_x, min_y, min_z, max_x, max_y, max_z).
            spacing: Distance between adjacent probes in world units.

        Returns:
            The created LightProbeVolume.

        Raises:
            ValueError: If the scene is not found or bounds are invalid.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"Scene not found: {scene_id}")

            if spacing <= 0.0:
                raise ValueError("spacing must be positive")

            min_x, min_y, min_z, max_x, max_y, max_z = bounds
            if min_x >= max_x or min_y >= max_y or min_z >= max_z:
                raise ValueError("bounds must have min < max on all axes")

            volume = LightProbeVolume(
                name=f"{scene.name}_Probes",
                bounds=bounds,
                probe_spacing=spacing,
            )

            x = min_x
            while x <= max_x + spacing * 0.5:
                y = min_y
                while y <= max_y + spacing * 0.5:
                    z = min_z
                    while z <= max_z + spacing * 0.5:
                        probe = LightProbe(
                            position=(x, y, z),
                            influence_radius=spacing * 1.5,
                        )
                        volume.probes.append(probe)
                        self._stats["total_probes_placed"] += 1
                        z += spacing
                    y += spacing
                x += spacing

            scene.probe_volume = volume
            return volume

    # ------------------------------------------------------------------
    # Public API: Bake Configuration
    # ------------------------------------------------------------------

    def configure_bake_settings(
        self, scene_id: str, settings: BakeSettings
    ) -> bool:
        """Assign or update the bake settings for a scene.

        Args:
            scene_id: The target scene identifier.
            settings: The BakeSettings to apply.

        Returns:
            True if settings were applied, False if scene not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            scene.bake_settings = settings
            return True

    # ------------------------------------------------------------------
    # Public API: Bake Execution
    # ------------------------------------------------------------------

    def start_bake(self, scene_id: str, algorithm: GIAlgorithm) -> str:
        """Start an asynchronous bake for the given scene.

        Launches a background thread that runs the selected GI algorithm
        on the scene's lightmap regions and probe volume. Progress is
        tracked via the scene's bake_status and reported as a float.

        Args:
            scene_id: The target scene identifier.
            algorithm: The GI algorithm to use.

        Returns:
            The bake_job_id for tracking progress.

        Raises:
            ValueError: If the scene is not found or a bake is already running.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"Scene not found: {scene_id}")

            if scene.bake_status == BakeStatus.IN_PROGRESS:
                raise ValueError(
                    f"Bake already in progress for scene: {scene_id}"
                )

            job_id = uuid.uuid4().hex[:12]
            scene.bake_status = BakeStatus.IN_PROGRESS

            self._bake_jobs[scene_id] = {
                "job_id": job_id,
                "algorithm": algorithm.value,
                "progress": 0.0,
                "started_at": _time_module.time(),
            }
            self._cancel_flags[scene_id] = False
            self._stats["total_bakes_started"] += 1

        thread = threading.Thread(
            target=self._bake_lightmap_thread,
            args=(scene_id, algorithm),
            daemon=True,
        )
        self._bake_threads[scene_id] = thread
        thread.start()

        return job_id

    def get_bake_status(self, scene_id: str) -> BakeStatus:
        """Get the current bake status of a scene.

        Args:
            scene_id: The target scene identifier.

        Returns:
            The current BakeStatus, or NOT_BAKED if scene not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return BakeStatus.NOT_BAKED
            return scene.bake_status

    def get_bake_progress(self, scene_id: str) -> float:
        """Get the bake progress as a float in [0.0, 1.0].

        Args:
            scene_id: The target scene identifier.

        Returns:
            Progress value between 0.0 and 1.0, or 0.0 if not found.
        """
        with self._lock:
            job = self._bake_jobs.get(scene_id)
            if job is None:
                return 0.0
            return job.get("progress", 0.0)

    def cancel_bake(self, scene_id: str) -> bool:
        """Cancel an in-progress bake for a scene.

        Args:
            scene_id: The target scene identifier.

        Returns:
            True if a bake was cancelled, False if no active bake.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            if scene.bake_status != BakeStatus.IN_PROGRESS:
                return False
            self._cancel_flags[scene_id] = True
            scene.bake_status = BakeStatus.NOT_BAKED
            self._stats["total_bakes_cancelled"] += 1

            job = self._bake_jobs.get(scene_id)
            if job:
                job["progress"] = 0.0
            return True

    # ------------------------------------------------------------------
    # Public API: Runtime Sampling
    # ------------------------------------------------------------------

    def sample_lighting(
        self,
        position: Tuple[float, float, float],
        normal: Tuple[float, float, float],
    ) -> Dict[str, Any]:
        """Sample baked lighting at a world-space position.

        Computes direct lighting contribution from all baked lights in
        all scenes and combines with indirect lighting from probe
        interpolation. Returns RGB color, occlusion factor, and
        indirect lighting contribution.

        Args:
            position: World-space sample point as (x, y, z).
            normal: Surface normal at the sample point.

        Returns:
            Dictionary with 'rgb', 'occlusion', and 'indirect' keys.
        """
        with self._lock:
            total_r = 0.0
            total_g = 0.0
            total_b = 0.0
            occlusion = 1.0
            indirect_r = 0.0
            indirect_g = 0.0
            indirect_b = 0.0

            n = self._normalize3(normal)

            for scene in self._scenes.values():
                if scene.bake_status not in (
                    BakeStatus.COMPLETED, BakeStatus.PARTIAL
                ):
                    continue

                for light in scene.baked_lights:
                    if light.light_type == LightType.EMISSIVE_SURFACE:
                        continue

                    contrib = self._compute_light_contribution(
                        light, position, n
                    )
                    if contrib is None:
                        continue
                    total_r += contrib[0]
                    total_g += contrib[1]
                    total_b += contrib[2]

                if scene.bake_settings and scene.bake_settings.ambient_occlusion:
                    occlusion = self._compute_ao(
                        position, n, scene,
                        scene.bake_settings.ao_radius,
                        scene.bake_settings.ao_samples,
                    )

                indirect = self.sample_probe_lighting(position)
                indirect_r = indirect.get("indirect_r", 0.0)
                indirect_g = indirect.get("indirect_g", 0.0)
                indirect_b = indirect.get("indirect_b", 0.0)

            return {
                "rgb": (
                    self._clamp(total_r, 0.0, 1.0),
                    self._clamp(total_g, 0.0, 1.0),
                    self._clamp(total_b, 0.0, 1.0),
                ),
                "occlusion": round(occlusion, 4),
                "indirect": (
                    round(indirect_r, 4),
                    round(indirect_g, 4),
                    round(indirect_b, 4),
                ),
            }

    def sample_probe_lighting(
        self, position: Tuple[float, float, float]
    ) -> Dict[str, Any]:
        """Sample probe-based indirect lighting at a world position.

        Interpolates spherical harmonics coefficients from the nearest
        probes across all scene volumes using inverse-distance weighting.

        Args:
            position: World-space sample point as (x, y, z).

        Returns:
            Dictionary with 'indirect_r', 'indirect_g', 'indirect_b',
            'probe_count', and 'sh_coefficients' keys.
        """
        with self._lock:
            all_probes: List[Tuple[float, LightProbe]] = []

            for scene in self._scenes.values():
                if scene.probe_volume is None:
                    continue
                for probe in scene.probe_volume.probes:
                    if probe.bake_status != BakeStatus.COMPLETED:
                        continue
                    dist = self._length3(
                        self._sub3(probe.position, position)
                    )
                    if dist <= probe.influence_radius:
                        all_probes.append((max(dist, 1e-6), probe))

            if not all_probes:
                return {
                    "indirect_r": 0.0,
                    "indirect_g": 0.0,
                    "indirect_b": 0.0,
                    "probe_count": 0,
                    "sh_coefficients": [0.0] * 27,
                }

            all_probes.sort(key=lambda item: item[0])
            selected = all_probes[:4]

            result = self._interpolate_probes(
                [p for _, p in selected], position
            )

            return {
                "indirect_r": round(result["r"], 4),
                "indirect_g": round(result["g"], 4),
                "indirect_b": round(result["b"], 4),
                "probe_count": len(selected),
                "sh_coefficients": result["coefficients"],
            }

    # ------------------------------------------------------------------
    # Public API: Lightmap Post-Processing
    # ------------------------------------------------------------------

    def apply_lightmap_to_mesh(
        self, scene_id: str, region_id: str
    ) -> Dict[str, Any]:
        """Apply baked lightmap data to a mesh region.

        Returns the current texel data for the region, suitable for
        uploading to a GPU texture or further processing.

        Args:
            scene_id: The target scene identifier.
            region_id: The region identifier within the atlas.

        Returns:
            Dictionary with texel data, resolution, and status.

        Raises:
            ValueError: If the scene or region is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"Scene not found: {scene_id}")
            if scene.lightmap_atlas is None:
                raise ValueError(f"Scene has no lightmap atlas: {scene_id}")

            region: Optional[LightmapRegion] = None
            for r in scene.lightmap_atlas.lightmaps:
                if r.region_id == region_id:
                    region = r
                    break

            if region is None:
                raise ValueError(f"Region not found: {region_id}")

            return {
                "region_id": region.region_id,
                "mesh_name": region.mesh_name,
                "resolution": list(region.resolution),
                "texel_data": [
                    [list(texel) for texel in row]
                    for row in region.texel_data
                ],
                "status": region.status.value,
            }

    def denoise_lightmap(
        self, scene_id: str, region_id: str
    ) -> Dict[str, Any]:
        """Apply a bilateral denoising filter to a lightmap region.

        Smooths the texel data while preserving edges using a
        simplified bilateral filter kernel. The denoising strength
        is controlled by the scene's bake settings.

        Args:
            scene_id: The target scene identifier.
            region_id: The region identifier within the atlas.

        Returns:
            Dictionary with denoised texel data and filter parameters.

        Raises:
            ValueError: If the scene or region is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                raise ValueError(f"Scene not found: {scene_id}")
            if scene.lightmap_atlas is None:
                raise ValueError(f"Scene has no lightmap atlas: {scene_id}")

            region: Optional[LightmapRegion] = None
            for r in scene.lightmap_atlas.lightmaps:
                if r.region_id == region_id:
                    region = r
                    break

            if region is None:
                raise ValueError(f"Region not found: {region_id}")

            strength = 0.75
            if scene.bake_settings:
                strength = scene.bake_settings.denoise_strength

            w, h = region.resolution
            denoised: List[List[Tuple[float, float, float]]] = [
                [(0.0, 0.0, 0.0) for _ in range(w)]
                for _ in range(h)
            ]

            kernel_size = 2
            for y in range(h):
                for x in range(w):
                    sum_r = 0.0
                    sum_g = 0.0
                    sum_b = 0.0
                    total_weight = 0.0

                    center = region.texel_data[y][x]
                    center_lum = (
                        center[0] * 0.299
                        + center[1] * 0.587
                        + center[2] * 0.114
                    )

                    for ky in range(-kernel_size, kernel_size + 1):
                        for kx in range(-kernel_size, kernel_size + 1):
                            nx = x + kx
                            ny = y + ky
                            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                                continue

                            spatial_dist = math.sqrt(
                                kx * kx + ky * ky
                            )
                            spatial_weight = math.exp(
                                -spatial_dist * spatial_dist
                                / (2.0 * strength * strength)
                            )

                            neighbor = region.texel_data[ny][nx]
                            neighbor_lum = (
                                neighbor[0] * 0.299
                                + neighbor[1] * 0.587
                                + neighbor[2] * 0.114
                            )
                            range_dist = abs(neighbor_lum - center_lum)
                            range_weight = math.exp(
                                -range_dist * range_dist
                                / (2.0 * 0.1 * 0.1)
                            )

                            weight = spatial_weight * range_weight
                            sum_r += neighbor[0] * weight
                            sum_g += neighbor[1] * weight
                            sum_b += neighbor[2] * weight
                            total_weight += weight

                    if total_weight > 0.0:
                        denoised[y][x] = (
                            sum_r / total_weight,
                            sum_g / total_weight,
                            sum_b / total_weight,
                        )
                    else:
                        denoised[y][x] = center

            region.texel_data = denoised

            return {
                "region_id": region.region_id,
                "mesh_name": region.mesh_name,
                "resolution": list(region.resolution),
                "texel_data": [
                    [list(texel) for texel in row]
                    for row in region.texel_data
                ],
                "denoise_strength": strength,
                "kernel_size": kernel_size,
            }

    def export_lightmap(
        self, scene_id: str, region_id: str, file_path: str
    ) -> bool:
        """Export a lightmap region to a file on disk.

        Writes the texel data as a raw RGB float binary file. Each texel
        is written as three 32-bit little-endian floats. A companion JSON
        metadata file is written alongside with region information.

        Args:
            scene_id: The target scene identifier.
            region_id: The region identifier to export.
            file_path: Destination file path (without extension).

        Returns:
            True if export succeeded, False otherwise.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None or scene.lightmap_atlas is None:
                return False

            region: Optional[LightmapRegion] = None
            for r in scene.lightmap_atlas.lightmaps:
                if r.region_id == region_id:
                    region = r
                    break

            if region is None:
                return False

            try:
                os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

                raw_path = file_path + ".lmap"
                with open(raw_path, "wb") as f:
                    w, h = region.resolution
                    f.write(struct.pack("<II", w, h))
                    for row in region.texel_data:
                        for texel in row:
                            f.write(struct.pack(
                                "<fff",
                                texel[0], texel[1], texel[2],
                            ))

                meta_path = file_path + ".json"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "region_id": region.region_id,
                        "mesh_name": region.mesh_name,
                        "resolution": list(region.resolution),
                        "uv_offset": list(region.uv_offset),
                        "uv_scale": list(region.uv_scale),
                        "status": region.status.value,
                    }, f, indent=2)

                self._stats["total_lightmaps_exported"] += 1
                return True

            except (OSError, IOError):
                return False

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the lightmapping system.

        Returns:
            Dictionary with counts, timing, and distribution data.
        """
        with self._lock:
            total_regions = 0
            total_texels = 0
            total_probes = 0
            status_counts: Dict[str, int] = {
                s.value: 0 for s in BakeStatus
            }
            light_type_counts: Dict[str, int] = {
                lt.value: 0 for lt in LightType
            }

            for scene in self._scenes.values():
                status_counts[scene.bake_status.value] += 1
                if scene.lightmap_atlas:
                    total_regions += len(scene.lightmap_atlas.lightmaps)
                    total_texels += scene.lightmap_atlas.occupied_texels
                if scene.probe_volume:
                    total_probes += len(scene.probe_volume.probes)
                for light in scene.baked_lights:
                    light_type_counts[light.light_type.value] += 1

            active_jobs = sum(
                1 for s in self._scenes.values()
                if s.bake_status == BakeStatus.IN_PROGRESS
            )

            avg_bake_time = 0.0
            if self._stats["total_bakes_completed"] > 0:
                avg_bake_time = (
                    self._stats["total_bake_time_seconds"]
                    / self._stats["total_bakes_completed"]
                )

            return {
                "total_scenes": len(self._scenes),
                "total_settings": len(self._settings),
                "total_regions": total_regions,
                "total_texels": total_texels,
                "total_probes": total_probes,
                "active_bake_jobs": active_jobs,
                "total_bakes_started": self._stats["total_bakes_started"],
                "total_bakes_completed": self._stats["total_bakes_completed"],
                "total_bakes_failed": self._stats["total_bakes_failed"],
                "total_bakes_cancelled": self._stats["total_bakes_cancelled"],
                "total_lights_registered": self._stats["total_lights_registered"],
                "total_regions_created": self._stats["total_regions_created"],
                "total_probes_placed": self._stats["total_probes_placed"],
                "total_lightmaps_exported": self._stats["total_lightmaps_exported"],
                "total_bake_time_seconds": round(
                    self._stats["total_bake_time_seconds"], 4
                ),
                "avg_bake_time_seconds": round(avg_bake_time, 4),
                "scene_status_distribution": status_counts,
                "light_type_distribution": light_type_counts,
            }

    # ------------------------------------------------------------------
    # Internal: Light Contribution
    # ------------------------------------------------------------------

    def _compute_light_contribution(
        self,
        light: BakedLight,
        position: Tuple[float, float, float],
        normal: Tuple[float, float, float],
    ) -> Optional[Tuple[float, float, float]]:
        """Compute the contribution of a single baked light at a point."""
        if light.light_type == LightType.DIRECTIONAL:
            light_dir = (0.0, -1.0, 0.0)
            attenuation = 1.0
        else:
            to_light = self._sub3(light.position, position)
            dist = self._length3(to_light)
            if dist < 1e-9:
                return None
            light_dir = self._normalize3(to_light)
            attenuation = 1.0 / (1.0 + dist * dist)

        n_dot_l = self._dot3(normal, light_dir)
        if n_dot_l <= 0.0:
            return None

        if light.light_type == LightType.SPOT:
            spot_dir = (0.0, -1.0, 0.0)
            cos_angle = self._dot3(spot_dir, light_dir)
            cos_cutoff = math.cos(math.radians(45.0))
            if cos_angle < cos_cutoff:
                return None
            spot_factor = (cos_angle - cos_cutoff) / (1.0 - cos_cutoff)
            attenuation *= spot_factor

        contribution = light.intensity * n_dot_l * attenuation
        return (
            light.color[0] * contribution,
            light.color[1] * contribution,
            light.color[2] * contribution,
        )

    # ------------------------------------------------------------------
    # Internal: Ray Tracing
    # ------------------------------------------------------------------

    def _trace_rays(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        scene: BakedScene,
        max_bounces: int,
    ) -> Dict[str, Any]:
        """Trace a ray through the scene for path tracing.

        Simulates ray bounces through the scene's baked lights and
        emissive surfaces. Returns accumulated color, hit information,
        and the number of bounces traced.

        Args:
            origin: Ray origin in world space.
            direction: Normalized ray direction.
            scene: The BakedScene to trace against.
            max_bounces: Maximum number of indirect bounces.

        Returns:
            Dictionary with 'color', 'hit', 'bounces', 'distance'.
        """
        accumulated_r = 0.0
        accumulated_g = 0.0
        accumulated_b = 0.0
        current_origin = origin
        current_dir = self._normalize3(direction)
        throughput = (1.0, 1.0, 1.0)
        hit = False
        total_distance = 0.0
        bounces = 0

        for bounce in range(max_bounces + 1):
            closest_dist = float("inf")
            closest_light: Optional[BakedLight] = None

            for light in scene.baked_lights:
                if light.light_type == LightType.DIRECTIONAL:
                    dist = 1000.0
                else:
                    to_light = self._sub3(light.position, current_origin)
                    dist = self._length3(to_light)

                if dist < closest_dist:
                    closest_dist = dist
                    closest_light = light

            if closest_light is None:
                break

            bounces = bounce
            hit = True
            total_distance += closest_dist

            if closest_light.light_type == LightType.DIRECTIONAL:
                light_dir = (0.0, -1.0, 0.0)
            else:
                light_dir = self._normalize3(
                    self._sub3(closest_light.position, current_origin)
                )

            cos_theta = abs(self._dot3(light_dir, current_dir))
            contrib = closest_light.intensity * cos_theta

            accumulated_r += throughput[0] * closest_light.color[0] * contrib
            accumulated_g += throughput[1] * closest_light.color[1] * contrib
            accumulated_b += throughput[2] * closest_light.color[2] * contrib

            # Russian roulette termination
            if bounce > 2:
                survival = max(throughput)
                if random.random() > survival:
                    break
                scale = 1.0 / survival
                throughput = (
                    throughput[0] * scale,
                    throughput[1] * scale,
                    throughput[2] * scale,
                )

            # Scatter
            scatter_dir = self._hemisphere_sample(
                light_dir, hash(current_origin) + bounce
            )
            throughput = (
                throughput[0] * 0.8,
                throughput[1] * 0.8,
                throughput[2] * 0.8,
            )
            current_origin = self._add3(
                current_origin,
                self._mul3(current_dir, closest_dist * 0.99),
            )
            current_dir = scatter_dir

        return {
            "color": (
                self._clamp(accumulated_r, 0.0, 1.0),
                self._clamp(accumulated_g, 0.0, 1.0),
                self._clamp(accumulated_b, 0.0, 1.0),
            ),
            "hit": hit,
            "bounces": bounces,
            "distance": total_distance,
        }

    # ------------------------------------------------------------------
    # Internal: Ambient Occlusion
    # ------------------------------------------------------------------

    def _compute_ao(
        self,
        position: Tuple[float, float, float],
        normal: Tuple[float, float, float],
        scene: BakedScene,
        radius: float,
        samples: int,
    ) -> float:
        """Compute ambient occlusion via hemisphere sampling.

        Casts sample rays into the hemisphere and checks for occlusion
        against the scene's baked lights as a geometric proxy. Returns
        an AO factor in [0.0, 1.0] where 1.0 is fully unoccluded.

        Args:
            position: World-space sample point.
            normal: Surface normal at the point.
            scene: The scene containing occlusion geometry.
            radius: AO sampling radius.
            samples: Number of hemisphere rays.

        Returns:
            AO factor in [0.0, 1.0].
        """
        if samples <= 0:
            return 1.0

        n = self._normalize3(normal)
        occluded = 0

        for i in range(samples):
            seed = hash(position) ^ i ^ int(normal[0] * 1000)
            sample_dir = self._hemisphere_sample(n, seed)

            sample_point = self._add3(
                position, self._mul3(sample_dir, radius)
            )

            for light in scene.baked_lights:
                if light.light_type == LightType.EMISSIVE_SURFACE:
                    continue
                if light.light_type == LightType.DIRECTIONAL:
                    continue
                to_light = self._sub3(light.position, sample_point)
                dist = self._length3(to_light)
                if dist < radius * 0.5:
                    occluded += 1
                    break

            if occluded > samples * 0.75:
                break

        return 1.0 - (occluded / samples)

    # ------------------------------------------------------------------
    # Internal: Spherical Harmonics Computation
    # ------------------------------------------------------------------

    def _calculate_spherical_harmonics(
        self, samples: List[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]
    ) -> List[float]:
        """Compute 27 SH coefficients from a set of direction-color samples.

        Each sample is a (direction, color) pair. The direction is used
        to evaluate the SH basis functions, and the color is projected
        onto each basis to produce per-channel coefficients.

        Args:
            samples: List of ((dx, dy, dz), (r, g, b)) tuples.

        Returns:
            A list of 27 float values (9 coefficients x 3 RGB channels).
        """
        coeff_count = 9
        coeffs_r = [0.0] * coeff_count
        coeffs_g = [0.0] * coeff_count
        coeffs_b = [0.0] * coeff_count

        if not samples:
            return [0.0] * 27

        for direction, color in samples:
            d = self._normalize3(direction)
            basis = self._sh_basis(d)
            for i in range(coeff_count):
                coeffs_r[i] += color[0] * basis[i]
                coeffs_g[i] += color[1] * basis[i]
                coeffs_b[i] += color[2] * basis[i]

        scale = (4.0 * math.pi) / len(samples)
        result: List[float] = []
        for coeffs in (coeffs_r, coeffs_g, coeffs_b):
            for i in range(coeff_count):
                result.append(coeffs[i] * scale)

        return result

    # ------------------------------------------------------------------
    # Internal: Probe Interpolation
    # ------------------------------------------------------------------

    def _interpolate_probes(
        self,
        probes: List[LightProbe],
        position: Tuple[float, float, float],
    ) -> Dict[str, Any]:
        """Interpolate SH coefficients from a set of probes.

        Uses inverse-distance weighting to blend the spherical harmonics
        coefficients of the provided probes. Evaluates the blended SH
        against the ambient direction to produce an RGB irradiance value.

        Args:
            probes: List of LightProbe instances to interpolate.
            position: The world-space position being sampled.

        Returns:
            Dictionary with 'r', 'g', 'b', and 'coefficients' keys.
        """
        if not probes:
            return {
                "r": 0.0, "g": 0.0, "b": 0.0,
                "coefficients": [0.0] * 27,
            }

        blended = [0.0] * 27
        total_weight = 0.0

        for probe in probes:
            dist = self._length3(
                self._sub3(probe.position, position)
            )
            dist = max(dist, 1e-6)
            weight = 1.0 / (dist * dist)

            for i in range(27):
                blended[i] += probe.spherical_harmonics[i] * weight
            total_weight += weight

        if total_weight > 0.0:
            for i in range(27):
                blended[i] /= total_weight

        ambient_dir = (0.0, 1.0, 0.0)
        basis = self._sh_basis(ambient_dir)

        r = 0.0
        g = 0.0
        b = 0.0
        for i in range(9):
            r += blended[i] * basis[i]
            g += blended[i + 9] * basis[i]
            b += blended[i + 18] * basis[i]

        return {
            "r": self._clamp(r, 0.0, 1.0),
            "g": self._clamp(g, 0.0, 1.0),
            "b": self._clamp(b, 0.0, 1.0),
            "coefficients": blended,
        }

    # ------------------------------------------------------------------
    # Internal: Bake Thread
    # ------------------------------------------------------------------

    def _bake_lightmap_thread(
        self, scene_id: str, algorithm: GIAlgorithm
    ) -> None:
        """Background thread executing the bake operation.

        Iterates over the scene's lightmap regions, computing per-texel
        lighting using the selected GI algorithm. Updates progress and
        finalizes the scene's bake status on completion or failure.

        Args:
            scene_id: The scene being baked.
            algorithm: The GI algorithm to apply.
        """
        start_time = _time_module.time()

        try:
            with self._lock:
                scene = self._scenes.get(scene_id)
                if scene is None:
                    return

            total_texels = 0
            if scene.lightmap_atlas:
                total_texels = sum(
                    r.texel_count for r in scene.lightmap_atlas.lightmaps
                )

            if scene.probe_volume:
                total_texels += len(scene.probe_volume.probes)

            if total_texels <= 0:
                with self._lock:
                    scene.bake_status = BakeStatus.COMPLETED
                    scene.bake_time = _time_module.time() - start_time
                    self._stats["total_bakes_completed"] += 1
                    self._stats["total_bake_time_seconds"] += scene.bake_time
                    if scene_id in self._bake_jobs:
                        self._bake_jobs[scene_id]["progress"] = 1.0
                return

            processed = 0

            if scene.lightmap_atlas:
                for region in scene.lightmap_atlas.lightmaps:
                    if self._cancel_flags.get(scene_id, False):
                        return

                    settings = scene.bake_settings
                    bounces = settings.indirect_bounces if settings else 0
                    ao_enabled = (
                        settings.ambient_occlusion if settings else False
                    )
                    ao_rad = settings.ao_radius if settings else 1.0
                    ao_smp = settings.ao_samples if settings else 16

                    w, h = region.resolution
                    for y in range(h):
                        for x in range(w):
                            if self._cancel_flags.get(scene_id, False):
                                return

                            u = (x + 0.5) / w
                            v = (y + 0.5) / h
                            world_pos = (
                                (u - 0.5) * 10.0,
                                0.0,
                                (v - 0.5) * 10.0,
                            )
                            world_normal = (0.0, 1.0, 0.0)

                            if algorithm == GIAlgorithm.PATH_TRACER:
                                result = self._trace_rays(
                                    world_pos,
                                    world_normal,
                                    scene,
                                    bounces,
                                )
                                color = result["color"]
                            elif algorithm == GIAlgorithm.PHOTON_MAPPING:
                                color = self._bake_photon_mapping(
                                    world_pos, world_normal, scene
                                )
                            elif algorithm == GIAlgorithm.RADIOSITY:
                                color = self._bake_radiosity(
                                    world_pos, world_normal, scene
                                )
                            else:
                                color = (0.5, 0.5, 0.5)

                            if ao_enabled:
                                ao = self._compute_ao(
                                    world_pos, world_normal,
                                    scene, ao_rad, ao_smp,
                                )
                                color = (
                                    color[0] * ao,
                                    color[1] * ao,
                                    color[2] * ao,
                                )

                            region.texel_data[y][x] = (
                                self._clamp(color[0], 0.0, 1.0),
                                self._clamp(color[1], 0.0, 1.0),
                                self._clamp(color[2], 0.0, 1.0),
                            )

                            processed += 1
                            with self._lock:
                                if scene_id in self._bake_jobs:
                                    self._bake_jobs[scene_id][
                                        "progress"
                                    ] = processed / total_texels

                    region.status = BakeStatus.COMPLETED

            if scene.probe_volume:
                for probe in scene.probe_volume.probes:
                    if self._cancel_flags.get(scene_id, False):
                        return

                    sample_list: List[
                        Tuple[
                            Tuple[float, float, float],
                            Tuple[float, float, float],
                        ]
                    ] = []
                    rng = random.Random(hash(probe.position))
                    for _ in range(32):
                        theta = 2.0 * math.pi * rng.random()
                        phi = math.acos(2.0 * rng.random() - 1.0)
                        d = (
                            math.sin(phi) * math.cos(theta),
                            math.sin(phi) * math.sin(theta),
                            math.cos(phi),
                        )
                        c = self._sample_direction_lighting(
                            probe.position, d, scene
                        )
                        sample_list.append((d, c))

                    probe.spherical_harmonics = (
                        self._calculate_spherical_harmonics(sample_list)
                    )
                    probe.bake_status = BakeStatus.COMPLETED

                    processed += 1
                    with self._lock:
                        if scene_id in self._bake_jobs:
                            self._bake_jobs[scene_id][
                                "progress"
                            ] = processed / total_texels

            elapsed = _time_module.time() - start_time

            with self._lock:
                scene.bake_status = BakeStatus.COMPLETED
                scene.bake_time = elapsed
                self._stats["total_bakes_completed"] += 1
                self._stats["total_bake_time_seconds"] += elapsed
                if scene_id in self._bake_jobs:
                    self._bake_jobs[scene_id]["progress"] = 1.0

        except Exception:
            with self._lock:
                scene.bake_status = BakeStatus.FAILED
                scene.bake_time = _time_module.time() - start_time
                self._stats["total_bakes_failed"] += 1
                if scene_id in self._bake_jobs:
                    self._bake_jobs[scene_id]["progress"] = 0.0

    def _bake_photon_mapping(
        self,
        position: Tuple[float, float, float],
        normal: Tuple[float, float, float],
        scene: BakedScene,
    ) -> Tuple[float, float, float]:
        """Compute lighting using a simplified photon mapping approach.

        Simulates photon emission from baked lights and gathers photon
        density at the surface point. Uses a sphere gathering kernel
        with exponential falloff for photon density estimation.

        Args:
            position: World-space surface point.
            normal: Surface normal at the point.
            scene: The scene containing photon sources.

        Returns:
            Estimated RGB color at the point.
        """
        n = self._normalize3(normal)
        photon_count = 1000
        if scene.bake_settings:
            photon_count = max(100, scene.bake_settings.photon_count // 100)

        accumulated_r = 0.0
        accumulated_g = 0.0
        accumulated_b = 0.0
        gather_radius = 2.0
        rng = random.Random(hash(position) ^ photon_count)

        for light in scene.baked_lights:
            if light.light_type == LightType.EMISSIVE_SURFACE:
                continue

            total_weight = 0.0
            for _ in range(photon_count // max(1, len(scene.baked_lights))):
                if light.light_type == LightType.DIRECTIONAL:
                    photon_dir = (0.0, -1.0, 0.0)
                    photon_origin = self._add3(
                        position,
                        self._mul3(
                            (
                                rng.uniform(-10, 10),
                                10.0,
                                rng.uniform(-10, 10),
                            ),
                            1.0,
                        ),
                    )
                else:
                    photon_dir = self._hemisphere_sample(
                        (0.0, 1.0, 0.0),
                        rng.randint(0, 2**31 - 1),
                    )
                    photon_origin = self._add3(
                        light.position,
                        self._mul3(photon_dir, rng.random() * 10.0),
                    )

                to_point = self._sub3(position, photon_origin)
                dist = self._length3(to_point)

                if dist < gather_radius:
                    weight = math.exp(-dist * dist / (gather_radius * gather_radius))
                    n_dot_l = max(0.0, self._dot3(n, self._normalize3(to_point)))
                    accumulated_r += light.color[0] * light.intensity * weight * n_dot_l
                    accumulated_g += light.color[1] * light.intensity * weight * n_dot_l
                    accumulated_b += light.color[2] * light.intensity * weight * n_dot_l
                    total_weight += weight

            if total_weight > 0.0:
                accumulated_r /= total_weight
                accumulated_g /= total_weight
                accumulated_b /= total_weight

        return (
            self._clamp(accumulated_r, 0.0, 1.0),
            self._clamp(accumulated_g, 0.0, 1.0),
            self._clamp(accumulated_b, 0.0, 1.0),
        )

    def _bake_radiosity(
        self,
        position: Tuple[float, float, float],
        normal: Tuple[float, float, float],
        scene: BakedScene,
    ) -> Tuple[float, float, float]:
        """Compute lighting using a simplified radiosity approach.

        Simulates diffuse interreflection by iteratively distributing
        light energy from each baked light and emissive surface across
        the hemisphere, accumulating form-factor-weighted contributions.

        Args:
            position: World-space surface point.
            normal: Surface normal at the point.
            scene: The scene with light sources.

        Returns:
            Estimated RGB color at the point.
        """
        n = self._normalize3(normal)
        accumulated_r = 0.0
        accumulated_g = 0.0
        accumulated_b = 0.0
        iterations = 3

        rng = random.Random(hash(position))

        for _ in range(iterations):
            for light in scene.baked_lights:
                if light.light_type == LightType.DIRECTIONAL:
                    to_light = (0.0, 1.0, 0.0)
                    dist = 1.0
                else:
                    to_light = self._sub3(light.position, position)
                    dist = self._length3(to_light)

                if dist < 1e-9:
                    continue

                light_dir = self._normalize3(to_light)
                n_dot_l = self._dot3(n, light_dir)
                if n_dot_l <= 0.0:
                    continue

                form_factor = n_dot_l / (math.pi * dist * dist)

                if light.light_type == LightType.EMISSIVE_SURFACE:
                    accumulated_r += light.color[0] * light.intensity * form_factor * 0.5
                    accumulated_g += light.color[1] * light.intensity * form_factor * 0.5
                    accumulated_b += light.color[2] * light.intensity * form_factor * 0.5
                else:
                    accumulated_r += light.color[0] * light.intensity * form_factor
                    accumulated_g += light.color[1] * light.intensity * form_factor
                    accumulated_b += light.color[2] * light.intensity * form_factor

            # Simulate bounce by adding a fraction of accumulated energy
            accumulated_r *= 0.3
            accumulated_g *= 0.3
            accumulated_b *= 0.3

        return (
            self._clamp(accumulated_r, 0.0, 1.0),
            self._clamp(accumulated_g, 0.0, 1.0),
            self._clamp(accumulated_b, 0.0, 1.0),
        )

    def _sample_direction_lighting(
        self,
        position: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        scene: BakedScene,
    ) -> Tuple[float, float, float]:
        """Sample incoming lighting from a direction for probe computation.

        Args:
            position: World-space probe position.
            direction: Sampling direction.
            scene: The scene to sample from.

        Returns:
            RGB color tuple from the sampled direction.
        """
        d = self._normalize3(direction)
        r = 0.0
        g = 0.0
        b = 0.0

        for light in scene.baked_lights:
            if light.light_type == LightType.EMISSIVE_SURFACE:
                continue
            if light.light_type == LightType.DIRECTIONAL:
                light_dir = (0.0, -1.0, 0.0)
            else:
                to_light = self._sub3(light.position, position)
                dist = self._length3(to_light)
                if dist < 1e-9:
                    continue
                light_dir = self._normalize3(to_light)

            cos_angle = self._dot3(d, light_dir)
            if cos_angle > 0.0:
                contrib = light.intensity * cos_angle
                r += light.color[0] * contrib
                g += light.color[1] * contrib
                b += light.color[2] * contrib

        return (
            self._clamp(r, 0.0, 1.0),
            self._clamp(g, 0.0, 1.0),
            self._clamp(b, 0.0, 1.0),
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all lightmapping state to defaults."""
        with self._lock:
            for scene_id in list(self._bake_threads.keys()):
                self._cancel_flags[scene_id] = True

            self._scenes.clear()
            self._settings.clear()
            self._bake_jobs.clear()
            self._bake_threads.clear()
            self._cancel_flags.clear()
            self._mesh_geometry.clear()
            self._stats = {
                "total_scenes_created": 0,
                "total_bakes_started": 0,
                "total_bakes_completed": 0,
                "total_bakes_failed": 0,
                "total_bakes_cancelled": 0,
                "total_lights_registered": 0,
                "total_regions_created": 0,
                "total_probes_placed": 0,
                "total_lightmaps_exported": 0,
                "total_bake_time_seconds": 0.0,
            }

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"LightmappingEngine(scenes={len(self._scenes)}, "
                f"settings={len(self._settings)}, "
                f"active_jobs={len(self._bake_threads)}, "
                f"lights={self._stats['total_lights_registered']})"
            )


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_lightmapping() -> LightmappingEngine:
    """Get or create the singleton LightmappingEngine instance."""
    return LightmappingEngine.get_instance()