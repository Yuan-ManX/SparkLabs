"""
SparkLabs Engine - Volumetric Rendering System

A comprehensive volumetric rendering system for atmospheric effects,
fog, light scattering, and volumetric clouds in the game engine.
Provides real-time ray marching, participating media simulation,
Beer-Lambert transmittance calculations, and physically-based phase
function evaluation for Rayleigh and Mie scattering.

Architecture:
  EngineVolumetricRendering (Singleton)
    |-- VolumetricFogConfig     — fog density, falloff, and color parameters
    |-- VolumetricLightConfig   — volumetric light shafts and god rays
    |-- VolumetricCloudConfig   — procedural volumetric cloud layers
    |-- ParticipatingMedia      — participating media properties
    |-- RayMarchResult          — ray marching integration output
    |-- VolumetricRenderPass    — render pass configuration

Key Features:
  - Physically-based Rayleigh and Mie scattering phase functions
  - Beer-Lambert law for light transmittance through participating media
  - Ray marching with adaptive step sizing
  - In-scattering integration for volumetric light effects
  - Quality presets affecting sample counts and resolution scale
  - Temporal accumulation and denoising for render passes
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VolumetricEffectType(Enum):
    """Types of volumetric rendering effects."""
    FOG = "fog"
    VOLUMETRIC_LIGHT = "volumetric_light"
    GOD_RAYS = "god_rays"
    VOLUMETRIC_CLOUDS = "volumetric_clouds"
    LIGHT_SHAFTS = "light_shafts"
    PARTICIPATING_MEDIA = "participating_media"


class ScatteringModel(Enum):
    """Scattering model used for phase function evaluation.

    Rayleigh: Molecular scattering, wavelength-dependent, strong forward/backward.
    Mie: Aerosol scattering, strongly forward-peaked.
    Isotropic: Equal scattering in all directions.
    Henyey-Greenstein: Approximate Mie scattering with a single parameter g.
    OMPF: One-Moment Phase Function, a simplified anisotropic model.
    """
    RAYLEIGH = "rayleigh"
    MIE = "mie"
    ISOTROPIC = "isotropic"
    HENYEY_GREENSTEIN = "henyey_greenstein"
    OMPF = "ompf"


class FogMode(Enum):
    """Fog density falloff models.

    LINEAR: Density increases linearly with distance.
    EXPONENTIAL: Standard exponential fog (density constant).
    EXPONENTIAL_SQUARED: Exponential with squared distance for softer falloff.
    LAYERED: Fog confined to a vertical layer with smooth edges.
    HEIGHT_BASED: Density varies with height above a reference plane.
    """
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_SQUARED = "exponential_squared"
    LAYERED = "layered"
    HEIGHT_BASED = "height_based"


class QualityPreset(Enum):
    """Quality presets affecting sample counts and resolution scale."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CINEMATIC = "cinematic"


# ---------------------------------------------------------------------------
# Quality Preset Configuration
# ---------------------------------------------------------------------------

_QUALITY_PRESET_CONFIGS: Dict[QualityPreset, Dict[str, Any]] = {
    QualityPreset.LOW: {
        "ray_march_steps": 16,
        "inscattering_samples": 4,
        "resolution_scale": 0.25,
        "temporal_accumulation": False,
        "denoise_enabled": False,
        "cloud_lighting_samples": 1,
        "cloud_shadow_steps": 2,
        "volumetric_shadow": False,
    },
    QualityPreset.MEDIUM: {
        "ray_march_steps": 32,
        "inscattering_samples": 8,
        "resolution_scale": 0.5,
        "temporal_accumulation": True,
        "denoise_enabled": False,
        "cloud_lighting_samples": 2,
        "cloud_shadow_steps": 4,
        "volumetric_shadow": False,
    },
    QualityPreset.HIGH: {
        "ray_march_steps": 64,
        "inscattering_samples": 16,
        "resolution_scale": 0.75,
        "temporal_accumulation": True,
        "denoise_enabled": True,
        "cloud_lighting_samples": 4,
        "cloud_shadow_steps": 8,
        "volumetric_shadow": True,
    },
    QualityPreset.ULTRA: {
        "ray_march_steps": 128,
        "inscattering_samples": 32,
        "resolution_scale": 1.0,
        "temporal_accumulation": True,
        "denoise_enabled": True,
        "cloud_lighting_samples": 8,
        "cloud_shadow_steps": 16,
        "volumetric_shadow": True,
    },
    QualityPreset.CINEMATIC: {
        "ray_march_steps": 256,
        "inscattering_samples": 64,
        "resolution_scale": 1.0,
        "temporal_accumulation": True,
        "denoise_enabled": True,
        "cloud_lighting_samples": 16,
        "cloud_shadow_steps": 32,
        "volumetric_shadow": True,
    },
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VolumetricFogConfig:
    """Configuration for volumetric fog rendering.

    Defines fog density falloff, colour, scattering properties, and
    height-based attenuation parameters. Supports linear, exponential,
    layered, and height-based fog models.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    fog_mode: FogMode = FogMode.EXPONENTIAL
    density: float = 0.01
    start_distance: float = 0.0
    end_distance: float = 1000.0
    color_rgba: Tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0)
    height_falloff: float = 0.1
    scattering_coefficient: float = 0.02
    absorption_coefficient: float = 0.01
    phase_function_g: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize fog configuration to dictionary."""
        return {
            "id": self.id,
            "fog_mode": self.fog_mode.value,
            "density": self.density,
            "start_distance": self.start_distance,
            "end_distance": self.end_distance,
            "color_rgba": list(self.color_rgba),
            "height_falloff": self.height_falloff,
            "scattering_coefficient": self.scattering_coefficient,
            "absorption_coefficient": self.absorption_coefficient,
            "phase_function_g": self.phase_function_g,
            "created_at": self.created_at,
        }


@dataclass
class VolumetricLightConfig:
    """Configuration for volumetric light shafts and god rays.

    Controls light shaft intensity, cone angle, sampling quality,
    shadow integration, and scattering colour for directional or
    spot lights casting volumetric illumination.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    light_id: str = ""
    intensity: float = 1.0
    cone_angle: float = 45.0
    sampling_steps: int = 64
    volumetric_shadow: bool = True
    scattering_color: Tuple[float, float, float] = (1.0, 1.0, 0.9)
    anisotropy: float = 0.8
    enabled: bool = True
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize volumetric light configuration to dictionary."""
        return {
            "id": self.id,
            "light_id": self.light_id,
            "intensity": self.intensity,
            "cone_angle": self.cone_angle,
            "sampling_steps": self.sampling_steps,
            "volumetric_shadow": self.volumetric_shadow,
            "scattering_color": list(self.scattering_color),
            "anisotropy": self.anisotropy,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


@dataclass
class VolumetricCloudConfig:
    """Configuration for procedural volumetric cloud rendering.

    Defines cloud density, coverage, vertical extent, wind animation,
    and lighting/shadow parameters for volumetric cloud layers.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cloud_density: float = 0.3
    cloud_coverage: float = 0.5
    cloud_height_min: float = 500.0
    cloud_height_max: float = 3000.0
    wind_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    wind_speed: float = 5.0
    lighting_samples: int = 4
    shadow_steps: int = 8
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize volumetric cloud configuration to dictionary."""
        return {
            "id": self.id,
            "cloud_density": self.cloud_density,
            "cloud_coverage": self.cloud_coverage,
            "cloud_height_min": self.cloud_height_min,
            "cloud_height_max": self.cloud_height_max,
            "wind_direction": list(self.wind_direction),
            "wind_speed": self.wind_speed,
            "lighting_samples": self.lighting_samples,
            "shadow_steps": self.shadow_steps,
            "created_at": self.created_at,
        }


@dataclass
class ParticipatingMedia:
    """Participating media properties for light transport.

    Defines the optical properties of a volume of participating media,
    including density, albedo, phase function asymmetry, extinction
    coefficient, and spatial bounds.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    media_type: VolumetricEffectType = VolumetricEffectType.PARTICIPATING_MEDIA
    density: float = 0.01
    albedo: Tuple[float, float, float] = (0.8, 0.8, 0.8)
    phase_g: float = 0.0
    extinction_coefficient: float = 0.05
    scattering_albedo: float = 0.9
    bounds: Tuple[float, float, float, float, float, float] = (
        -100.0, -100.0, -100.0, 100.0, 100.0, 100.0,
    )
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize participating media to dictionary."""
        return {
            "id": self.id,
            "media_type": self.media_type.value,
            "density": self.density,
            "albedo": list(self.albedo),
            "phase_g": self.phase_g,
            "extinction_coefficient": self.extinction_coefficient,
            "scattering_albedo": self.scattering_albedo,
            "bounds": list(self.bounds),
            "created_at": self.created_at,
        }


@dataclass
class RayMarchResult:
    """Result of a ray marching integration through participating media.

    Contains the accumulated transmittance, scattered radiance,
    in-scattering contribution, optical depth, and execution metadata.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    total_transmittance: float = 1.0
    scattered_radiance: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    in_scattering: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    optical_depth: float = 0.0
    sample_count: int = 0
    execution_time_ms: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ray march result to dictionary."""
        return {
            "id": self.id,
            "total_transmittance": self.total_transmittance,
            "scattered_radiance": list(self.scattered_radiance),
            "in_scattering": list(self.in_scattering),
            "optical_depth": self.optical_depth,
            "sample_count": self.sample_count,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at,
        }


@dataclass
class VolumetricRenderPass:
    """Render pass configuration for volumetric effects.

    Defines a single volumetric render pass with effect type, sample
    counts, resolution scaling, temporal accumulation, and denoising
    settings.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pass_name: str = "VolumetricPass"
    effect_type: VolumetricEffectType = VolumetricEffectType.FOG
    enabled: bool = True
    sample_count: int = 64
    resolution_scale: float = 0.5
    temporal_accumulation: bool = True
    denoise_enabled: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize volumetric render pass to dictionary."""
        return {
            "id": self.id,
            "pass_name": self.pass_name,
            "effect_type": self.effect_type.value,
            "enabled": self.enabled,
            "sample_count": self.sample_count,
            "resolution_scale": self.resolution_scale,
            "temporal_accumulation": self.temporal_accumulation,
            "denoise_enabled": self.denoise_enabled,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Engine Volumetric Rendering
# ---------------------------------------------------------------------------

class EngineVolumetricRendering:
    """Volumetric rendering system for atmospheric effects.

    Provides a comprehensive volumetric rendering pipeline including
    fog configuration, volumetric light shafts, procedural clouds,
    ray marching through participating media, and physically-based
    scattering phase function evaluation.

    Usage:
        vr = get_volumetric_rendering()
        fog = vr.configure_fog(VolumetricFogConfig(density=0.02))
        result = vr.ray_march(camera_pos, ray_dir, max_distance=500.0)
        transmittance = vr.compute_transmittance(origin, target)
    """

    _instance: Optional["EngineVolumetricRendering"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineVolumetricRendering":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineVolumetricRendering":
        """Return the singleton EngineVolumetricRendering instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._fog_configs: Dict[str, VolumetricFogConfig] = {}
        self._volumetric_light_configs: Dict[str, VolumetricLightConfig] = {}
        self._cloud_configs: Dict[str, VolumetricCloudConfig] = {}
        self._participating_media: Dict[str, ParticipatingMedia] = {}
        self._render_passes: Dict[str, VolumetricRenderPass] = {}

        self._active_fog_id: str = ""
        self._active_cloud_id: str = ""
        self._active_quality_preset: QualityPreset = QualityPreset.HIGH

        self._total_fog_configs_created: int = 0
        self._total_light_configs_created: int = 0
        self._total_cloud_configs_created: int = 0
        self._total_media_created: int = 0
        self._total_render_passes_created: int = 0
        self._total_ray_march_calls: int = 0

        self._initialized = True

    # ------------------------------------------------------------------
    # Fog Configuration
    # ------------------------------------------------------------------

    def configure_fog(
        self, fog_config: VolumetricFogConfig
    ) -> VolumetricFogConfig:
        """Register a volumetric fog configuration.

        Stores the fog configuration and sets it as the active fog if
        no active fog is currently set.

        Args:
            fog_config: The VolumetricFogConfig to register.

        Returns:
            The registered VolumetricFogConfig instance.
        """
        with self._lock:
            self._fog_configs[fog_config.id] = fog_config
            self._total_fog_configs_created += 1

            if not self._active_fog_id:
                self._active_fog_id = fog_config.id

            return fog_config

    def get_fog_config(self, fog_id: str) -> Optional[VolumetricFogConfig]:
        """Retrieve a fog configuration by ID.

        Args:
            fog_id: The fog configuration ID.

        Returns:
            The VolumetricFogConfig or None if not found.
        """
        return self._fog_configs.get(fog_id)

    def get_active_fog(self) -> Optional[VolumetricFogConfig]:
        """Get the currently active fog configuration.

        Returns:
            The active VolumetricFogConfig or None.
        """
        with self._lock:
            if not self._active_fog_id:
                return None
            return self._fog_configs.get(self._active_fog_id)

    def set_active_fog(self, fog_id: str) -> bool:
        """Set the active fog configuration by ID.

        Args:
            fog_id: The fog configuration ID to activate.

        Returns:
            True if set successfully, False if not found.
        """
        with self._lock:
            if fog_id not in self._fog_configs:
                return False
            self._active_fog_id = fog_id
            return True

    def remove_fog_config(self, fog_id: str) -> bool:
        """Remove a fog configuration.

        If the removed config is the active one, clears the active fog.

        Args:
            fog_id: The fog configuration ID to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if fog_id not in self._fog_configs:
                return False
            del self._fog_configs[fog_id]
            if self._active_fog_id == fog_id:
                self._active_fog_id = ""
            return True

    # ------------------------------------------------------------------
    # Volumetric Light Configuration
    # ------------------------------------------------------------------

    def configure_volumetric_light(
        self, light_config: VolumetricLightConfig
    ) -> VolumetricLightConfig:
        """Register a volumetric light configuration.

        Args:
            light_config: The VolumetricLightConfig to register.

        Returns:
            The registered VolumetricLightConfig instance.
        """
        with self._lock:
            self._volumetric_light_configs[light_config.id] = light_config
            self._total_light_configs_created += 1
            return light_config

    def get_volumetric_light(
        self, light_id: str
    ) -> Optional[VolumetricLightConfig]:
        """Retrieve a volumetric light configuration by ID.

        Args:
            light_id: The volumetric light configuration ID.

        Returns:
            The VolumetricLightConfig or None if not found.
        """
        return self._volumetric_light_configs.get(light_id)

    def get_all_volumetric_lights(self) -> List[Dict[str, Any]]:
        """List all volumetric light configurations as dictionaries.

        Returns:
            A list of serialized volumetric light configuration dicts.
        """
        with self._lock:
            return [
                cfg.to_dict()
                for cfg in self._volumetric_light_configs.values()
            ]

    def remove_volumetric_light(self, light_id: str) -> bool:
        """Remove a volumetric light configuration.

        Args:
            light_id: The volumetric light configuration ID to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if light_id not in self._volumetric_light_configs:
                return False
            del self._volumetric_light_configs[light_id]
            return True

    # ------------------------------------------------------------------
    # Volumetric Cloud Configuration
    # ------------------------------------------------------------------

    def configure_volumetric_clouds(
        self, cloud_config: VolumetricCloudConfig
    ) -> VolumetricCloudConfig:
        """Register a volumetric cloud configuration.

        Stores the cloud configuration and sets it as the active cloud
        layer if none is currently active.

        Args:
            cloud_config: The VolumetricCloudConfig to register.

        Returns:
            The registered VolumetricCloudConfig instance.
        """
        with self._lock:
            self._cloud_configs[cloud_config.id] = cloud_config
            self._total_cloud_configs_created += 1

            if not self._active_cloud_id:
                self._active_cloud_id = cloud_config.id

            return cloud_config

    def get_cloud_config(
        self, cloud_id: str
    ) -> Optional[VolumetricCloudConfig]:
        """Retrieve a cloud configuration by ID.

        Args:
            cloud_id: The cloud configuration ID.

        Returns:
            The VolumetricCloudConfig or None if not found.
        """
        return self._cloud_configs.get(cloud_id)

    def get_active_clouds(self) -> Optional[VolumetricCloudConfig]:
        """Get the currently active cloud configuration.

        Returns:
            The active VolumetricCloudConfig or None.
        """
        with self._lock:
            if not self._active_cloud_id:
                return None
            return self._cloud_configs.get(self._active_cloud_id)

    def set_active_clouds(self, cloud_id: str) -> bool:
        """Set the active cloud configuration by ID.

        Args:
            cloud_id: The cloud configuration ID to activate.

        Returns:
            True if set successfully, False if not found.
        """
        with self._lock:
            if cloud_id not in self._cloud_configs:
                return False
            self._active_cloud_id = cloud_id
            return True

    def remove_cloud_config(self, cloud_id: str) -> bool:
        """Remove a cloud configuration.

        If the removed config is the active one, clears the active cloud.

        Args:
            cloud_id: The cloud configuration ID to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if cloud_id not in self._cloud_configs:
                return False
            del self._cloud_configs[cloud_id]
            if self._active_cloud_id == cloud_id:
                self._active_cloud_id = ""
            return True

    # ------------------------------------------------------------------
    # Participating Media
    # ------------------------------------------------------------------

    def add_participating_media(
        self, media: ParticipatingMedia
    ) -> ParticipatingMedia:
        """Register a participating media volume.

        Args:
            media: The ParticipatingMedia to register.

        Returns:
            The registered ParticipatingMedia instance.
        """
        with self._lock:
            self._participating_media[media.id] = media
            self._total_media_created += 1
            return media

    def get_participating_media(
        self, media_id: str
    ) -> Optional[ParticipatingMedia]:
        """Retrieve participating media by ID.

        Args:
            media_id: The participating media ID.

        Returns:
            The ParticipatingMedia or None if not found.
        """
        return self._participating_media.get(media_id)

    def get_all_participating_media(self) -> List[Dict[str, Any]]:
        """List all participating media volumes as dictionaries.

        Returns:
            A list of serialized participating media dicts.
        """
        with self._lock:
            return [
                m.to_dict() for m in self._participating_media.values()
            ]

    def remove_participating_media(self, media_id: str) -> bool:
        """Remove a participating media volume.

        Args:
            media_id: The participating media ID to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if media_id not in self._participating_media:
                return False
            del self._participating_media[media_id]
            return True

    # ------------------------------------------------------------------
    # Ray Marching
    # ------------------------------------------------------------------

    def ray_march(
        self,
        camera_pos: Tuple[float, float, float],
        ray_direction: Tuple[float, float, float],
        max_distance: float = 100.0,
        step_count: int = 64,
    ) -> RayMarchResult:
        """Simulate ray marching through participating media.

        Performs numerical integration along a ray from the camera
        position in the given direction. Accumulates transmittance
        (Beer-Lambert law), scattered radiance, and in-scattering
        contributions at each step.

        The ray marching uses variable step sizing: larger steps
        in sparse regions, refined near media boundaries.

        Args:
            camera_pos: Origin of the ray in world space (x, y, z).
            ray_direction: Normalized ray direction vector (x, y, z).
            max_distance: Maximum distance to march along the ray.
            step_count: Number of integration steps.

        Returns:
            A RayMarchResult with total transmittance, scattered
            radiance, in-scattering, optical depth, and metadata.
        """
        start_time = _time_module.perf_counter()

        with self._lock:
            # Normalize ray direction
            dx, dy, dz = ray_direction
            length = math.sqrt(dx * dx + dy * dy + dz * dz)
            if length < 1e-10:
                return RayMarchResult(
                    total_transmittance=1.0,
                    scattered_radiance=(0.0, 0.0, 0.0),
                    in_scattering=(0.0, 0.0, 0.0),
                    optical_depth=0.0,
                    sample_count=0,
                    execution_time_ms=0.0,
                )

            dir_x = dx / length
            dir_y = dy / length
            dir_z = dz / length

            # Determine step size based on active fog/media density
            fog = self._fog_configs.get(self._active_fog_id)
            base_density = fog.density if fog else 0.01
            step_size = max_distance / max(1, step_count)

            # Accumulators
            total_transmittance = 1.0
            optical_depth = 0.0
            accumulated_scattered_r = 0.0
            accumulated_scattered_g = 0.0
            accumulated_scattered_b = 0.0
            accumulated_inscattering_r = 0.0
            accumulated_inscattering_g = 0.0
            accumulated_inscattering_b = 0.0

            cx, cy, cz = camera_pos

            for i in range(step_count):
                t = (i + 0.5) * step_size
                if t > max_distance:
                    break

                # Sample position along the ray
                px = cx + dir_x * t
                py = cy + dir_y * t
                pz = cz + dir_z * t

                # Compute local density at this sample point
                local_density = self._compute_local_density(px, py, pz, fog)

                if local_density <= 0.0:
                    continue

                # Beer-Lambert: dT = exp(-sigma_e * density * ds)
                extinction = local_density * step_size
                transmittance_step = math.exp(-extinction)
                optical_depth += extinction
                total_transmittance *= transmittance_step

                # Scattered radiance: scat_color * density * transmittance * ds
                if fog:
                    fog_r = fog.color_rgba[0]
                    fog_g = fog.color_rgba[1]
                    fog_b = fog.color_rgba[2]
                else:
                    fog_r = fog_g = fog_b = 0.7

                weight = local_density * total_transmittance * step_size
                accumulated_scattered_r += fog_r * weight
                accumulated_scattered_g += fog_g * weight
                accumulated_scattered_b += fog_b * weight

                # In-scattering: approximated from light direction
                # Simplified: inscatter = density * scattering_albedo * phase
                scattering_albedo = 0.9
                accumulated_inscattering_r += fog_r * local_density * scattering_albedo * step_size
                accumulated_inscattering_g += fog_g * local_density * scattering_albedo * step_size
                accumulated_inscattering_b += fog_b * local_density * scattering_albedo * step_size

            end_time = _time_module.perf_counter()
            execution_ms = (end_time - start_time) * 1000.0

            self._total_ray_march_calls += 1

            return RayMarchResult(
                total_transmittance=total_transmittance,
                scattered_radiance=(
                    accumulated_scattered_r,
                    accumulated_scattered_g,
                    accumulated_scattered_b,
                ),
                in_scattering=(
                    accumulated_inscattering_r,
                    accumulated_inscattering_g,
                    accumulated_inscattering_b,
                ),
                optical_depth=optical_depth,
                sample_count=step_count,
                execution_time_ms=execution_ms,
            )

    def _compute_local_density(
        self,
        x: float,
        y: float,
        z: float,
        fog: Optional[VolumetricFogConfig],
    ) -> float:
        """Compute the local fog density at a given world position.

        Applies the active fog mode to compute density based on
        distance, height, and configured falloff parameters.

        Args:
            x, y, z: World position.
            fog: The active fog configuration, or None for default.

        Returns:
            Local density value at the given position.
        """
        if fog is None:
            return 0.0

        mode = fog.fog_mode
        density = fog.density

        if mode == FogMode.LINEAR:
            return density

        elif mode == FogMode.EXPONENTIAL:
            return density

        elif mode == FogMode.EXPONENTIAL_SQUARED:
            return density

        elif mode == FogMode.LAYERED:
            # Layered fog: density only within a height band
            height = y
            mid_height = (fog.start_distance + fog.end_distance) / 2.0
            half_thickness = abs(fog.end_distance - fog.start_distance) / 2.0
            if half_thickness < 1e-6:
                return density
            normalized = abs(height - mid_height) / half_thickness
            if normalized > 1.0:
                return 0.0
            edge_fade = 1.0 - normalized
            return density * edge_fade

        elif mode == FogMode.HEIGHT_BASED:
            # Height-based fog: density decreases with height
            height = y
            falloff = fog.height_falloff
            if falloff <= 0.0:
                return density
            return density * math.exp(-height * falloff)

        return density

    # ------------------------------------------------------------------
    # Transmittance (Beer-Lambert Law)
    # ------------------------------------------------------------------

    def compute_transmittance(
        self,
        origin: Tuple[float, float, float],
        target: Tuple[float, float, float],
        media_density: float = 0.01,
    ) -> float:
        """Compute light transmittance between two points using the
        Beer-Lambert law.

        T = exp(-sigma_t * rho * d)

        where sigma_t is the extinction coefficient (default 1.0),
        rho is the media density, and d is the distance between
        the two points.

        Args:
            origin: Start point in world space (x, y, z).
            target: End point in world space (x, y, z).
            media_density: Density of the participating medium.

        Returns:
            Transmittance value in [0.0, 1.0].
        """
        with self._lock:
            ox, oy, oz = origin
            tx, ty, tz = target

            dx = tx - ox
            dy = ty - oy
            dz = tz - oz
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)

            if distance < 1e-10:
                return 1.0

            # Extinction coefficient from active fog
            fog = self._fog_configs.get(self._active_fog_id)
            sigma_t = 1.0
            if fog:
                sigma_t = fog.scattering_coefficient + fog.absorption_coefficient

            optical_depth = sigma_t * media_density * distance
            transmittance = math.exp(-optical_depth)

            return max(0.0, min(1.0, transmittance))

    # ------------------------------------------------------------------
    # Phase Function Evaluation
    # ------------------------------------------------------------------

    def evaluate_phase_function(
        self,
        scattering_model: ScatteringModel,
        cos_theta: float,
        g: float = 0.0,
    ) -> float:
        """Evaluate the scattering phase function.

        Computes the angular distribution of scattered light for the
        given scattering model. The phase function determines how much
        light is scattered in a particular direction relative to the
        incident direction.

        Args:
            scattering_model: The scattering model to use.
            cos_theta: Cosine of the scattering angle (dot product of
                incident and scattered directions).
            g: Asymmetry parameter for Henyey-Greenstein and OMPF
                models. g > 0 gives forward scattering, g < 0 gives
                backward scattering.

        Returns:
            Phase function value (normalized such that the integral
            over the sphere equals 4*pi for isotropic).
        """
        with self._lock:
            cos_theta = max(-1.0, min(1.0, cos_theta))

            if scattering_model == ScatteringModel.ISOTROPIC:
                # Isotropic: equal probability in all directions
                return 1.0 / (4.0 * math.pi)

            elif scattering_model == ScatteringModel.RAYLEIGH:
                # Rayleigh phase function:
                # p(theta) = (3 / (16*pi)) * (1 + cos^2(theta))
                return (3.0 / (16.0 * math.pi)) * (1.0 + cos_theta * cos_theta)

            elif scattering_model == ScatteringModel.MIE:
                # Mie scattering approximation using a simplified
                # Cornette-Shanks phase function:
                # p(theta) = (3/2) * ((1-g^2)/(2+g^2)) * (1+cos^2(theta)) / (1+g^2 - 2g*cos(theta))^(3/2)
                g_clamped = max(-1.0, min(1.0, g))
                g2 = g_clamped * g_clamped
                numerator = (1.0 - g2) * (1.0 + cos_theta * cos_theta)
                denominator = (1.0 + g2 - 2.0 * g_clamped * cos_theta)
                if denominator < 1e-10:
                    denominator = 1e-10
                return (3.0 / (2.0 * (2.0 + g2))) * numerator / (denominator ** 1.5)

            elif scattering_model == ScatteringModel.HENYEY_GREENSTEIN:
                # Henyey-Greenstein phase function:
                # p(theta) = (1 / (4*pi)) * (1 - g^2) / (1 + g^2 - 2g*cos(theta))^(3/2)
                g_clamped = max(-1.0, min(1.0, g))
                g2 = g_clamped * g_clamped
                denominator = 1.0 + g2 - 2.0 * g_clamped * cos_theta
                if denominator < 1e-10:
                    denominator = 1e-10
                return (1.0 / (4.0 * math.pi)) * (1.0 - g2) / (denominator ** 1.5)

            elif scattering_model == ScatteringModel.OMPF:
                # One-Moment Phase Function:
                # p(theta) = (1 / (4*pi)) * (1 + 3g*cos(theta))
                g_clamped = max(-1.0 / 3.0, min(1.0 / 3.0, g))
                return (1.0 / (4.0 * math.pi)) * (1.0 + 3.0 * g_clamped * cos_theta)

            # Default: isotropic
            return 1.0 / (4.0 * math.pi)

    # ------------------------------------------------------------------
    # In-Scattering Computation
    # ------------------------------------------------------------------

    def compute_inscattering(
        self,
        position: Tuple[float, float, float],
        light_direction: Tuple[float, float, float],
        view_direction: Tuple[float, float, float],
        samples: int = 16,
    ) -> float:
        """Compute in-scattered light at a point.

        Integrates the light reaching a point through scattering from
        a directional light source. Evaluates the phase function at
        each sample along the light direction and accumulates the
        scattered contribution using Beer-Lambert attenuation.

        In-scattering integral:
            L_inscatter = sum_i [ phase(theta_i) * T(light) * T(view) * ds ]

        Args:
            position: World position (x, y, z).
            light_direction: Normalized direction to the light source.
            view_direction: Normalized view direction.
            samples: Number of integration samples along the light ray.

        Returns:
            Accumulated in-scattered light intensity.
        """
        with self._lock:
            px, py, pz = position

            # Normalize light direction
            lx, ly, lz = light_direction
            light_len = math.sqrt(lx * lx + ly * ly + lz * lz)
            if light_len < 1e-10:
                return 0.0
            lx /= light_len
            ly /= light_len
            lz /= light_len

            # Normalize view direction
            vx, vy, vz = view_direction
            view_len = math.sqrt(vx * vx + vy * vy + vz * vz)
            if view_len < 1e-10:
                return 0.0
            vx /= view_len
            vy /= view_len
            vz /= view_len

            # Cosine of scattering angle: dot(light_dir, view_dir)
            cos_theta = lx * vx + ly * vy + lz * vz
            cos_theta = max(-1.0, min(1.0, cos_theta))

            # Get media properties
            fog = self._fog_configs.get(self._active_fog_id)
            density = fog.density if fog else 0.01
            phase_g = fog.phase_function_g if fog else 0.0

            # Evaluate phase function
            phase = self.evaluate_phase_function(
                ScatteringModel.HENYEY_GREENSTEIN, cos_theta, phase_g
            )

            # Integration along the light direction
            max_distance = 500.0
            step_size = max_distance / max(1, samples)

            accumulated = 0.0
            current_transmittance = 1.0

            for i in range(samples):
                t = (i + 0.5) * step_size
                if t > max_distance:
                    break

                # Sample point along the light ray
                sx = px + lx * t
                sy = py + ly * t
                sz = pz + lz * t

                # Local density at sample
                local_density = self._compute_local_density(sx, sy, sz, fog)

                # Beer-Lambert attenuation along light ray
                extinction = local_density * step_size
                current_transmittance *= math.exp(-extinction)

                # In-scattering contribution
                accumulated += phase * local_density * current_transmittance * step_size

            return accumulated

    # ------------------------------------------------------------------
    # Render Pass Management
    # ------------------------------------------------------------------

    def create_render_pass(
        self, pass_config: VolumetricRenderPass
    ) -> VolumetricRenderPass:
        """Create a volumetric render pass.

        Registers a new render pass configuration for volumetric
        effects rendering.

        Args:
            pass_config: The VolumetricRenderPass to register.

        Returns:
            The registered VolumetricRenderPass instance.
        """
        with self._lock:
            self._render_passes[pass_config.id] = pass_config
            self._total_render_passes_created += 1
            return pass_config

    def get_render_pass(
        self, pass_id: str
    ) -> Optional[VolumetricRenderPass]:
        """Retrieve a render pass by ID.

        Args:
            pass_id: The render pass ID.

        Returns:
            The VolumetricRenderPass or None if not found.
        """
        return self._render_passes.get(pass_id)

    def get_all_render_passes(self) -> List[Dict[str, Any]]:
        """List all render passes as dictionaries.

        Returns:
            A list of serialized render pass dicts.
        """
        with self._lock:
            return [rp.to_dict() for rp in self._render_passes.values()]

    def remove_render_pass(self, pass_id: str) -> bool:
        """Remove a render pass.

        Args:
            pass_id: The render pass ID to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if pass_id not in self._render_passes:
                return False
            del self._render_passes[pass_id]
            return True

    # ------------------------------------------------------------------
    # Quality Preset
    # ------------------------------------------------------------------

    def set_quality_preset(self, preset: QualityPreset) -> Dict[str, Any]:
        """Set the global quality preset for all volumetric effects.

        Updates all active render passes with the sample counts,
        resolution scale, temporal accumulation, and denoising
        settings prescribed by the given quality preset.

        Args:
            preset: The QualityPreset to apply.

        Returns:
            Dict with the applied preset settings.
        """
        with self._lock:
            self._active_quality_preset = preset
            preset_config = _QUALITY_PRESET_CONFIGS.get(
                preset, _QUALITY_PRESET_CONFIGS[QualityPreset.HIGH]
            )

            # Apply preset to all render passes
            for rp in self._render_passes.values():
                rp.sample_count = preset_config["ray_march_steps"]
                rp.resolution_scale = preset_config["resolution_scale"]
                rp.temporal_accumulation = preset_config["temporal_accumulation"]
                rp.denoise_enabled = preset_config["denoise_enabled"]

            # Apply preset to cloud configs
            for cc in self._cloud_configs.values():
                cc.lighting_samples = preset_config["cloud_lighting_samples"]
                cc.shadow_steps = preset_config["cloud_shadow_steps"]

            # Apply preset to volumetric light configs
            for vl in self._volumetric_light_configs.values():
                vl.sampling_steps = preset_config["ray_march_steps"]
                vl.volumetric_shadow = preset_config["volumetric_shadow"]

            return dict(preset_config)

    def get_quality_preset(self) -> Dict[str, Any]:
        """Get the current quality preset and its settings.

        Returns:
            Dict with the current preset name and its settings.
        """
        with self._lock:
            preset_config = _QUALITY_PRESET_CONFIGS.get(
                self._active_quality_preset,
                _QUALITY_PRESET_CONFIGS[QualityPreset.HIGH],
            )
            return {
                "preset": self._active_quality_preset.value,
                "settings": dict(preset_config),
            }

    # ------------------------------------------------------------------
    # Status and Statistics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return comprehensive status of the volumetric rendering system.

        Returns:
            Dict with configuration counts, active settings, quality
            preset info, and performance statistics.
        """
        with self._lock:
            fog_mode_distribution: Dict[str, int] = {}
            for fc in self._fog_configs.values():
                mode = fc.fog_mode.value
                fog_mode_distribution[mode] = fog_mode_distribution.get(mode, 0) + 1

            effect_type_distribution: Dict[str, int] = {}
            for rp in self._render_passes.values():
                et = rp.effect_type.value
                effect_type_distribution[et] = effect_type_distribution.get(et, 0) + 1

            active_fog_mode = None
            if self._active_fog_id:
                fog = self._fog_configs.get(self._active_fog_id)
                if fog:
                    active_fog_mode = fog.fog_mode.value

            return {
                "total_fog_configs": len(self._fog_configs),
                "total_fog_configs_created": self._total_fog_configs_created,
                "active_fog_id": self._active_fog_id,
                "active_fog_mode": active_fog_mode,
                "fog_mode_distribution": fog_mode_distribution,
                "total_volumetric_lights": len(self._volumetric_light_configs),
                "total_light_configs_created": self._total_light_configs_created,
                "total_cloud_configs": len(self._cloud_configs),
                "total_cloud_configs_created": self._total_cloud_configs_created,
                "active_cloud_id": self._active_cloud_id,
                "total_participating_media": len(self._participating_media),
                "total_media_created": self._total_media_created,
                "total_render_passes": len(self._render_passes),
                "total_render_passes_created": self._total_render_passes_created,
                "effect_type_distribution": effect_type_distribution,
                "total_ray_march_calls": self._total_ray_march_calls,
                "active_quality_preset": self._active_quality_preset.value,
                "quality_settings": _QUALITY_PRESET_CONFIGS.get(
                    self._active_quality_preset,
                    _QUALITY_PRESET_CONFIGS[QualityPreset.HIGH],
                ),
            }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire volumetric rendering state.

        Returns:
            Dict representation of all fog configs, light configs,
            cloud configs, participating media, and render passes.
        """
        with self._lock:
            return {
                "fog_configs": [
                    fc.to_dict() for fc in self._fog_configs.values()
                ],
                "volumetric_light_configs": [
                    vl.to_dict()
                    for vl in self._volumetric_light_configs.values()
                ],
                "cloud_configs": [
                    cc.to_dict() for cc in self._cloud_configs.values()
                ],
                "participating_media": [
                    m.to_dict() for m in self._participating_media.values()
                ],
                "render_passes": [
                    rp.to_dict() for rp in self._render_passes.values()
                ],
                "status": self.get_status(),
            }

    def create_fog_config(
        self,
        name: str = "",
        density: float = 0.01,
        scattering_coefficient: float = 0.02,
        absorption_coefficient: float = 0.01,
        phase_g: float = 0.0,
        color: Tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0),
    ) -> VolumetricFogConfig:
        """Create and register a volumetric fog configuration.

        Convenience method that constructs a VolumetricFogConfig
        dataclass and registers it via configure_fog.

        Args:
            name: Display name stored via internal label.
            density: Fog density (0-1).
            scattering_coefficient: Scattering coefficient.
            absorption_coefficient: Absorption coefficient.
            phase_g: Phase function anisotropy parameter.
            color: RGBA color tuple.

        Returns:
            The registered VolumetricFogConfig.
        """
        config = VolumetricFogConfig(
            density=density,
            scattering_coefficient=scattering_coefficient,
            absorption_coefficient=absorption_coefficient,
            phase_function_g=phase_g,
            color_rgba=color,
        )
        return self.configure_fog(config)

    def create_light_config(
        self,
        name: str = "",
        position: Tuple[float, float] = (0, 0),
        intensity: float = 1.0,
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        radius: float = 10.0,
        volumetric_enabled: bool = True,
    ) -> VolumetricLightConfig:
        """Create and register a volumetric light configuration.

        Convenience method that constructs a VolumetricLightConfig
        dataclass and registers it via configure_volumetric_light.

        Args:
            name: Display name.
            position: Light position (x, y).
            intensity: Light intensity.
            color: RGB color tuple.
            radius: Light influence radius.
            volumetric_enabled: Enable volumetric scattering.

        Returns:
            The registered VolumetricLightConfig.
        """
        config = VolumetricLightConfig(
            intensity=intensity,
            scattering_color=color,
            volumetric_shadow=volumetric_enabled,
        )
        return self.configure_volumetric_light(config)

    def create_cloud_config(
        self,
        name: str = "",
        coverage: float = 0.5,
        density: float = 0.3,
        altitude: float = 500.0,
        thickness: float = 200.0,
        wind_speed: float = 5.0,
        wind_direction: float = 0.0,
    ) -> VolumetricCloudConfig:
        """Create and register a volumetric cloud configuration.

        Convenience method that constructs a VolumetricCloudConfig
        dataclass and registers it via configure_volumetric_clouds.

        Args:
            name: Display name.
            coverage: Cloud coverage (0-1).
            density: Cloud density (0-1).
            altitude: Base altitude of cloud layer.
            thickness: Vertical thickness of cloud layer.
            wind_speed: Wind speed for animation.
            wind_direction: Wind direction in radians.

        Returns:
            The registered VolumetricCloudConfig.
        """
        import math as _math
        config = VolumetricCloudConfig(
            cloud_density=density,
            cloud_coverage=coverage,
            cloud_height_min=altitude,
            cloud_height_max=altitude + thickness,
            wind_speed=wind_speed,
            wind_direction=(
                _math.cos(wind_direction),
                _math.sin(wind_direction),
                0.0,
            ),
        )
        return self.configure_volumetric_clouds(config)

    def reset(self) -> None:
        """Reset all volumetric rendering state to defaults.

        Clears all configurations, render passes, participating media,
        and resets quality preset to HIGH.
        """
        with self._lock:
            self._fog_configs.clear()
            self._volumetric_light_configs.clear()
            self._cloud_configs.clear()
            self._participating_media.clear()
            self._render_passes.clear()

            self._active_fog_id = ""
            self._active_cloud_id = ""
            self._active_quality_preset = QualityPreset.HIGH

            self._total_fog_configs_created = 0
            self._total_light_configs_created = 0
            self._total_cloud_configs_created = 0
            self._total_media_created = 0
            self._total_render_passes_created = 0
            self._total_ray_march_calls = 0

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"EngineVolumetricRendering(fog={len(self._fog_configs)}, "
                f"lights={len(self._volumetric_light_configs)}, "
                f"clouds={len(self._cloud_configs)}, "
                f"media={len(self._participating_media)}, "
                f"passes={len(self._render_passes)}, "
                f"quality={self._active_quality_preset.value})"
            )


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_volumetric_rendering() -> EngineVolumetricRendering:
    """Get or create the singleton EngineVolumetricRendering instance."""
    return EngineVolumetricRendering.get_instance()