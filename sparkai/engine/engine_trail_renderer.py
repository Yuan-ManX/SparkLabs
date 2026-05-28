"""
TrailRenderer - Singleton system for rendering ribbon/particle trails behind
moving objects, projectile paths, sword swings, and motion effects.

Manages trail configurations, active trail instances, point lifecycle (birth,
fade, culling), and produces visible segment data for the rendering pipeline.
Supports multiple trail modes, fade curves, materials, and attachment points.
"""

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

_time_module = time


class TrailMode(Enum):
    """Visual modes determining how trail points are connected and rendered.

    Each mode produces a distinct visual effect suitable for different
    gameplay scenarios: ribbon trails for melee weapons, particle bursts
    for explosions, ghost echoes for dash abilities, etc.
    """

    RIBBON = "ribbon"
    PARTICLE_BURST = "particle_burst"
    GHOST_ECHO = "ghost_echo"
    DASH_LINE = "dash_line"
    SMOKE_PLUME = "smoke_plume"
    ENERGY_BEAM = "energy_beam"


class TrailFadeMode(Enum):
    """Fade curves controlling how trail alpha decays over time.

    LINEAR produces a constant fade rate. EXPONENTIAL fades quickly at first
    then slows. SMOOTH_STEP uses a cubic hermite curve for natural-looking
    fade-in/fade-out transitions. NONE keeps full opacity until removal.
    """

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    SMOOTH_STEP = "smooth_step"
    NONE = "none"

    def compute_alpha(self, elapsed: float, duration: float) -> float:
        """Computes the alpha multiplier for a point given elapsed time.

        Args:
            elapsed: Time in seconds since the point was created.
            duration: Total fade duration in seconds.

        Returns:
            Alpha value clamped between 0.0 and 1.0.
        """
        if duration <= 0.0:
            return 0.0 if elapsed > 0 else 1.0

        t = elapsed / duration

        if self == TrailFadeMode.LINEAR:
            alpha = 1.0 - t
        elif self == TrailFadeMode.EXPONENTIAL:
            alpha = math.exp(-3.0 * t)
        elif self == TrailFadeMode.SMOOTH_STEP:
            alpha = 1.0 - (t * t * (3.0 - 2.0 * t))
        elif self == TrailFadeMode.NONE:
            alpha = 1.0
        else:
            alpha = 1.0 - t

        return max(0.0, min(1.0, alpha))


class TrailMaterial(Enum):
    """Surface materials defining how trail geometry reacts to lighting.

    SOLID_COLOR ignores lighting entirely. GRADIENT blends between start
    and end colors along the trail length. TEXTURED applies a texture map.
    GLOW adds an emissive bloom pass. TRANSLUCENT uses alpha blending with
    back-to-front sorting. SPARKLE adds animated specular highlights.
    """

    SOLID_COLOR = "solid_color"
    GRADIENT = "gradient"
    TEXTURED = "textured"
    GLOW = "glow"
    TRANSLUCENT = "translucent"
    SPARKLE = "sparkle"


class TrailAttachment(Enum):
    """Attachment points defining where a trail originates on an object.

    OBJECT_CENTER uses the object's pivot point. OBJECT_EDGE samples the
    object's bounding surface closest to the camera. CUSTOM_OFFSET applies
    a user-defined local-space offset. MOUSE_CURSOR follows the screen-space
    cursor projected into world space. PROJECTILE_TIP attaches to the front
    of a projectile's velocity-aligned bounding box.
    """

    OBJECT_CENTER = "object_center"
    OBJECT_EDGE = "object_edge"
    CUSTOM_OFFSET = "custom_offset"
    MOUSE_CURSOR = "mouse_cursor"
    PROJECTILE_TIP = "projectile_tip"


@dataclass
class TrailPoint:
    """A single sampled point along a trail's path.

    Records the world-space position, capture timestamp, instantaneous
    velocity, current alpha, and point size. Trail renderers use sequences
    of TrailPoints to construct ribbon geometry or particle placements.
    """

    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    timestamp: float = field(default_factory=_time_module.time)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    alpha: float = 1.0
    size: float = 1.0

    @property
    def speed(self) -> float:
        """Magnitude of the velocity vector at this point."""
        vx, vy, vz = self.velocity
        return math.sqrt(vx * vx + vy * vy + vz * vz)

    @property
    def age(self) -> float:
        """Elapsed time in seconds since this point was recorded."""
        return _time_module.time() - self.timestamp

    def to_dict(self) -> dict:
        """Serializes the trail point to a dictionary."""
        return {
            "position": list(self.position),
            "timestamp": self.timestamp,
            "velocity": list(self.velocity),
            "alpha": self.alpha,
            "size": self.size,
            "speed": self.speed,
            "age": self.age,
        }

    def __repr__(self) -> str:
        return (
            f"TrailPoint(pos=({self.position[0]:.2f}, {self.position[1]:.2f}, "
            f"{self.position[2]:.2f}), alpha={self.alpha:.2f}, "
            f"size={self.size:.2f})"
        )


@dataclass
class TrailConfig:
    """Persistent configuration template for a trail effect.

    Defines the visual parameters shared across all trail instances created
    from this configuration: colors, widths, fade behavior, material type,
    point budget, and attachment point. Configs are registered with the
    TrailRenderer and referenced by ID when spawning trail instances.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "default_trail"
    mode: TrailMode = TrailMode.RIBBON
    color_start: Tuple[int, int, int, int] = (255, 255, 255, 255)
    color_end: Tuple[int, int, int, int] = (255, 255, 255, 0)
    width_start: float = 0.5
    width_end: float = 0.0
    max_points: int = 100
    fade_duration: float = 1.0
    fade_mode: TrailFadeMode = TrailFadeMode.LINEAR
    material: TrailMaterial = TrailMaterial.SOLID_COLOR
    attachment: TrailAttachment = TrailAttachment.OBJECT_CENTER
    emission_rate: float = 60.0
    gravity: Tuple[float, float, float] = (0.0, -9.8, 0.0)
    texture_tile: float = 1.0
    sort_offset: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates configuration parameters after construction."""
        if self.max_points < 2:
            raise ValueError(f"max_points must be at least 2, got {self.max_points}")
        if self.fade_duration < 0.0:
            raise ValueError(
                f"fade_duration must be non-negative, got {self.fade_duration}"
            )
        if self.width_start < 0.0:
            raise ValueError(
                f"width_start must be non-negative, got {self.width_start}"
            )
        if self.width_end < 0.0:
            raise ValueError(
                f"width_end must be non-negative, got {self.width_end}"
            )
        if self.emission_rate <= 0.0:
            raise ValueError(
                f"emission_rate must be positive, got {self.emission_rate}"
            )
        for channel in self.color_start:
            if not 0 <= channel <= 255:
                raise ValueError(
                    f"color_start channel out of range [0,255]: {channel}"
                )
        for channel in self.color_end:
            if not 0 <= channel <= 255:
                raise ValueError(
                    f"color_end channel out of range [0,255]: {channel}"
                )

    def to_dict(self) -> dict:
        """Serializes the trail configuration to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode.value,
            "color_start": list(self.color_start),
            "color_end": list(self.color_end),
            "width_start": self.width_start,
            "width_end": self.width_end,
            "max_points": self.max_points,
            "fade_duration": self.fade_duration,
            "fade_mode": self.fade_mode.value,
            "material": self.material.value,
            "attachment": self.attachment.value,
            "emission_rate": self.emission_rate,
            "gravity": list(self.gravity),
            "texture_tile": self.texture_tile,
            "sort_offset": self.sort_offset,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"TrailConfig(id={self.id[:8]}..., name={self.name}, "
            f"mode={self.mode.value}, max_pts={self.max_points})"
        )


@dataclass
class TrailInstance:
    """An active trail attached to a game object.

    Links a TrailConfig to a specific object, maintains the ordered list
    of TrailPoints sampled over time, and tracks whether the trail is
    currently emitting and how long it has been alive.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str = ""
    object_id: str = ""
    points: List[TrailPoint] = field(default_factory=list)
    active: bool = True
    lifetime: float = 0.0
    time_since_last_emit: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    @property
    def point_count(self) -> int:
        """Number of points currently in the trail."""
        return len(self.points)

    @property
    def is_expired(self) -> bool:
        """Whether the trail has been deactivated and all points have faded."""
        return not self.active and len(self.points) == 0

    def to_dict(self) -> dict:
        """Serializes the trail instance to a dictionary."""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "object_id": self.object_id,
            "point_count": self.point_count,
            "active": self.active,
            "lifetime": self.lifetime,
            "time_since_last_emit": self.time_since_last_emit,
            "is_expired": self.is_expired,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"TrailInstance(id={self.id[:8]}..., obj={self.object_id[:8]}..., "
            f"config={self.config_id[:8]}..., pts={self.point_count}, "
            f"active={self.active})"
        )


@dataclass
class TrailSegment:
    """A visible segment produced for rendering between two trail points.

    Contains the interpolated world-space positions, colors, widths, and
    alpha values needed by the GPU to draw one quad or ribbon strip
    connecting two consecutive TrailPoints.
    """

    point_a: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    point_b: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    color_a: Tuple[int, int, int, int] = (255, 255, 255, 255)
    color_b: Tuple[int, int, int, int] = (255, 255, 255, 255)
    width_a: float = 1.0
    width_b: float = 1.0
    alpha: float = 1.0
    instance_id: str = ""
    material: TrailMaterial = TrailMaterial.SOLID_COLOR
    texture_tile: float = 1.0

    def to_dict(self) -> dict:
        """Serializes the trail segment to a dictionary."""
        return {
            "point_a": list(self.point_a),
            "point_b": list(self.point_b),
            "color_a": list(self.color_a),
            "color_b": list(self.color_b),
            "width_a": self.width_a,
            "width_b": self.width_b,
            "alpha": self.alpha,
            "instance_id": self.instance_id,
            "material": self.material.value,
            "texture_tile": self.texture_tile,
        }

    def __repr__(self) -> str:
        return (
            f"TrailSegment(a=({self.point_a[0]:.1f},{self.point_a[1]:.1f}), "
            f"alpha={self.alpha:.2f}, w={self.width_a:.2f})"
        )


class TrailRenderer:
    """Singleton manager for trail effects rendering.

    Central system for creating trail configurations, spawning trail instances
    on game objects, recording position samples each frame, fading and culling
    old points, and producing sorted visible segments for the GPU.

    Thread-safe via a reentrant lock. Use get_trail_renderer() or
    TrailRenderer.get_instance() to obtain the singleton instance.
    """

    _instance: Optional["TrailRenderer"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_MAX_TRAIL_INSTANCES: int = 256
    _DEFAULT_MAX_TOTAL_POINTS: int = 16384

    def __new__(cls) -> "TrailRenderer":
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
        self._trail_configs: Dict[str, TrailConfig] = {}
        self._active_trails: Dict[str, TrailInstance] = {}
        self._trail_pool: List[TrailInstance] = []
        self._stats: Dict = {
            "total_configs_created": 0,
            "total_instances_spawned": 0,
            "total_points_emitted": 0,
            "total_points_culled": 0,
            "total_segments_generated": 0,
            "peak_concurrent_trails": 0,
            "peak_total_points": 0,
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "TrailRenderer":
        """Returns the singleton TrailRenderer instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _interpolate_color(
        self,
        start: Tuple[int, int, int, int],
        end: Tuple[int, int, int, int],
        t: float,
    ) -> Tuple[int, int, int, int]:
        """Linearly interpolates between two RGBA colors.

        Args:
            start: The starting RGBA tuple.
            end: The ending RGBA tuple.
            t: Interpolation factor in [0.0, 1.0].

        Returns:
            Interpolated RGBA tuple with integer channel values.
        """
        t_clamped = max(0.0, min(1.0, t))
        return tuple(
            int(start[i] + (end[i] - start[i]) * t_clamped)
            for i in range(4)
        )

    def _interpolate_width(
        self,
        width_start: float,
        width_end: float,
        t: float,
    ) -> float:
        """Linearly interpolates between start and end width values.

        Args:
            width_start: Width at the head of the trail.
            width_end: Width at the tail of the trail.
            t: Interpolation factor in [0.0, 1.0].

        Returns:
            Interpolated width value.
        """
        t_clamped = max(0.0, min(1.0, t))
        return width_start + (width_end - width_start) * t_clamped

    def _apply_fade(
        self,
        points: List[TrailPoint],
        fade_mode: TrailFadeMode,
        fade_duration: float,
    ) -> List[TrailPoint]:
        """Applies fade curve to all points, returning only visible ones.

        Computes alpha for each point using the configured fade mode and
        removes points whose alpha has reached zero.

        Args:
            points: The list of TrailPoints to process.
            fade_mode: The fade curve to apply.
            fade_duration: Total fade duration in seconds.

        Returns:
            Filtered list containing only points with alpha > 0.
        """
        visible: List[TrailPoint] = []
        current_time = _time_module.time()

        for point in points:
            elapsed = current_time - point.timestamp
            point.alpha = fade_mode.compute_alpha(elapsed, fade_duration)
            if point.alpha > 0.0:
                visible.append(point)
            else:
                self._stats["total_points_culled"] += 1

        return visible

    def _cull_excess_points(
        self,
        points: List[TrailPoint],
        max_points: int,
    ) -> List[TrailPoint]:
        """Trims the oldest points when the trail exceeds its point budget.

        Args:
            points: The list of TrailPoints to trim.
            max_points: Maximum number of points allowed.

        Returns:
            A list trimmed to at most max_points, keeping the newest points.
        """
        if len(points) <= max_points:
            return points

        excess = len(points) - max_points
        self._stats["total_points_culled"] += excess
        return points[excess:]

    def _build_segments_for_instance(
        self,
        instance: TrailInstance,
        config: TrailConfig,
    ) -> List[TrailSegment]:
        """Constructs TrailSegments from a trail instance's point list.

        Walks pairs of consecutive points and produces one TrailSegment
        per pair with interpolated colors, widths, and metadata.

        Args:
            instance: The TrailInstance to build segments from.
            config: The TrailConfig defining visual parameters.

        Returns:
            A list of TrailSegments ready for rendering.
        """
        segments: List[TrailSegment] = []
        points = instance.points

        if len(points) < 2:
            return segments

        total_count = len(points)

        for i in range(total_count - 1):
            point_a = points[i]
            point_b = points[i + 1]

            t = i / max(total_count - 1, 1)

            color_a = self._interpolate_color(
                config.color_start, config.color_end, t
            )
            color_b = self._interpolate_color(
                config.color_start, config.color_end,
                (i + 1) / max(total_count - 1, 1),
            )

            width_a = self._interpolate_width(
                config.width_start, config.width_end, t
            )
            width_b = self._interpolate_width(
                config.width_start, config.width_end,
                (i + 1) / max(total_count - 1, 1),
            )

            avg_alpha = (point_a.alpha + point_b.alpha) * 0.5

            segment = TrailSegment(
                point_a=point_a.position,
                point_b=point_b.position,
                color_a=color_a,
                color_b=color_b,
                width_a=width_a,
                width_b=width_b,
                alpha=avg_alpha,
                instance_id=instance.id,
                material=config.material,
                texture_tile=config.texture_tile,
            )
            segments.append(segment)

        self._stats["total_segments_generated"] += len(segments)
        return segments

    def _acquire_instance(self) -> TrailInstance:
        """Obtains a TrailInstance from the pool or creates a new one.

        Returns:
            A TrailInstance ready for use.
        """
        if self._trail_pool:
            instance = self._trail_pool.pop()
            instance.points.clear()
            instance.active = True
            instance.lifetime = 0.0
            instance.time_since_last_emit = 0.0
            instance.created_at = _time_module.time()
            return instance
        return TrailInstance()

    def _release_instance(self, instance: TrailInstance) -> None:
        """Returns a TrailInstance to the pool for reuse.

        Args:
            instance: The TrailInstance to recycle.
        """
        instance.points.clear()
        instance.active = False
        self._trail_pool.append(instance)

    def _update_stats_peaks(self) -> None:
        """Updates peak concurrent trail and total point statistics."""
        concurrent = len(self._active_trails)
        if concurrent > self._stats["peak_concurrent_trails"]:
            self._stats["peak_concurrent_trails"] = concurrent

        total_points = sum(
            inst.point_count for inst in self._active_trails.values()
        )
        if total_points > self._stats["peak_total_points"]:
            self._stats["peak_total_points"] = total_points

    # ------------------------------------------------------------------
    # Public API: Configuration management
    # ------------------------------------------------------------------

    def create_config(
        self,
        name: str,
        mode: TrailMode,
        color_start: Tuple[int, int, int, int],
        color_end: Tuple[int, int, int, int],
        width_start: float = 0.5,
        width_end: float = 0.0,
        max_points: int = 100,
        fade_duration: float = 1.0,
        fade_mode: TrailFadeMode = TrailFadeMode.LINEAR,
        material: TrailMaterial = TrailMaterial.SOLID_COLOR,
        attachment: TrailAttachment = TrailAttachment.OBJECT_CENTER,
        emission_rate: float = 60.0,
        gravity: Tuple[float, float, float] = (0.0, -9.8, 0.0),
        texture_tile: float = 1.0,
        sort_offset: int = 0,
    ) -> TrailConfig:
        """Creates and registers a new trail configuration.

        Trail configs define the visual template for trail effects. Once
        registered, they can be referenced by ID when spawning instances
        via attach_trail().

        Args:
            name: Human-readable name for this trail config.
            mode: The visual mode (ribbon, particle burst, etc.).
            color_start: RGBA color at the head of the trail.
            color_end: RGBA color at the tail of the trail.
            width_start: Width at the head of the trail.
            width_end: Width at the tail of the trail.
            max_points: Maximum trail points before oldest are culled.
            fade_duration: Time in seconds for points to fully fade.
            fade_mode: Alpha fade curve to apply over time.
            material: Surface material type.
            attachment: Where the trail attaches to the object.
            emission_rate: Points emitted per second while active.
            gravity: World-space gravity applied to particles.
            texture_tile: Texture repeat count along the trail.
            sort_offset: Rendering sort order offset.

        Returns:
            The created TrailConfig instance.

        Raises:
            ValueError: If any parameter fails validation.
        """
        with self._lock:
            config = TrailConfig(
                name=name,
                mode=mode,
                color_start=color_start,
                color_end=color_end,
                width_start=width_start,
                width_end=width_end,
                max_points=max_points,
                fade_duration=fade_duration,
                fade_mode=fade_mode,
                material=material,
                attachment=attachment,
                emission_rate=emission_rate,
                gravity=gravity,
                texture_tile=texture_tile,
                sort_offset=sort_offset,
            )

            self._trail_configs[config.id] = config
            self._stats["total_configs_created"] += 1
            return config

    def get_config(self, config_id: str) -> Optional[TrailConfig]:
        """Retrieves a trail configuration by its ID.

        Args:
            config_id: The unique ID of the trail config.

        Returns:
            The TrailConfig if found, None otherwise.
        """
        with self._lock:
            return self._trail_configs.get(config_id)

    def remove_config(self, config_id: str) -> bool:
        """Removes a trail configuration by its ID.

        Configs that still have active trail instances cannot be removed.

        Args:
            config_id: The unique ID of the config to remove.

        Returns:
            True if the config was removed, False otherwise.
        """
        with self._lock:
            for instance in self._active_trails.values():
                if instance.config_id == config_id:
                    return False

            if config_id in self._trail_configs:
                del self._trail_configs[config_id]
                return True
            return False

    def list_configs(self) -> List[TrailConfig]:
        """Returns all registered trail configurations.

        Returns:
            A list of TrailConfig objects.
        """
        with self._lock:
            return list(self._trail_configs.values())

    # ------------------------------------------------------------------
    # Public API: Trail instance management
    # ------------------------------------------------------------------

    def attach_trail(
        self,
        object_id: str,
        config_id: str,
    ) -> Optional[TrailInstance]:
        """Attaches a trail effect to a game object.

        Creates a new TrailInstance from the given config and binds it to
        the specified object. The trail will begin recording points on
        subsequent calls to add_point().

        Args:
            object_id: The game object to attach the trail to.
            config_id: The trail configuration ID to use.

        Returns:
            The created TrailInstance, or None if the config doesn't exist
            or the instance limit has been reached.
        """
        with self._lock:
            config = self._trail_configs.get(config_id)
            if config is None:
                return None

            if len(self._active_trails) >= self._DEFAULT_MAX_TRAIL_INSTANCES:
                return None

            instance = self._acquire_instance()
            instance.config_id = config_id
            instance.object_id = object_id
            instance.id = uuid.uuid4().hex

            self._active_trails[instance.id] = instance
            self._stats["total_instances_spawned"] += 1
            return instance

    def detach_trail(self, instance_id: str) -> bool:
        """Deactivates a trail instance so it fades out naturally.

        The trail stops emitting new points but existing points continue
        to fade according to the config's fade mode. Once all points have
        faded, the instance is removed during the next update() cycle.

        Args:
            instance_id: The unique ID of the trail instance to detach.

        Returns:
            True if the instance was found and deactivated, False otherwise.
        """
        with self._lock:
            instance = self._active_trails.get(instance_id)
            if instance is None:
                return False
            instance.active = False
            return True

    def remove_trail(self, instance_id: str) -> bool:
        """Immediately removes a trail instance and all its points.

        Unlike detach_trail(), this removes the trail instantly without
        any fade-out animation. The instance is returned to the pool.

        Args:
            instance_id: The unique ID of the trail instance to remove.

        Returns:
            True if the instance was found and removed, False otherwise.
        """
        with self._lock:
            instance = self._active_trails.pop(instance_id, None)
            if instance is None:
                return False
            self._release_instance(instance)
            return True

    def get_trail(self, instance_id: str) -> Optional[TrailInstance]:
        """Retrieves an active trail instance by its ID.

        Args:
            instance_id: The unique ID of the trail instance.

        Returns:
            The TrailInstance if found and active, None otherwise.
        """
        with self._lock:
            return self._active_trails.get(instance_id)

    def get_trails_for_object(self, object_id: str) -> List[TrailInstance]:
        """Returns all active trail instances attached to a given object.

        Args:
            object_id: The game object ID to query.

        Returns:
            A list of TrailInstances attached to the specified object.
        """
        with self._lock:
            return [
                inst
                for inst in self._active_trails.values()
                if inst.object_id == object_id
            ]

    # ------------------------------------------------------------------
    # Public API: Point emission
    # ------------------------------------------------------------------

    def add_point(
        self,
        instance_id: str,
        position: Tuple[float, float, float],
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        size: float = 1.0,
    ) -> bool:
        """Records a position sample on an active trail.

        Called each frame (or at the config's emission rate) to add a new
        TrailPoint to the trail. Points are appended to the end of the
        point list and culled if the max_points budget is exceeded.

        Args:
            instance_id: The trail instance to add a point to.
            position: World-space position of the new point.
            velocity: Instantaneous velocity at this position.
            size: Base size multiplier for this point.

        Returns:
            True if the point was added, False if the instance doesn't
            exist or is not active.
        """
        with self._lock:
            instance = self._active_trails.get(instance_id)
            if instance is None:
                return False
            if not instance.active:
                return False

            point = TrailPoint(
                position=position,
                velocity=velocity,
                size=size,
            )
            instance.points.append(point)
            self._stats["total_points_emitted"] += 1

            config = self._trail_configs.get(instance.config_id)
            if config is not None:
                instance.points = self._cull_excess_points(
                    instance.points, config.max_points
                )

            return True

    # ------------------------------------------------------------------
    # Public API: Update loop
    # ------------------------------------------------------------------

    def update(self, delta_time: float) -> None:
        """Advances all active trails by one simulation step.

        Performs the per-frame trail lifecycle: fades points using each
        trail's fade mode, culls fully faded points, removes expired
        trail instances, and updates peak statistics.

        Args:
            delta_time: Frame delta time in seconds.
        """
        with self._lock:
            expired_instances: List[str] = []

            for instance_id, instance in self._active_trails.items():
                instance.lifetime += delta_time

                if instance.active:
                    instance.time_since_last_emit += delta_time
                else:
                    instance.time_since_last_emit = 0.0

                config = self._trail_configs.get(instance.config_id)
                if config is None:
                    expired_instances.append(instance_id)
                    continue

                instance.points = self._apply_fade(
                    instance.points,
                    config.fade_mode,
                    config.fade_duration,
                )

                if instance.is_expired:
                    expired_instances.append(instance_id)

            for instance_id in expired_instances:
                instance = self._active_trails.pop(instance_id, None)
                if instance is not None:
                    self._release_instance(instance)

            self._update_stats_peaks()

    # ------------------------------------------------------------------
    # Public API: Visible segments
    # ------------------------------------------------------------------

    def get_visible_segments(self) -> List[TrailSegment]:
        """Produces sorted TrailSegments for all active trails.

        Builds segments by pairing consecutive points in each trail,
        applies color and width interpolation, and returns them sorted
        by the config's sort_offset for correct rendering order.

        Returns:
            A list of TrailSegments sorted by sort_offset.
        """
        all_segments: List[Tuple[int, TrailSegment]] = []

        with self._lock:
            for instance_id, instance in self._active_trails.items():
                if instance.point_count < 2:
                    continue

                config = self._trail_configs.get(instance.config_id)
                if config is None:
                    continue

                segments = self._build_segments_for_instance(instance, config)

                for segment in segments:
                    all_segments.append((config.sort_offset, segment))

        all_segments.sort(key=lambda item: item[0])

        return [segment for _, segment in all_segments]

    def get_segment_count(self) -> int:
        """Returns the total number of renderable segments across all trails.

        Returns:
            The count of segments that would be produced by get_visible_segments().
        """
        with self._lock:
            count = 0
            for instance in self._active_trails.values():
                if instance.point_count >= 2:
                    count += instance.point_count - 1
            return count

    # ------------------------------------------------------------------
    # Public API: Lifecycle
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        """Removes all trail instances and returns them to the pool.

        Does not remove registered trail configurations — only active
        instances and their points are cleared.
        """
        with self._lock:
            for instance in list(self._active_trails.values()):
                self._release_instance(instance)
            self._active_trails.clear()

    def clear_configs(self) -> None:
        """Removes all trail configurations and active instances.

        Performs a full reset of the trail system. Active trails are
        released to the pool, and all registered configs are deleted.
        Statistics are preserved.
        """
        with self._lock:
            self.clear_all()
            self._trail_configs.clear()

    def reset(self) -> None:
        """Performs a complete reset of all trail renderer state.

        Clears configs, active trails, the instance pool, and resets
        all statistics to their initial values.
        """
        with self._lock:
            self._trail_configs.clear()
            for instance in list(self._active_trails.values()):
                self._release_instance(instance)
            self._active_trails.clear()
            self._trail_pool.clear()
            self._stats = {
                "total_configs_created": 0,
                "total_instances_spawned": 0,
                "total_points_emitted": 0,
                "total_points_culled": 0,
                "total_segments_generated": 0,
                "peak_concurrent_trails": 0,
                "peak_total_points": 0,
            }

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Returns a comprehensive statistics dictionary for monitoring.

        Includes configuration counts, active trail metrics, point emission
        and culling totals, segment generation counts, pool size, and peak
        concurrent usage statistics.

        Returns:
            A dictionary with string keys and numeric values.
        """
        with self._lock:
            active_count = len(self._active_trails)
            total_points = sum(
                inst.point_count for inst in self._active_trails.values()
            )
            total_segments = self.get_segment_count()

            mode_breakdown: Dict[str, int] = {}
            for instance in self._active_trails.values():
                config = self._trail_configs.get(instance.config_id)
                if config is not None:
                    mode_name = config.mode.value
                    mode_breakdown[mode_name] = (
                        mode_breakdown.get(mode_name, 0) + 1
                    )

            material_breakdown: Dict[str, int] = {}
            for instance in self._active_trails.values():
                config = self._trail_configs.get(instance.config_id)
                if config is not None:
                    mat_name = config.material.value
                    material_breakdown[mat_name] = (
                        material_breakdown.get(mat_name, 0) + 1
                    )

            avg_points_per_trail = 0.0
            if active_count > 0:
                avg_points_per_trail = total_points / active_count

            return {
                "config_count": len(self._trail_configs),
                "active_trail_count": active_count,
                "pool_size": len(self._trail_pool),
                "total_points_active": total_points,
                "total_segments_active": total_segments,
                "avg_points_per_trail": round(avg_points_per_trail, 2),
                "total_configs_created": self._stats["total_configs_created"],
                "total_instances_spawned": self._stats["total_instances_spawned"],
                "total_points_emitted": self._stats["total_points_emitted"],
                "total_points_culled": self._stats["total_points_culled"],
                "total_segments_generated": self._stats["total_segments_generated"],
                "peak_concurrent_trails": self._stats["peak_concurrent_trails"],
                "peak_total_points": self._stats["peak_total_points"],
                "mode_breakdown": mode_breakdown,
                "material_breakdown": material_breakdown,
                "max_trail_instances": self._DEFAULT_MAX_TRAIL_INSTANCES,
                "max_total_points": self._DEFAULT_MAX_TOTAL_POINTS,
            }

    # ------------------------------------------------------------------
    # Public API: Pool management
    # ------------------------------------------------------------------

    def preallocate_pool(self, count: int) -> None:
        """Pre-creates TrailInstance objects in the pool for reuse.

        Pre-warming the pool avoids allocation overhead during gameplay
        when trails are spawned and destroyed frequently.

        Args:
            count: Number of instances to preallocate.
        """
        with self._lock:
            for _ in range(count):
                instance = TrailInstance()
                instance.active = False
                self._trail_pool.append(instance)

    def get_pool_size(self) -> int:
        """Returns the current number of recycled instances in the pool.

        Returns:
            The pool size.
        """
        with self._lock:
            return len(self._trail_pool)

    # ------------------------------------------------------------------
    # Public API: Emission helpers
    # ------------------------------------------------------------------

    def should_emit(self, instance_id: str, delta_time: float) -> bool:
        """Checks whether a trail instance should emit a point this frame.

        Respects the config's emission rate to avoid oversampling. Returns
        True when enough time has accumulated since the last emission.

        Args:
            instance_id: The trail instance to check.
            delta_time: Frame delta time in seconds.

        Returns:
            True if a point should be emitted this frame.
        """
        with self._lock:
            instance = self._active_trails.get(instance_id)
            if instance is None or not instance.active:
                return False

            config = self._trail_configs.get(instance.config_id)
            if config is None:
                return False

            instance.time_since_last_emit += delta_time
            interval = 1.0 / config.emission_rate

            if instance.time_since_last_emit >= interval:
                instance.time_since_last_emit -= interval
                return True

            return False

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"TrailRenderer(configs={len(self._trail_configs)}, "
                f"active={len(self._active_trails)}, "
                f"pool={len(self._trail_pool)})"
            )


def get_trail_renderer() -> TrailRenderer:
    """Module-level accessor for the TrailRenderer singleton.

    Convenience function that returns the singleton instance without
    needing to reference TrailRenderer.get_instance() directly.

    Returns:
        The singleton TrailRenderer instance.
    """
    return TrailRenderer.get_instance()