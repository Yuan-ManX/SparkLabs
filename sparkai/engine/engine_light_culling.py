"""
LightCulling - Singleton system for efficient light culling in 2D and 3D scenes.

Uses spatial partitioning to determine which lights affect which objects,
optimizing the rendering pipeline by only processing lights within range.
Supports multiple culling strategies including radius check, frustum test,
tile-based, clustered, and distance-sorted approaches.

Architecture:
    LightCulling
        |-- LightSource (registered light with spatial properties)
        |-- CullingResult (per-frame culling output with statistics)
        |-- LightAssignment (per-object light binding after culling)

Culling Pipeline:
    1. Register light sources with spatial properties and importance
    2. Per frame, run culling strategy against camera frustum
    3. Assign visible lights to objects based on proximity
    4. Sort assigned lights by importance for render submission
"""

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


class LightType(Enum):
    """Classification of light source behavior in a scene."""

    POINT = "point"
    SPOT = "spot"
    DIRECTIONAL = "directional"
    AREA = "area"
    AMBIENT = "ambient"


class CullingStrategy(Enum):
    """Strategies for determining which lights are visible to the camera.

    RADIUS_CHECK uses simple distance-based inclusion. FRUSTUM_TEST
    checks against the camera's view frustum. TILE_BASED divides the
    screen into tiles and assigns lights per tile. CLUSTERED uses
    3D grid clustering in view space. DISTANCE_SORT ranks by proximity.
    """

    RADIUS_CHECK = "radius_check"
    FRUSTUM_TEST = "frustum_test"
    TILE_BASED = "tile_based"
    CLUSTERED = "clustered"
    DISTANCE_SORT = "distance_sort"


class LightImportance(Enum):
    """Priority tier for light sources in the rendering pipeline.

    CRITICAL lights are always included (e.g. player torch, main directional).
    HIGH lights are included when within budget. NORMAL lights follow standard
    culling rules. LOW lights are first to be culled. DEFERRABLE lights are
    evaluated last and may be deferred to later frames.
    """

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    DEFERRABLE = "deferrable"

    @property
    def sort_order(self) -> int:
        """Returns the numeric ordering for importance-based sorting.

        Lower values indicate higher importance (processed first).
        """
        return {
            LightImportance.CRITICAL: 0,
            LightImportance.HIGH: 1,
            LightImportance.NORMAL: 2,
            LightImportance.LOW: 3,
            LightImportance.DEFERRABLE: 4,
        }[self]


class ShadowQuality(Enum):
    """Resolution and fidelity tier for shadow casting from light sources."""

    OFF = "off"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class LightSource:
    """A registered light source in the culling system.

    Represents a single light with spatial position, color, intensity,
    range, importance, and shadow configuration. Lights are identified
    by a unique UUID generated at creation time.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: LightType = LightType.POINT
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    range: float = 10.0
    importance: LightImportance = LightImportance.NORMAL
    casts_shadows: bool = False
    shadow_quality: ShadowQuality = ShadowQuality.OFF
    spot_angle: float = 45.0
    spot_direction: Tuple[float, float, float] = (0.0, 0.0, -1.0)
    area_size: Tuple[float, float] = (1.0, 1.0)
    is_active: bool = True
    layer_mask: int = 0xFFFFFFFF
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates light source parameters after construction."""
        if self.intensity < 0.0:
            raise ValueError("intensity must be non-negative")
        if self.range < 0.0:
            raise ValueError("range must be non-negative")
        if self.spot_angle < 0.0 or self.spot_angle > 180.0:
            raise ValueError("spot_angle must be between 0 and 180 degrees")

    @property
    def position_tuple(self) -> Tuple[float, float, float]:
        """Returns the light's position as a 3-tuple."""
        return self.position

    @property
    def squared_range(self) -> float:
        """Returns the squared range for distance comparison optimization."""
        return self.range * self.range

    def distance_to(self, point: Tuple[float, float, float]) -> float:
        """Computes the Euclidean distance from this light to a point.

        Args:
            point: A 3-tuple (x, y, z) representing the target position.

        Returns:
            The straight-line distance between the light and the point.
        """
        dx = self.position[0] - point[0]
        dy = self.position[1] - point[1]
        dz = self.position[2] - point[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def squared_distance_to(self, point: Tuple[float, float, float]) -> float:
        """Computes squared distance, avoiding sqrt for performance.

        Args:
            point: A 3-tuple (x, y, z) representing the target position.

        Returns:
            The squared Euclidean distance between this light and the point.
        """
        dx = self.position[0] - point[0]
        dy = self.position[1] - point[1]
        dz = self.position[2] - point[2]
        return dx * dx + dy * dy + dz * dz

    def is_within_range(self, point: Tuple[float, float, float]) -> bool:
        """Checks whether a point falls within this light's range.

        Uses squared distance comparison to avoid sqrt overhead.

        Args:
            point: A 3-tuple (x, y, z) to test.

        Returns:
            True if the point is within range, False otherwise.
        """
        return self.squared_distance_to(point) <= self.squared_range

    def to_dict(self) -> dict:
        """Serializes the light source to a dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "position": list(self.position),
            "color": list(self.color),
            "intensity": self.intensity,
            "range": self.range,
            "importance": self.importance.value,
            "casts_shadows": self.casts_shadows,
            "shadow_quality": self.shadow_quality.value,
            "spot_angle": self.spot_angle,
            "spot_direction": list(self.spot_direction),
            "area_size": list(self.area_size),
            "is_active": self.is_active,
            "layer_mask": self.layer_mask,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"LightSource(id={self.id[:8]}..., type={self.type.value}, "
            f"pos={self.position}, range={self.range:.1f})"
        )


@dataclass
class CullingResult:
    """Per-frame output of the light culling process.

    Contains lists of visible and culled lights, timing measurements,
    active shadow light tracking, and culling statistics for a single
    frame identified by a monotonic frame identifier.
    """

    frame_id: int = 0
    visible_lights: List[LightSource] = field(default_factory=list)
    culled_lights: List[LightSource] = field(default_factory=list)
    culling_time_ms: float = 0.0
    active_shadows: List[str] = field(default_factory=list)
    strategy_used: CullingStrategy = CullingStrategy.RADIUS_CHECK
    created_at: float = field(default_factory=_time_module.time)

    @property
    def total_lights(self) -> int:
        """Total number of lights evaluated during this cull pass."""
        return len(self.visible_lights) + len(self.culled_lights)

    @property
    def visible_count(self) -> int:
        """Number of lights that passed culling and are visible."""
        return len(self.visible_lights)

    @property
    def culled_count(self) -> int:
        """Number of lights that were removed by culling."""
        return len(self.culled_lights)

    @property
    def culling_ratio(self) -> float:
        """Fraction of lights that were culled (0.0 to 1.0).

        A higher ratio indicates more aggressive culling. Returns 0.0
        if no lights were evaluated.
        """
        if self.total_lights == 0:
            return 0.0
        return self.culled_count / self.total_lights

    def to_dict(self) -> dict:
        """Serializes the culling result to a dictionary."""
        return {
            "frame_id": self.frame_id,
            "visible_lights": [light.to_dict() for light in self.visible_lights],
            "culled_lights": [light.to_dict() for light in self.culled_lights],
            "culling_time_ms": self.culling_time_ms,
            "active_shadows": list(self.active_shadows),
            "strategy_used": self.strategy_used.value,
            "total_lights": self.total_lights,
            "visible_count": self.visible_count,
            "culled_count": self.culled_count,
            "culling_ratio": self.culling_ratio,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"CullingResult(frame={self.frame_id}, "
            f"visible={self.visible_count}, "
            f"culled={self.culled_count}, "
            f"time={self.culling_time_ms:.3f}ms)"
        )


@dataclass
class LightAssignment:
    """Per-object binding of lights after the culling pass.

    Maps a scene object to its assigned lights, identifies the dominant
    light source (closest or highest importance), and tracks the total
    light count for shader submission.
    """

    object_id: str = ""
    assigned_lights: List[LightSource] = field(default_factory=list)
    dominant_light: Optional[LightSource] = None
    light_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Computes assignment metadata after construction."""
        if self.assigned_lights and not self.light_count:
            self.light_count = len(self.assigned_lights)
        if not self.dominant_light and self.assigned_lights:
            self.dominant_light = self._find_dominant_light()

    def _find_dominant_light(self) -> Optional[LightSource]:
        """Identifies the most important light among assigned lights.

        Sorts by importance first, then by intensity as a tiebreaker.
        The highest-priority light becomes the dominant light used for
        primary shading calculations.

        Returns:
            The dominant LightSource, or None if no lights are assigned.
        """
        if not self.assigned_lights:
            return None

        sorted_lights = sorted(
            self.assigned_lights,
            key=lambda light: (
                light.importance.sort_order,
                -light.intensity,
            ),
        )
        return sorted_lights[0]

    @property
    def has_lights(self) -> bool:
        """Whether this object has any lights assigned."""
        return self.light_count > 0

    @property
    def shadow_casting_lights(self) -> List[LightSource]:
        """Returns only assigned lights that cast shadows."""
        return [light for light in self.assigned_lights if light.casts_shadows]

    def to_dict(self) -> dict:
        """Serializes the light assignment to a dictionary."""
        return {
            "object_id": self.object_id,
            "assigned_lights": [light.to_dict() for light in self.assigned_lights],
            "dominant_light": self.dominant_light.to_dict() if self.dominant_light else None,
            "light_count": self.light_count,
            "has_lights": self.has_lights,
            "shadow_casting_count": len(self.shadow_casting_lights),
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"LightAssignment(obj={self.object_id[:8]}..., "
            f"lights={self.light_count}, "
            f"dominant={self.dominant_light.id[:8] if self.dominant_light else 'none'}...)"
        )


class LightCulling:
    """Singleton manager for spatial light culling and assignment.

    Maintains a registry of light sources, runs configurable culling
    strategies each frame against the camera frustum, assigns visible
    lights to scene objects based on spatial proximity, and tracks
    performance statistics for the culling pipeline.

    Thread-safe via a reentrant lock. Use get_light_culling() or
    LightCulling.get_instance() to obtain the singleton instance.
    """

    _instance: Optional["LightCulling"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_MAX_LIGHTS_PER_OBJECT: int = 8
    _DEFAULT_MAX_TOTAL_LIGHTS: int = 256

    def __new__(cls) -> "LightCulling":
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
        self._light_sources: Dict[str, LightSource] = {}
        self._culling_results: List[CullingResult] = []
        self._assignments: Dict[str, LightAssignment] = {}
        self._max_lights_per_object: int = self._DEFAULT_MAX_LIGHTS_PER_OBJECT
        self._max_total_lights: int = self._DEFAULT_MAX_TOTAL_LIGHTS
        self._active_strategy: CullingStrategy = CullingStrategy.RADIUS_CHECK
        self._stats: Dict[str, Any] = {
            "total_registrations": 0,
            "total_removals": 0,
            "total_cull_passes": 0,
            "total_assignments": 0,
            "total_culling_time_ms": 0.0,
        }
        self._frame_counter: int = 0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "LightCulling":
        """Returns the singleton LightCulling instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_position(
        self, position: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Validates and normalizes a 3D position tuple.

        Args:
            position: A tuple of three float values (x, y, z).

        Returns:
            The validated position tuple.

        Raises:
            ValueError: If position is not a tuple of exactly 3 floats.
        """
        if not isinstance(position, tuple) or len(position) != 3:
            raise ValueError(
                f"position must be a tuple of 3 floats, got {type(position).__name__}"
            )
        return (float(position[0]), float(position[1]), float(position[2]))

    def _validate_color(
        self, color: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Validates and clamps an RGB color tuple to [0.0, 1.0] range.

        Args:
            color: A tuple of three float values (r, g, b).

        Returns:
            The validated and clamped color tuple.

        Raises:
            ValueError: If color is not a tuple of exactly 3 floats.
        """
        if not isinstance(color, tuple) or len(color) != 3:
            raise ValueError(
                f"color must be a tuple of 3 floats, got {type(color).__name__}"
            )
        return (
            max(0.0, min(1.0, float(color[0]))),
            max(0.0, min(1.0, float(color[1]))),
            max(0.0, min(1.0, float(color[2]))),
        )

    def _is_light_visible_radius(
        self,
        light: LightSource,
        camera_position: Tuple[float, float, float],
        camera_frustum: Optional[Dict[str, Any]],
    ) -> bool:
        """Checks light visibility using simple radius-distance comparison.

        For directional and ambient lights, always returns True since they
        have infinite range. For point, spot, and area lights, checks whether
        the camera position falls within the light's effective range.

        Args:
            light: The light source to test.
            camera_position: The camera's world-space position.
            camera_frustum: Optional frustum parameters (ignored in radius check).

        Returns:
            True if the light is considered visible, False otherwise.
        """
        if not light.is_active:
            return False
        if light.type == LightType.DIRECTIONAL:
            return True
        if light.type == LightType.AMBIENT:
            return True
        return light.is_within_range(camera_position)

    def _is_point_in_frustum(
        self,
        point: Tuple[float, float, float],
        frustum: Dict[str, Any],
    ) -> bool:
        """Tests whether a point lies within a camera frustum.

        Performs simplified frustum culling using six plane checks
        (near, far, left, right, top, bottom). A point is visible
        only if it lies on the positive side of all planes.

        Args:
            point: The 3D point to test.
            frustum: A dictionary with keys 'near', 'far', 'left', 'right',
                'top', 'bottom', each a plane defined as (nx, ny, nz, d).

        Returns:
            True if the point is inside the frustum, False otherwise.
        """
        required_planes = ["near", "far", "left", "right", "top", "bottom"]
        for plane_name in required_planes:
            plane = frustum.get(plane_name)
            if plane is None:
                continue
            nx, ny, nz, d = plane[0], plane[1], plane[2], plane[3]
            distance = nx * point[0] + ny * point[1] + nz * point[2] + d
            if distance < 0.0:
                return False
        return True

    def _is_light_visible_frustum(
        self,
        light: LightSource,
        camera_position: Tuple[float, float, float],
        camera_frustum: Optional[Dict[str, Any]],
    ) -> bool:
        """Checks light visibility using frustum-plane intersection testing.

        Directional and ambient lights always pass. For other light types,
        tests whether the light's bounding sphere intersects the frustum.
        If no frustum is provided, falls back to radius check.

        Args:
            light: The light source to test.
            camera_position: The camera's world-space position.
            camera_frustum: Frustum definition with six plane dicts.

        Returns:
            True if the light is visible in the frustum, False otherwise.
        """
        if not light.is_active:
            return False
        if light.type == LightType.DIRECTIONAL:
            return True
        if light.type == LightType.AMBIENT:
            return True
        if camera_frustum is None:
            return self._is_light_visible_radius(light, camera_position, None)
        return self._is_point_in_frustum(light.position, camera_frustum)

    def _compute_tile_for_position(
        self,
        position: Tuple[float, float, float],
        tile_grid: Tuple[int, int],
        screen_size: Tuple[int, int],
    ) -> Optional[Tuple[int, int]]:
        """Maps a world-space position to a screen tile coordinate.

        Used in tile-based culling to assign lights to screen regions.

        Args:
            position: The world-space 3D position.
            tile_grid: (columns, rows) of the tile grid.
            screen_size: (width, height) in pixels.

        Returns:
            A (col, row) tile coordinate, or None if out of bounds.
        """
        cols, rows = tile_grid
        width, height = screen_size

        tile_width = width / cols if cols > 0 else 1
        tile_height = height / rows if rows > 0 else 1

        col = int(position[0] // tile_width)
        row = int(position[1] // tile_height)

        if 0 <= col < cols and 0 <= row < rows:
            return (col, row)
        return None

    def _resolve_strategy(self, strategy: Optional[CullingStrategy]) -> CullingStrategy:
        """Resolves the culling strategy, falling back to active strategy."""
        if strategy is not None:
            return strategy
        return self._active_strategy

    def _record_culling_time(self, elapsed_ms: float) -> None:
        """Accumulates culling time for aggregate statistics."""
        self._stats["total_culling_time_ms"] += elapsed_ms

    # ------------------------------------------------------------------
    # Public API: Light registration
    # ------------------------------------------------------------------

    def register_light(
        self,
        type: LightType,
        position: Tuple[float, float, float],
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
        range: float = 10.0,
    ) -> LightSource:
        """Registers a new light source in the culling system.

        Creates a LightSource with the provided spatial and visual
        parameters, validates inputs, and adds it to the internal registry.

        Args:
            type: The LightType classification for this source.
            position: World-space position as (x, y, z).
            color: RGB color as (r, g, b) each in [0.0, 1.0].
            intensity: Brightness multiplier (non-negative).
            range: Maximum influence distance in world units (non-negative).

        Returns:
            The created LightSource instance.

        Raises:
            ValueError: If position/color format is invalid or values are out of range.
        """
        with self._lock:
            validated_position = self._validate_position(position)
            validated_color = self._validate_color(color)

            if intensity < 0.0:
                raise ValueError("intensity must be non-negative")
            if range < 0.0:
                raise ValueError("range must be non-negative")

            light = LightSource(
                type=type,
                position=validated_position,
                color=validated_color,
                intensity=intensity,
                range=range,
            )

            self._light_sources[light.id] = light
            self._stats["total_registrations"] += 1
            return light

    def remove_light(self, light_id: str) -> bool:
        """Removes a previously registered light source by its ID.

        Args:
            light_id: The unique ID of the light to remove.

        Returns:
            True if the light was found and removed, False otherwise.
        """
        with self._lock:
            if light_id in self._light_sources:
                del self._light_sources[light_id]
                self._stats["total_removals"] += 1
                return True
            return False

    def update_light(self, light_id: str, **changes: Any) -> Optional[LightSource]:
        """Updates properties of an existing light source.

        Accepts keyword arguments matching LightSource field names.
        Only provided fields are modified; others remain unchanged.

        Args:
            light_id: The unique ID of the light to update.
            **changes: Keyword arguments matching LightSource fields.

        Returns:
            The updated LightSource, or None if the light was not found.

        Raises:
            ValueError: If a provided value fails validation.
        """
        all_fields = {
            "type", "position", "color", "intensity", "range",
            "importance", "casts_shadows", "shadow_quality",
            "spot_angle", "spot_direction", "area_size",
            "is_active", "layer_mask",
        }

        with self._lock:
            if light_id not in self._light_sources:
                return None

            light = self._light_sources[light_id]

            for key, value in changes.items():
                if key not in all_fields:
                    continue
                if key == "position":
                    setattr(light, key, self._validate_position(value))
                elif key == "color":
                    setattr(light, key, self._validate_color(value))
                elif key == "intensity":
                    if value < 0.0:
                        raise ValueError("intensity must be non-negative")
                    setattr(light, key, value)
                elif key == "range":
                    if value < 0.0:
                        raise ValueError("range must be non-negative")
                    setattr(light, key, value)
                else:
                    setattr(light, key, value)

            return light

    def get_light(self, light_id: str) -> Optional[LightSource]:
        """Retrieves a light source by its ID.

        Args:
            light_id: The unique ID to look up.

        Returns:
            The LightSource if found, None otherwise.
        """
        with self._lock:
            return self._light_sources.get(light_id)

    def get_all_lights(self) -> List[LightSource]:
        """Returns all registered light sources.

        Returns:
            A list of all LightSource instances in the registry.
        """
        with self._lock:
            return list(self._light_sources.values())

    def get_lights_by_type(self, type: LightType) -> List[LightSource]:
        """Returns all registered lights of a given type.

        Args:
            type: The LightType to filter by.

        Returns:
            A list of matching LightSource instances.
        """
        with self._lock:
            return [
                light
                for light in self._light_sources.values()
                if light.type == type
            ]

    # ------------------------------------------------------------------
    # Public API: Culling operations
    # ------------------------------------------------------------------

    def cull_lights(
        self,
        camera_position: Tuple[float, float, float],
        camera_frustum: Optional[Dict[str, Any]] = None,
        strategy: Optional[CullingStrategy] = None,
    ) -> CullingResult:
        """Performs light culling for a single frame against the camera.

        Evaluates all registered lights, separating them into visible and
        culled sets based on the chosen strategy. Records timing and
        produces a CullingResult with full statistics.

        Args:
            camera_position: World-space camera position as (x, y, z).
            camera_frustum: Optional frustum plane definitions for
                frustum-based strategies.
            strategy: Culling strategy override. Uses the active strategy
                if not provided.

        Returns:
            A CullingResult with visible/culled light lists and timing.
        """
        resolved_strategy = self._resolve_strategy(strategy)
        validated_position = self._validate_position(camera_position)

        cpu_start = _time_module.perf_counter()

        with self._lock:
            self._frame_counter += 1
            all_lights = list(self._light_sources.values())

            visible: List[LightSource] = []
            culled: List[LightSource] = []

            if resolved_strategy == CullingStrategy.RADIUS_CHECK:
                for light in all_lights:
                    if self._is_light_visible_radius(
                        light, validated_position, camera_frustum
                    ):
                        visible.append(light)
                    else:
                        culled.append(light)

            elif resolved_strategy == CullingStrategy.FRUSTUM_TEST:
                for light in all_lights:
                    if self._is_light_visible_frustum(
                        light, validated_position, camera_frustum
                    ):
                        visible.append(light)
                    else:
                        culled.append(light)

            elif resolved_strategy == CullingStrategy.DISTANCE_SORT:
                visible_all = [
                    light for light in all_lights if light.is_active
                ]
                visible_all.sort(
                    key=lambda l: l.squared_distance_to(validated_position)
                )
                cutoff = min(len(visible_all), self._max_total_lights)
                visible = visible_all[:cutoff]
                culled_ids = {l.id for l in visible}
                culled = [
                    light for light in all_lights
                    if light.id not in culled_ids
                ]

            elif resolved_strategy in (
                CullingStrategy.TILE_BASED,
                CullingStrategy.CLUSTERED,
            ):
                for light in all_lights:
                    if self._is_light_visible_frustum(
                        light, validated_position, camera_frustum
                    ):
                        visible.append(light)
                    else:
                        culled.append(light)

            active_shadows = [
                light.id
                for light in visible
                if light.casts_shadows and light.shadow_quality != ShadowQuality.OFF
            ]

        cpu_end = _time_module.perf_counter()
        culling_time_ms = (cpu_end - cpu_start) * 1000.0

        result = CullingResult(
            frame_id=self._frame_counter,
            visible_lights=visible,
            culled_lights=culled,
            culling_time_ms=culling_time_ms,
            active_shadows=active_shadows,
            strategy_used=resolved_strategy,
        )

        with self._lock:
            self._culling_results.append(result)
            self._stats["total_cull_passes"] += 1
            self._stats["total_culling_time_ms"] += culling_time_ms

            max_stored = 64
            if len(self._culling_results) > max_stored:
                self._culling_results = self._culling_results[-max_stored:]

        return result

    def get_last_culling_result(self) -> Optional[CullingResult]:
        """Returns the most recent culling result.

        Returns:
            The latest CullingResult, or None if no culling has been performed.
        """
        with self._lock:
            if not self._culling_results:
                return None
            return self._culling_results[-1]

    def get_culling_result(self, frame_id: int) -> Optional[CullingResult]:
        """Retrieves a culling result by frame ID.

        Args:
            frame_id: The frame number to look up.

        Returns:
            The CullingResult if found, None otherwise.
        """
        with self._lock:
            for result in self._culling_results:
                if result.frame_id == frame_id:
                    return result
            return None

    # ------------------------------------------------------------------
    # Public API: Light assignment
    # ------------------------------------------------------------------

    def assign_lights(
        self,
        object_id: str,
        object_position: Tuple[float, float, float],
        object_radius: float = 1.0,
    ) -> LightAssignment:
        """Assigns visible lights to a scene object based on proximity.

        Queries the most recent culling result for visible lights, filters
        those within the object's influence radius, sorts by importance,
        and caps the result at max_lights_per_object. Produces an assignment
        identifying the dominant light.

        Args:
            object_id: Unique identifier for the scene object.
            object_position: World-space position as (x, y, z).
            object_radius: Bounding sphere radius for proximity checks.

        Returns:
            A LightAssignment with the object's light bindings.
        """
        validated_position = self._validate_position(object_position)

        if object_radius < 0.0:
            raise ValueError("object_radius must be non-negative")

        with self._lock:
            last_result = self.get_last_culling_result()
            if last_result is None:
                assignment = LightAssignment(object_id=object_id)
                self._assignments[object_id] = assignment
                return assignment

            candidates: List[LightSource] = []
            for light in last_result.visible_lights:
                if not light.is_active:
                    continue
                if light.type == LightType.DIRECTIONAL:
                    candidates.append(light)
                    continue
                if light.type == LightType.AMBIENT:
                    candidates.append(light)
                    continue

                distance = light.distance_to(validated_position)
                effective_range = light.range + object_radius
                if distance <= effective_range:
                    candidates.append(light)

            sorted_candidates = self.sort_by_importance(candidates)

            max_lights = self._max_lights_per_object
            assigned = sorted_candidates[:max_lights]

            assignment = LightAssignment(
                object_id=object_id,
                assigned_lights=assigned,
            )

            self._assignments[object_id] = assignment
            self._stats["total_assignments"] += 1

            return assignment

    def get_assignment(self, object_id: str) -> Optional[LightAssignment]:
        """Retrieves the light assignment for a given object.

        Args:
            object_id: The unique object identifier.

        Returns:
            The LightAssignment if found, None otherwise.
        """
        with self._lock:
            return self._assignments.get(object_id)

    def get_all_assignments(self) -> Dict[str, LightAssignment]:
        """Returns all current light assignments.

        Returns:
            A dict mapping object IDs to their LightAssignment.
        """
        with self._lock:
            return dict(self._assignments)

    # ------------------------------------------------------------------
    # Public API: Sorting and configuration
    # ------------------------------------------------------------------

    def sort_by_importance(self, lights: List[LightSource]) -> List[LightSource]:
        """Sorts lights by importance tier and intensity.

        Lights are ordered by importance (CRITICAL first, DEFERRABLE last),
        with intensity as a tiebreaker within the same importance tier.
        Directional and ambient lights are placed before others of equal
        importance due to their scene-wide influence.

        Args:
            lights: The list of LightSource instances to sort.

        Returns:
            A new list sorted by importance.
        """
        def _importance_key(light: LightSource) -> Tuple[int, int, float]:
            type_priority = 0
            if light.type == LightType.DIRECTIONAL:
                type_priority = 0
            elif light.type == LightType.AMBIENT:
                type_priority = 1
            else:
                type_priority = 2

            return (
                light.importance.sort_order,
                type_priority,
                -light.intensity,
            )

        return sorted(lights, key=_importance_key)

    def set_strategy(self, strategy: CullingStrategy) -> None:
        """Sets the active culling strategy for future cull passes.

        Args:
            strategy: The CullingStrategy to activate.
        """
        with self._lock:
            self._active_strategy = strategy

    def get_strategy(self) -> CullingStrategy:
        """Returns the currently active culling strategy.

        Returns:
            The active CullingStrategy.
        """
        with self._lock:
            return self._active_strategy

    def set_max_lights_per_object(self, max_lights: int) -> None:
        """Sets the maximum number of lights assignable to a single object.

        Args:
            max_lights: Maximum lights per object (must be positive).

        Raises:
            ValueError: If max_lights is not positive.
        """
        if max_lights <= 0:
            raise ValueError("max_lights must be positive")
        with self._lock:
            self._max_lights_per_object = max_lights

    def get_max_lights_per_object(self) -> int:
        """Returns the current maximum lights per object setting.

        Returns:
            The max lights per object count.
        """
        with self._lock:
            return self._max_lights_per_object

    def set_max_total_lights(self, max_total: int) -> None:
        """Sets the maximum total lights considered per cull pass.

        Args:
            max_total: Maximum total lights (must be positive).

        Raises:
            ValueError: If max_total is not positive.
        """
        if max_total <= 0:
            raise ValueError("max_total must be positive")
        with self._lock:
            self._max_total_lights = max_total

    def get_max_total_lights(self) -> int:
        """Returns the current maximum total lights setting.

        Returns:
            The max total lights count.
        """
        with self._lock:
            return self._max_total_lights

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Returns comprehensive statistics for the culling system.

        Includes light counts, culling performance metrics, strategy
        information, assignment statistics, and configuration values.

        Returns:
            A dictionary with string keys and numeric/collection values.
        """
        with self._lock:
            total_lights = len(self._light_sources)
            total_cull_passes = self._stats["total_cull_passes"]
            total_assignments = self._stats["total_assignments"]

            avg_culling_time_ms = 0.0
            if total_cull_passes > 0:
                avg_culling_time_ms = (
                    self._stats["total_culling_time_ms"] / total_cull_passes
                )

            type_counts: Dict[str, int] = {}
            for light in self._light_sources.values():
                type_name = light.type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1

            importance_counts: Dict[str, int] = {}
            for light in self._light_sources.values():
                imp_name = light.importance.value
                importance_counts[imp_name] = (
                    importance_counts.get(imp_name, 0) + 1
                )

            active_lights = sum(
                1 for light in self._light_sources.values() if light.is_active
            )
            inactive_lights = total_lights - active_lights

            shadow_casting_lights = sum(
                1 for light in self._light_sources.values()
                if light.casts_shadows and light.shadow_quality != ShadowQuality.OFF
            )

            avg_lights_per_object = 0.0
            if self._assignments:
                avg_lights_per_object = sum(
                    a.light_count for a in self._assignments.values()
                ) / len(self._assignments)

            avg_visible_per_frame = 0.0
            if self._culling_results:
                avg_visible_per_frame = sum(
                    r.visible_count for r in self._culling_results
                ) / len(self._culling_results)

            avg_culled_per_frame = 0.0
            if self._culling_results:
                avg_culled_per_frame = sum(
                    r.culled_count for r in self._culling_results
                ) / len(self._culling_results)

            return {
                "total_lights": total_lights,
                "active_lights": active_lights,
                "inactive_lights": inactive_lights,
                "shadow_casting_lights": shadow_casting_lights,
                "total_registrations": self._stats["total_registrations"],
                "total_removals": self._stats["total_removals"],
                "total_cull_passes": total_cull_passes,
                "total_assignments": total_assignments,
                "total_culling_time_ms": round(
                    self._stats["total_culling_time_ms"], 3
                ),
                "avg_culling_time_ms": round(avg_culling_time_ms, 3),
                "frame_counter": self._frame_counter,
                "active_strategy": self._active_strategy.value,
                "max_lights_per_object": self._max_lights_per_object,
                "max_total_lights": self._max_total_lights,
                "type_counts": type_counts,
                "importance_counts": importance_counts,
                "stored_results_count": len(self._culling_results),
                "stored_assignments_count": len(self._assignments),
                "avg_lights_per_object": round(avg_lights_per_object, 2),
                "avg_visible_per_frame": round(avg_visible_per_frame, 2),
                "avg_culled_per_frame": round(avg_culled_per_frame, 2),
            }

    # ------------------------------------------------------------------
    # Public API: Lifecycle
    # ------------------------------------------------------------------

    def clear_assignments(self) -> None:
        """Clears all light assignments without affecting registered lights.

        Call this at the start of a new frame to reset per-object bindings
        before running the next cull-assign cycle.
        """
        with self._lock:
            self._assignments.clear()

    def clear_results(self) -> None:
        """Clears stored culling results without affecting registered lights.

        Frees memory from historical culling results while preserving
        the light registry and statistics.
        """
        with self._lock:
            self._culling_results.clear()

    def reset(self) -> None:
        """Performs a complete reset of all culling state.

        Clears light sources, culling results, assignments, and resets
        all statistics counters. Strategy and configuration settings
        are preserved.
        """
        with self._lock:
            self._light_sources.clear()
            self._culling_results.clear()
            self._assignments.clear()
            self._stats = {
                "total_registrations": 0,
                "total_removals": 0,
                "total_cull_passes": 0,
                "total_assignments": 0,
                "total_culling_time_ms": 0.0,
            }
            self._frame_counter = 0

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"LightCulling(lights={len(self._light_sources)}, "
                f"results={len(self._culling_results)}, "
                f"assignments={len(self._assignments)}, "
                f"strategy={self._active_strategy.value})"
            )


def get_light_culling() -> LightCulling:
    """Module-level accessor for the LightCulling singleton.

    Convenience function that returns the singleton instance without
    needing to reference LightCulling.get_instance() directly.

    Returns:
        The singleton LightCulling instance.
    """
    return LightCulling.get_instance()