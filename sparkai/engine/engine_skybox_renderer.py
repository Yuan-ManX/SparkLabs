"""
SkyboxRenderer - Dynamic procedural skybox rendering with time-of-day gradients,
star fields, cloud layers, and atmospheric scattering for the SparkLabs game engine.

Manages skybox configurations with preset support, smooth colour interpolation
across the day-night cycle, procedural star field generation, multi-layer cloud
rendering, and Rayleigh/Mie atmospheric scattering simulation.
"""

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

_time_module = time


class SkyPreset(Enum):
    """Predefined skybox configurations for common atmospheric conditions."""

    CLEAR_DAY = "clear_day"
    SUNSET = "sunset"
    NIGHT = "night"
    STORMY = "stormy"
    ALIEN_WORLD = "alien_world"
    NEBULA = "nebula"
    TOXIC_WASTELAND = "toxic_wasteland"
    ARCTIC_TWILIGHT = "arctic_twilight"
    DESERT_MIRAGE = "desert_mirage"


class TimeOfDay(Enum):
    """Discrete time-of-day phases used for sky colour classification.

    Each phase maps to a normalised time range within the 24-hour cycle.
    """

    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"

    @property
    def normalised_range(self) -> Tuple[float, float]:
        """Returns the (start, end) range in normalised time [0.0, 1.0]."""
        return {
            TimeOfDay.DAWN: (0.18, 0.28),
            TimeOfDay.MORNING: (0.28, 0.42),
            TimeOfDay.NOON: (0.42, 0.58),
            TimeOfDay.AFTERNOON: (0.58, 0.72),
            TimeOfDay.DUSK: (0.72, 0.82),
            TimeOfDay.NIGHT: (0.82, 0.95),
            TimeOfDay.MIDNIGHT: (0.95, 1.01),
        }[self]

    @classmethod
    def from_normalised_time(cls, normalised: float) -> "TimeOfDay":
        """Determines the TimeOfDay phase from a normalised time value.

        Args:
            normalised: Time value in [0.0, 1.0] where 0.0 is midnight.

        Returns:
            The TimeOfDay phase for the given time.
        """
        wrapped = normalised % 1.0
        for phase in cls:
            start, end = phase.normalised_range
            if end > 1.0:
                if wrapped >= start or wrapped < (end - 1.0):
                    return phase
            elif start <= wrapped < end:
                return phase
        return TimeOfDay.NIGHT


class CloudLayer(Enum):
    """Cloud layer types for procedural skybox cloud rendering."""

    CIRRUS = "cirrus"
    CUMULUS = "cumulus"
    STRATUS = "stratus"
    NIMBUS = "nimbus"
    CUSTOM = "custom"

    @property
    def default_altitude(self) -> float:
        """Returns the default altitude fraction for this cloud type."""
        return {
            CloudLayer.CIRRUS: 0.85,
            CloudLayer.CUMULUS: 0.55,
            CloudLayer.STRATUS: 0.45,
            CloudLayer.NIMBUS: 0.35,
            CloudLayer.CUSTOM: 0.50,
        }[self]

    @property
    def default_opacity(self) -> float:
        """Returns the default opacity for this cloud type."""
        return {
            CloudLayer.CIRRUS: 0.15,
            CloudLayer.CUMULUS: 0.50,
            CloudLayer.STRATUS: 0.65,
            CloudLayer.NIMBUS: 0.80,
            CloudLayer.CUSTOM: 0.40,
        }[self]

    @property
    def default_coverage(self) -> float:
        """Returns the default coverage fraction for this cloud type."""
        return {
            CloudLayer.CIRRUS: 0.20,
            CloudLayer.CUMULUS: 0.35,
            CloudLayer.STRATUS: 0.55,
            CloudLayer.NIMBUS: 0.70,
            CloudLayer.CUSTOM: 0.40,
        }[self]


class StarDensity(Enum):
    """Star field density levels for night sky rendering."""

    NONE = "none"
    SPARSE = "sparse"
    NORMAL = "normal"
    DENSE = "dense"
    GALACTIC = "galactic"

    @property
    def star_count(self) -> int:
        """Returns the number of stars to generate for this density."""
        return {
            StarDensity.NONE: 0,
            StarDensity.SPARSE: 150,
            StarDensity.NORMAL: 500,
            StarDensity.DENSE: 1200,
            StarDensity.GALACTIC: 3000,
        }[self]


@dataclass
class SkyConfig:
    """Configuration for a skybox preset, defining colours and parameters.

    Stores the top, horizon, and bottom gradient colours for the sky dome,
    along with sun position, cloud coverage, star density, and atmospheric
    thickness settings. Each config has a unique auto-generated ID.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    preset: SkyPreset = SkyPreset.CLEAR_DAY
    top_color: Tuple[float, float, float] = (0.3, 0.6, 0.95)
    horizon_color: Tuple[float, float, float] = (0.7, 0.85, 1.0)
    bottom_color: Tuple[float, float, float] = (0.85, 0.85, 0.9)
    sun_azimuth: float = 0.0
    sun_elevation: float = 45.0
    cloud_coverage: float = 0.3
    star_density: StarDensity = StarDensity.NORMAL
    atmosphere_thickness: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> dict:
        """Serializes the sky configuration to a dictionary."""
        return {
            "id": self.id,
            "preset": self.preset.value,
            "top_color": list(self.top_color),
            "horizon_color": list(self.horizon_color),
            "bottom_color": list(self.bottom_color),
            "sun_azimuth": self.sun_azimuth,
            "sun_elevation": self.sun_elevation,
            "cloud_coverage": self.cloud_coverage,
            "star_density": self.star_density.value,
            "atmosphere_thickness": self.atmosphere_thickness,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"SkyConfig(id={self.id[:8]}..., preset={self.preset.value}, "
            f"sun_elev={self.sun_elevation:.1f})"
        )


@dataclass
class AtmosphereParams:
    """Physical parameters governing atmospheric light scattering.

    Uses a simplified Rayleigh/Mie scattering model. Rayleigh scattering
    produces the blue sky and red sunset hues, while Mie scattering
    contributes to haze and the whiter appearance near the horizon.
    """

    rayleigh_coefficient: Tuple[float, float, float] = (5.8e-6, 13.5e-6, 33.1e-6)
    mie_coefficient: float = 2.1e-5
    sun_intensity: float = 20.0
    scattering_samples: int = 16
    exposure: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> dict:
        """Serializes the atmosphere parameters to a dictionary."""
        return {
            "rayleigh_coefficient": list(self.rayleigh_coefficient),
            "mie_coefficient": self.mie_coefficient,
            "sun_intensity": self.sun_intensity,
            "scattering_samples": self.scattering_samples,
            "exposure": self.exposure,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"AtmosphereParams(rayleigh={self.rayleigh_coefficient}, "
            f"mie={self.mie_coefficient}, intensity={self.sun_intensity})"
        )


@dataclass
class SkyRenderState:
    """Snapshot of the current skybox rendering state for a single frame.

    Captures the active configuration, current interpolated colours,
    visible star positions, active cloud layers, and per-frame statistics.
    """

    config_id: str = ""
    current_time: float = 0.0
    interpolated_colors: Dict[str, Tuple[float, float, float]] = field(
        default_factory=dict
    )
    visible_stars: List[Dict] = field(default_factory=list)
    active_clouds: List[Dict] = field(default_factory=list)
    render_calls_this_frame: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> dict:
        """Serializes the sky render state to a dictionary."""
        return {
            "config_id": self.config_id,
            "current_time": self.current_time,
            "interpolated_colors": {
                key: list(val) for key, val in self.interpolated_colors.items()
            },
            "visible_stars": list(self.visible_stars),
            "active_clouds": list(self.active_clouds),
            "render_calls_this_frame": self.render_calls_this_frame,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"SkyRenderState(config={self.config_id[:8]}..., "
            f"time={self.current_time:.3f}, "
            f"stars={len(self.visible_stars)}, "
            f"clouds={len(self.active_clouds)})"
        )


class SkyboxRenderer:
    """Singleton system for dynamic procedural skybox rendering.

    Manages skybox configurations with time-of-day gradient interpolation,
    procedural star field generation for night skies, multi-layer cloud
    rendering, and simplified atmospheric scattering for realistic sky
    appearance.

    Thread-safe via a reentrant lock. Use get_skybox_renderer() or
    SkyboxRenderer.get_instance() to obtain the singleton instance.
    """

    _instance: Optional["SkyboxRenderer"] = None
    _lock: threading.RLock = threading.RLock()

    _PRESET_CONFIGS: Dict[SkyPreset, dict] = {
        SkyPreset.CLEAR_DAY: {
            "top_color": (0.25, 0.55, 0.90),
            "horizon_color": (0.65, 0.80, 0.95),
            "bottom_color": (0.90, 0.90, 0.88),
            "sun_azimuth": 180.0,
            "sun_elevation": 65.0,
            "cloud_coverage": 0.15,
            "star_density": StarDensity.NONE,
            "atmosphere_thickness": 1.0,
        },
        SkyPreset.SUNSET: {
            "top_color": (0.12, 0.08, 0.35),
            "horizon_color": (0.95, 0.45, 0.15),
            "bottom_color": (0.85, 0.50, 0.20),
            "sun_azimuth": 270.0,
            "sun_elevation": 5.0,
            "cloud_coverage": 0.30,
            "star_density": StarDensity.SPARSE,
            "atmosphere_thickness": 1.5,
        },
        SkyPreset.NIGHT: {
            "top_color": (0.02, 0.02, 0.08),
            "horizon_color": (0.04, 0.04, 0.12),
            "bottom_color": (0.01, 0.01, 0.04),
            "sun_azimuth": 0.0,
            "sun_elevation": -30.0,
            "cloud_coverage": 0.10,
            "star_density": StarDensity.DENSE,
            "atmosphere_thickness": 0.3,
        },
        SkyPreset.STORMY: {
            "top_color": (0.15, 0.15, 0.18),
            "horizon_color": (0.22, 0.22, 0.25),
            "bottom_color": (0.10, 0.10, 0.12),
            "sun_azimuth": 90.0,
            "sun_elevation": 10.0,
            "cloud_coverage": 0.85,
            "star_density": StarDensity.NONE,
            "atmosphere_thickness": 2.0,
        },
        SkyPreset.ALIEN_WORLD: {
            "top_color": (0.15, 0.05, 0.30),
            "horizon_color": (0.40, 0.15, 0.50),
            "bottom_color": (0.10, 0.02, 0.20),
            "sun_azimuth": 135.0,
            "sun_elevation": 35.0,
            "cloud_coverage": 0.40,
            "star_density": StarDensity.GALACTIC,
            "atmosphere_thickness": 1.3,
        },
        SkyPreset.NEBULA: {
            "top_color": (0.02, 0.01, 0.06),
            "horizon_color": (0.08, 0.03, 0.15),
            "bottom_color": (0.01, 0.00, 0.03),
            "sun_azimuth": 200.0,
            "sun_elevation": -15.0,
            "cloud_coverage": 0.05,
            "star_density": StarDensity.GALACTIC,
            "atmosphere_thickness": 0.2,
        },
        SkyPreset.TOXIC_WASTELAND: {
            "top_color": (0.10, 0.25, 0.05),
            "horizon_color": (0.35, 0.55, 0.10),
            "bottom_color": (0.15, 0.20, 0.05),
            "sun_azimuth": 160.0,
            "sun_elevation": 40.0,
            "cloud_coverage": 0.60,
            "star_density": StarDensity.NONE,
            "atmosphere_thickness": 2.5,
        },
        SkyPreset.ARCTIC_TWILIGHT: {
            "top_color": (0.05, 0.10, 0.30),
            "horizon_color": (0.30, 0.40, 0.60),
            "bottom_color": (0.80, 0.85, 0.90),
            "sun_azimuth": 300.0,
            "sun_elevation": -2.0,
            "cloud_coverage": 0.25,
            "star_density": StarDensity.NORMAL,
            "atmosphere_thickness": 0.8,
        },
        SkyPreset.DESERT_MIRAGE: {
            "top_color": (0.15, 0.25, 0.55),
            "horizon_color": (0.85, 0.65, 0.30),
            "bottom_color": (0.75, 0.55, 0.25),
            "sun_azimuth": 210.0,
            "sun_elevation": 55.0,
            "cloud_coverage": 0.05,
            "star_density": StarDensity.NONE,
            "atmosphere_thickness": 1.2,
        },
    }

    def __new__(cls) -> "SkyboxRenderer":
        """Thread-safe singleton construction with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initializes internal state on first construction only."""
        if getattr(self, "_initialized", False):
            return
        self._sky_configs: Dict[str, SkyConfig] = {}
        self._active_config_id: str = ""
        self._time_progression: float = 0.42
        self._atmosphere_params: AtmosphereParams = AtmosphereParams()
        self._stats: Dict[str, int] = {
            "total_configs_created": 0,
            "total_transitions": 0,
            "total_frames_rendered": 0,
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "SkyboxRenderer":
        """Returns the singleton SkyboxRenderer instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lerp_color(
        self,
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
        t: float,
    ) -> Tuple[float, float, float]:
        """Linearly interpolates between two RGB colour tuples.

        Args:
            a: Start colour.
            b: End colour.
            t: Interpolation factor in [0.0, 1.0].

        Returns:
            The interpolated colour tuple.
        """
        t_clamped = max(0.0, min(1.0, t))
        return (
            a[0] + (b[0] - a[0]) * t_clamped,
            a[1] + (b[1] - a[1]) * t_clamped,
            a[2] + (b[2] - a[2]) * t_clamped,
        )

    def _get_default_colors_for_time(
        self,
        normalised_time: float,
    ) -> Dict[str, Tuple[float, float, float]]:
        """Produces a default day-night gradient cycle based on normalised time.

        The cycle models a realistic progression: dark midnight blues, dawn
        oranges, bright daytime blues, and evening purples.

        Args:
            normalised_time: Time in [0.0, 1.0] where 0.0 = midnight.

        Returns:
            A dict with 'top', 'horizon', and 'bottom' colour tuples.
        """
        t = normalised_time % 1.0

        midnight_top = (0.02, 0.02, 0.10)
        dawn_top = (0.25, 0.20, 0.45)
        noon_top = (0.20, 0.50, 0.90)
        dusk_top = (0.35, 0.15, 0.50)
        midnight_horizon = (0.03, 0.03, 0.12)
        dawn_horizon = (0.80, 0.40, 0.25)
        noon_horizon = (0.60, 0.75, 0.95)
        dusk_horizon = (0.90, 0.35, 0.20)
        midnight_bottom = (0.01, 0.01, 0.04)
        dawn_bottom = (0.70, 0.60, 0.45)
        noon_bottom = (0.85, 0.85, 0.85)
        dusk_bottom = (0.65, 0.30, 0.25)

        if t < 0.25:
            factor = t / 0.25
            top = self._lerp_color(midnight_top, dawn_top, factor)
            horizon = self._lerp_color(midnight_horizon, dawn_horizon, factor)
            bottom = self._lerp_color(midnight_bottom, dawn_bottom, factor)
        elif t < 0.30:
            factor = (t - 0.25) / 0.05
            dawn_noon_top = self._lerp_color(dawn_top, noon_top, factor)
            dawn_noon_horizon = self._lerp_color(dawn_horizon, noon_horizon, factor)
            dawn_noon_bottom = self._lerp_color(dawn_bottom, noon_bottom, factor)
            top = dawn_noon_top
            horizon = dawn_noon_horizon
            bottom = dawn_noon_bottom
        elif t < 0.45:
            top = noon_top
            horizon = noon_horizon
            bottom = noon_bottom
        elif t < 0.50:
            factor = (t - 0.45) / 0.05
            top = self._lerp_color(noon_top, dusk_top, factor)
            horizon = self._lerp_color(noon_horizon, dusk_horizon, factor)
            bottom = self._lerp_color(noon_bottom, dusk_bottom, factor)
        elif t < 0.75:
            top = dusk_top
            horizon = dusk_horizon
            bottom = dusk_bottom
        elif t < 0.80:
            factor = (t - 0.75) / 0.05
            top = self._lerp_color(dusk_top, midnight_top, factor)
            horizon = self._lerp_color(dusk_horizon, midnight_horizon, factor)
            bottom = self._lerp_color(dusk_bottom, midnight_bottom, factor)
        else:
            top = midnight_top
            horizon = midnight_horizon
            bottom = midnight_bottom

        return {
            "top": top,
            "horizon": horizon,
            "bottom": bottom,
        }

    def _compute_sun_direction(
        self,
        normalised_time: float,
    ) -> Tuple[float, float, float]:
        """Computes a sun direction vector from normalised time.

        The sun traces an arc from east (dawn) to west (dusk), with the
        elevation peaking at noon. Returns a unit-length direction vector.

        Args:
            normalised_time: Time in [0.0, 1.0] where 0.0 = midnight.

        Returns:
            A (x, y, z) tuple representing the sun direction.
        """
        t = normalised_time % 1.0
        azimuth_rad = t * math.pi * 2.0
        elevation_rad = math.sin(t * math.pi) * math.pi * 0.45
        x = math.cos(elevation_rad) * math.cos(azimuth_rad)
        y = math.sin(elevation_rad)
        z = math.cos(elevation_rad) * math.sin(azimuth_rad)
        return (x, y, z)

    def _generate_star_positions(
        self,
        density: StarDensity,
    ) -> List[Dict]:
        """Procedurally generates star positions on a unit hemisphere.

        Stars are distributed with a preference toward the upper hemisphere
        and away from the horizon for a natural night-sky appearance.

        Args:
            density: The StarDensity level controlling the star count.

        Returns:
            A list of dicts, each with 'position' (x,y,z), 'brightness',
            and 'size' fields.
        """
        count = density.star_count
        stars: List[Dict] = []
        if count == 0:
            return stars

        rng = random.Random(42)
        for _ in range(count):
            phi = rng.uniform(0.0, math.pi * 2.0)
            theta = rng.uniform(0.0, math.pi * 0.48)
            x = math.sin(theta) * math.cos(phi)
            y = math.cos(theta)
            z = math.sin(theta) * math.sin(phi)
            brightness = rng.uniform(0.3, 1.0)
            size = rng.uniform(0.5, 2.5)
            color_variation = rng.uniform(0.0, 1.0)
            if color_variation < 0.05:
                r, g, b = 1.0, 0.85, 0.70
            elif color_variation < 0.10:
                r, g, b = 0.70, 0.80, 1.0
            else:
                r, g, b = 1.0, 1.0, 1.0
            stars.append({
                "position": (x, y, z),
                "brightness": brightness,
                "size": size,
                "color": (r, g, b),
            })
        return stars

    def _generate_cloud_layers(
        self,
        coverage: float,
    ) -> List[Dict]:
        """Generates active cloud layer descriptors based on coverage.

        Coverage above 0.5 adds nimbus and stratus layers. Coverage above
        0.3 adds cumulus. Coverage above 0.1 adds cirrus wisps.

        Args:
            coverage: Overall cloud coverage in [0.0, 1.0].

        Returns:
            A list of dicts describing active cloud layers with type,
            altitude, opacity, and coverage properties.
        """
        layers: List[Dict] = []
        if coverage <= 0.0:
            return layers

        if coverage >= 0.6:
            layers.append({
                "type": CloudLayer.NIMBUS.value,
                "altitude": CloudLayer.NIMBUS.default_altitude,
                "opacity": CloudLayer.NIMBUS.default_opacity * coverage,
                "coverage": CloudLayer.NIMBUS.default_coverage,
            })
        if coverage >= 0.4:
            layers.append({
                "type": CloudLayer.STRATUS.value,
                "altitude": CloudLayer.STRATUS.default_altitude,
                "opacity": CloudLayer.STRATUS.default_opacity * coverage,
                "coverage": CloudLayer.STRATUS.default_coverage,
            })
        if coverage >= 0.2:
            layers.append({
                "type": CloudLayer.CUMULUS.value,
                "altitude": CloudLayer.CUMULUS.default_altitude,
                "opacity": CloudLayer.CUMULUS.default_opacity * coverage,
                "coverage": CloudLayer.CUMULUS.default_coverage,
            })
        if coverage >= 0.08:
            layers.append({
                "type": CloudLayer.CIRRUS.value,
                "altitude": CloudLayer.CIRRUS.default_altitude,
                "opacity": CloudLayer.CIRRUS.default_opacity * coverage,
                "coverage": CloudLayer.CIRRUS.default_coverage,
            })
        return layers

    def _apply_rayleigh_scattering(
        self,
        color: Tuple[float, float, float],
        view_direction: Tuple[float, float, float],
        sun_direction: Tuple[float, float, float],
    ) -> Tuple[float, float, float]:
        """Applies a simplified Rayleigh scattering model to a colour.

        Computes scattering contribution based on the angle between the
        view direction and the sun direction. Larger angles (near horizon)
        produce stronger blue scatter. Small angles (near the sun) produce
        redder hues.

        Args:
            color: The base RGB colour to scatter.
            view_direction: Normalised view direction vector.
            sun_direction: Normalised sun direction vector.

        Returns:
            The scattered RGB colour tuple.
        """
        cos_angle = max(
            -1.0,
            min(
                1.0,
                view_direction[0] * sun_direction[0]
                + view_direction[1] * sun_direction[1]
                + view_direction[2] * sun_direction[2],
            ),
        )
        phase = (3.0 / (16.0 * math.pi)) * (1.0 + cos_angle * cos_angle)
        intensity = max(0.0, phase * self._atmosphere_params.sun_intensity)
        beta_r = self._atmosphere_params.rayleigh_coefficient
        scatter_r = min(1.0, color[0] + beta_r[0] * intensity * 1e4)
        scatter_g = min(1.0, color[1] + beta_r[1] * intensity * 1e4)
        scatter_b = min(1.0, color[2] + beta_r[2] * intensity * 1e4)
        exposure = self._atmosphere_params.exposure
        return (
            1.0 - math.exp(-scatter_r * exposure),
            1.0 - math.exp(-scatter_g * exposure),
            1.0 - math.exp(-scatter_b * exposure),
        )

    # ------------------------------------------------------------------
    # Public API: Configuration management
    # ------------------------------------------------------------------

    def create_config(
        self,
        name: str,
        preset: SkyPreset,
    ) -> SkyConfig:
        """Creates a new sky configuration from a preset.

        Loads default colour, sun position, cloud, and star parameters
        from the preset and registers the configuration for runtime use.

        Args:
            name: A descriptive name for the configuration.
            preset: The SkyPreset to base this configuration on.

        Returns:
            The newly created SkyConfig instance.
        """
        with self._lock:
            preset_data = self._PRESET_CONFIGS.get(
                preset, self._PRESET_CONFIGS[SkyPreset.CLEAR_DAY]
            )
            config = SkyConfig(
                preset=preset,
                top_color=preset_data["top_color"],
                horizon_color=preset_data["horizon_color"],
                bottom_color=preset_data["bottom_color"],
                sun_azimuth=preset_data["sun_azimuth"],
                sun_elevation=preset_data["sun_elevation"],
                cloud_coverage=preset_data["cloud_coverage"],
                star_density=preset_data["star_density"],
                atmosphere_thickness=preset_data["atmosphere_thickness"],
            )
            self._sky_configs[config.id] = config
            self._stats["total_configs_created"] += 1
            return config

    def set_active_config(self, config_id: str) -> None:
        """Sets the active skybox configuration by ID.

        Args:
            config_id: The UUID of the SkyConfig to activate.

        Raises:
            KeyError: If no configuration exists with the given ID.
        """
        with self._lock:
            if config_id not in self._sky_configs:
                raise KeyError(
                    f"No sky configuration found with id '{config_id}'"
                )
            self._active_config_id = config_id

    def get_config(self, config_id: str) -> Optional[SkyConfig]:
        """Retrieves a sky configuration by its ID.

        Args:
            config_id: The UUID of the configuration.

        Returns:
            The SkyConfig if found, None otherwise.
        """
        with self._lock:
            return self._sky_configs.get(config_id)

    def list_configs(self) -> List[SkyConfig]:
        """Returns all registered sky configurations.

        Returns:
            A list of all SkyConfig instances.
        """
        with self._lock:
            return list(self._sky_configs.values())

    def remove_config(self, config_id: str) -> bool:
        """Removes a sky configuration by its ID.

        If the removed config is the active one, the active config is
        cleared and subsequent renders fall back to default colours.

        Args:
            config_id: The UUID of the configuration to remove.

        Returns:
            True if the config was found and removed, False otherwise.
        """
        with self._lock:
            if config_id in self._sky_configs:
                del self._sky_configs[config_id]
                if self._active_config_id == config_id:
                    self._active_config_id = ""
                return True
            return False

    # ------------------------------------------------------------------
    # Public API: Time-of-day progression
    # ------------------------------------------------------------------

    def update_time(self, delta_seconds: float) -> None:
        """Advances the time-of-day by the given delta.

        The normalised time wraps from 1.0 back to 0.0, simulating a full
        day-night cycle. A default 24-hour cycle is assumed, so a delta of
        86400 seconds (24 hours) completes one full cycle.

        Args:
            delta_seconds: Time delta in seconds to advance.
        """
        with self._lock:
            self._time_progression += delta_seconds / 86400.0
            self._time_progression %= 1.0

    def set_time(self, normalised_time: float) -> None:
        """Sets the time-of-day to an absolute normalised value.

        Args:
            normalised_time: Target time in [0.0, 1.0] where 0.0 = midnight.
        """
        with self._lock:
            self._time_progression = normalised_time % 1.0

    def get_current_time(self) -> float:
        """Returns the current normalised time-of-day.

        Returns:
            The current time in [0.0, 1.0].
        """
        with self._lock:
            return self._time_progression

    def get_time_of_day(self) -> TimeOfDay:
        """Returns the current TimeOfDay phase.

        Returns:
            The TimeOfDay enum value for the current time.
        """
        with self._lock:
            return TimeOfDay.from_normalised_time(self._time_progression)

    # ------------------------------------------------------------------
    # Public API: Atmosphere parameters
    # ------------------------------------------------------------------

    def set_atmosphere_params(self, params: AtmosphereParams) -> None:
        """Replaces the active atmosphere parameters.

        Args:
            params: The new AtmosphereParams to use.
        """
        with self._lock:
            self._atmosphere_params = params

    def get_atmosphere_params(self) -> AtmosphereParams:
        """Returns the current atmosphere parameters.

        Returns:
            A copy of the active AtmosphereParams.
        """
        with self._lock:
            return AtmosphereParams(
                rayleigh_coefficient=self._atmosphere_params.rayleigh_coefficient,
                mie_coefficient=self._atmosphere_params.mie_coefficient,
                sun_intensity=self._atmosphere_params.sun_intensity,
                scattering_samples=self._atmosphere_params.scattering_samples,
                exposure=self._atmosphere_params.exposure,
            )

    # ------------------------------------------------------------------
    # Public API: Rendering
    # ------------------------------------------------------------------

    def interpolate_colors(
        self,
        time_of_day: Optional[TimeOfDay] = None,
    ) -> Dict[str, Tuple[float, float, float]]:
        """Interpolates sky gradient colours for the current or given time.

        If an active configuration is set, its colours are blended with the
        default day-night cycle based on the config's parameters. Otherwise,
        a pure day-night cycle is used.

        Args:
            time_of_day: Optional TimeOfDay override. Uses current time
                progression if not provided.

        Returns:
            A dict with 'top', 'horizon', and 'bottom' colour tuples.
        """
        with self._lock:
            if time_of_day is not None:
                start, end = time_of_day.normalised_range
                local_time = (start + end) / 2.0
            else:
                local_time = self._time_progression

            default_colors = self._get_default_colors_for_time(local_time)

            if not self._active_config_id:
                return default_colors

            config = self._sky_configs.get(self._active_config_id)
            if config is None:
                return default_colors

            blend_factor = 0.7
            top = self._lerp_color(
                default_colors["top"], config.top_color, blend_factor
            )
            horizon = self._lerp_color(
                default_colors["horizon"], config.horizon_color, blend_factor
            )
            bottom = self._lerp_color(
                default_colors["bottom"], config.bottom_color, blend_factor
            )
            return {"top": top, "horizon": horizon, "bottom": bottom}

    def generate_star_field(
        self,
        density: Optional[StarDensity] = None,
    ) -> List[Dict]:
        """Generates a procedural star field for the night sky.

        Uses the active configuration's star density if none is specified.
        Returns an empty list if density is NONE or no stars are configured.

        Args:
            density: Optional StarDensity override.

        Returns:
            A list of star descriptors with position, brightness, size,
            and colour fields.
        """
        with self._lock:
            if density is not None:
                resolved_density = density
            elif self._active_config_id:
                config = self._sky_configs.get(self._active_config_id)
                resolved_density = (
                    config.star_density if config else StarDensity.NORMAL
                )
            else:
                resolved_density = StarDensity.NORMAL
            return self._generate_star_positions(resolved_density)

    def apply_atmosphere(
        self,
        color: Tuple[float, float, float],
        view_direction: Tuple[float, float, float],
    ) -> Tuple[float, float, float]:
        """Applies atmospheric scattering to a given colour.

        Computes Rayleigh scattering based on the view direction relative
        to the current sun position. This should be applied to distant
        objects (e.g., mountains, skybox geometry) for atmospheric depth.

        Args:
            color: The base RGB colour to scatter.
            view_direction: Normalised (x, y, z) view direction vector.

        Returns:
            The scattered RGB colour tuple.
        """
        with self._lock:
            sun_dir = self._compute_sun_direction(self._time_progression)
            return self._apply_rayleigh_scattering(color, view_direction, sun_dir)

    def get_current_sky_state(self) -> SkyRenderState:
        """Captures a complete snapshot of the current sky rendering state.

        Computes interpolated colours, generates the current star field,
        determines active cloud layers, and packs everything into a single
        render state for consumption by the rendering pipeline.

        Returns:
            A SkyRenderState with all current sky data.
        """
        with self._lock:
            colors = self.interpolate_colors()

            if self._active_config_id:
                config = self._sky_configs.get(self._active_config_id)
                density = config.star_density if config else StarDensity.NONE
                coverage = config.cloud_coverage if config else 0.0
            else:
                time_of_day = TimeOfDay.from_normalised_time(
                    self._time_progression
                )
                if time_of_day in (TimeOfDay.NIGHT, TimeOfDay.MIDNIGHT):
                    density = StarDensity.DENSE
                elif time_of_day in (TimeOfDay.DAWN, TimeOfDay.DUSK):
                    density = StarDensity.SPARSE
                else:
                    density = StarDensity.NONE
                coverage = 0.2

            star_field = self._generate_star_positions(density)
            cloud_layers = self._generate_cloud_layers(coverage)

            self._stats["total_frames_rendered"] += 1

            return SkyRenderState(
                config_id=self._active_config_id,
                current_time=self._time_progression,
                interpolated_colors=colors,
                visible_stars=star_field,
                active_clouds=cloud_layers,
                render_calls_this_frame=1,
            )

    # ------------------------------------------------------------------
    # Public API: Transitions
    # ------------------------------------------------------------------

    def transition_to(
        self,
        config_id: str,
        duration_seconds: float = 2.0,
    ) -> None:
        """Initiates a smooth transition to a new sky configuration.

        The transition blends from the current sky state to the target
        configuration's colours over the specified duration. Internally
        this sets the active configuration immediately; actual colour
        blending is handled by the interpolate_colors method.

        Args:
            config_id: The UUID of the target SkyConfig.
            duration_seconds: Transition duration in seconds.

        Raises:
            KeyError: If no configuration exists with the given ID.
        """
        with self._lock:
            if config_id not in self._sky_configs:
                raise KeyError(
                    f"No sky configuration found with id '{config_id}'"
                )
            self._active_config_id = config_id
            self._stats["total_transitions"] += 1

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Returns a comprehensive statistics dictionary for monitoring.

        Includes configuration counts, rendering statistics, current
        time-of-day, active configuration, and atmosphere parameter
        summaries.

        Returns:
            A dictionary with string keys and numeric/collection values.
        """
        with self._lock:
            active_preset = None
            if self._active_config_id:
                config = self._sky_configs.get(self._active_config_id)
                if config:
                    active_preset = config.preset.value

            config_presets: Dict[str, int] = {}
            for cfg in self._sky_configs.values():
                preset_name = cfg.preset.value
                config_presets[preset_name] = (
                    config_presets.get(preset_name, 0) + 1
                )

            return {
                "total_configs_created": self._stats["total_configs_created"],
                "total_transitions": self._stats["total_transitions"],
                "total_frames_rendered": self._stats["total_frames_rendered"],
                "active_configs_count": len(self._sky_configs),
                "active_config_id": self._active_config_id,
                "active_preset": active_preset,
                "current_time": self._time_progression,
                "time_of_day": self.get_time_of_day().value,
                "config_presets_breakdown": config_presets,
                "atmosphere_params": self._atmosphere_params.to_dict(),
            }

    def reset(self) -> None:
        """Resets all renderer state to initial defaults.

        Clears all configurations, resets time progression to noon,
        restores default atmosphere parameters, and zeroes statistics.
        """
        with self._lock:
            self._sky_configs.clear()
            self._active_config_id = ""
            self._time_progression = 0.42
            self._atmosphere_params = AtmosphereParams()
            self._stats = {
                "total_configs_created": 0,
                "total_transitions": 0,
                "total_frames_rendered": 0,
            }

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"SkyboxRenderer(configs={len(self._sky_configs)}, "
                f"active={self._active_config_id[:8] if self._active_config_id else 'none'}..., "
                f"time={self._time_progression:.3f}, "
                f"frames={self._stats['total_frames_rendered']})"
            )


def get_skybox_renderer() -> SkyboxRenderer:
    """Module-level accessor for the SkyboxRenderer singleton.

    Convenience function that returns the singleton instance without
    needing to reference SkyboxRenderer.get_instance() directly.

    Returns:
        The singleton SkyboxRenderer instance.
    """
    return SkyboxRenderer.get_instance()