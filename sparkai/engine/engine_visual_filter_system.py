"""
SparkLabs Engine - Visual Filter System

Manages real-time visual filters and color grading presets that can be
applied to the game viewport, screenshot pipeline, cutscenes, and photo
mode. The system owns a registry of filter presets (each a bundle of
typed parameters such as brightness, contrast, saturation, grain, and
vignette), filter stacks that compose multiple presets per render
target, LUT assets used for color grading, capture records that prove a
filter was applied to a frame, smooth transitions between presets,
side-by-side parameter comparisons, and an audit trail of every
lifecycle event.

An integrated AI layer can generate a complete filter preset from a
natural-language description ("dark and moody horror", "bright cheerful
cartoon", "retro 80s synthwave"), suggest which parameters a designer
should adjust next for a given preset, and optimize an existing filter
for a target frame rate by reducing the cost of expensive effects.

Architecture:
  VisualFilterSystem (singleton)
    |-- FilterPresetType, FilterParameter, FilterCategory, FilterBlendMode,
       FilterQuality, FilterStatus, FilterLUTFormat, FilterTarget,
       VisualFilterEventKind
    |-- FilterParameterEntry, FilterPreset, FilterStack, FilterLUT,
       FilterCapture, VisualFilterConfig, VisualFilterStats,
       VisualFilterSnapshot, VisualFilterEvent, FilterTransition,
       FilterComparison
    |-- get_visual_filter_system

Core Capabilities:
  - register_preset / get_preset / list_presets / remove_preset /
    update_preset: filter preset registry management with FIFO eviction.
  - set_parameter / get_parameter / reset_parameter: per-preset typed
    parameter management with min/max clamping and default fallback.
  - create_stack / get_stack / list_stacks / remove_stack /
    add_preset_to_stack / remove_preset_from_stack / activate_stack /
    deactivate_stack: compose ordered preset stacks per render target.
  - register_lut / get_lut / list_luts / remove_lut: color grading LUT
    asset registry.
  - apply_filter / revert_filter / capture_filtered: apply a preset to a
    target, revert the active filter, and capture a filtered frame.
  - create_transition / get_transition / update_transition /
    remove_transition: smooth interpolated transitions between presets.
  - compare_presets: compute parameter deltas across two or more presets.
  - export_preset / import_preset: JSON serialization round-trip.
  - auto_generate_filter: AI-driven filter generation from a
    natural-language description (horror, vibrant, retro, dreamy,
    watercolor, cinematic, noir, vintage, cyberpunk, pastel, warm, cool).
  - suggest_parameters: AI-driven parameter suggestion that inspects a
    preset and proposes the next parameters a designer should tune.
  - optimize_filter: AI-driven optimization that reduces expensive
    effects so the filter meets a target frame rate.
  - get_status / get_stats / get_snapshot / get_config / set_config /
    tick / reset / list_events: observability, tuning, and lifecycle.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`VisualFilterSystem.get_instance` or the module-level
:func:`get_visual_filter_system` factory. All public methods are guarded
by the re-entrant lock.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry
# is evicted in FIFO order to keep memory growth predictable under heavy
# dynamic use (for example a game that swaps filters every frame during a
# cutscene or registers a fresh capture for every screenshot).
_MAX_FILTERS: int = 2000
_MAX_STACKS: int = 500
_MAX_LUTS: int = 1000
_MAX_CAPTURES: int = 5000
_MAX_TRANSITIONS: int = 500
_MAX_COMPARISONS: int = 1000
_MAX_EVENTS: int = 10000

# Numeric bounds for common parameters.
_INTENSITY_MIN: float = 0.0
_INTENSITY_MAX: float = 2.0
_BLEND_STRENGTH_MIN: float = 0.0
_BLEND_STRENGTH_MAX: float = 2.0
_SORT_ORDER_MIN: float = -1000.0
_SORT_ORDER_MAX: float = 1000.0

# List limits.
_DEFAULT_LIST_LIMIT: int = 100
_MAX_LIST_LIMIT: int = 500


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Used as the default factory for ``created_at`` / ``updated_at`` fields
    and for event timestamps throughout the module.
    """
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with an
            underscore. When omitted the bare hexadecimal id is returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits ``max_size``.

    Uses insertion-order iteration so the first inserted key is dropped
    first. This keeps memory growth bounded for FIFO-style stores.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits ``max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to ``default``.

    Accepts either an existing enum member or its raw value. Returns
    ``default`` when the value cannot be resolved.
    """
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into a JSON-serializable form.

    Handles enums (by value), dicts, lists, tuples, sets, dataclasses
    (via ``__dataclass_fields__``), and objects exposing ``to_dict``.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance into a dict of JSON-serializable values.

    Checks ``__dataclass_fields__`` BEFORE ``to_dict`` to avoid recursion
    when a dataclass also defines a ``to_dict`` method that delegates back
    to this helper.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to the inclusive ``[low, high]`` range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning ``default`` on failure."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int, returning ``default`` on failure."""
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FilterPresetType(str, Enum):
    """Classification of a visual filter preset by its stylistic family.

    Each value names a canonical look that the system can seed with
    sensible default parameters. CUSTOM is used for presets that do not
    fit any of the named families.
    """

    CINEMATIC = "cinematic"
    NOIR = "noir"
    VINTAGE = "vintage"
    VIBRANT = "vibrant"
    DREAMY = "dreamy"
    HORROR = "horror"
    RETRO = "retro"
    WATERCOLOR = "watercolor"
    SEPIA = "sepia"
    CYBERPUNK = "cyberpunk"
    PASTEL = "pastel"
    HIGH_CONTRAST = "high_contrast"
    WARM = "warm"
    COOL = "cool"
    NEUTRAL = "neutral"
    CUSTOM = "custom"


class FilterParameter(str, Enum):
    """A single tunable parameter of a visual filter.

    The set spans color correction (brightness, contrast, saturation,
    hue_shift, gamma, exposure, temperature, tint), stylized effects
    (grain, vignette, bloom, chromatic_aberration, depth_of_field,
    motion_blur, sharpness, noise), and retro effects (scanline,
    pixelate, color_invert, posterize).
    """

    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"
    HUE_SHIFT = "hue_shift"
    GAMMA = "gamma"
    EXPOSURE = "exposure"
    TEMPERATURE = "temperature"
    TINT = "tint"
    GRAIN = "grain"
    VIGNETTE = "vignette"
    BLOOM = "bloom"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    DEPTH_OF_FIELD = "depth_of_field"
    MOTION_BLUR = "motion_blur"
    SHARPNESS = "sharpness"
    NOISE = "noise"
    SCANLINE = "scanline"
    PIXELATE = "pixelate"
    COLOR_INVERT = "color_invert"
    POSTERIZE = "posterize"


class FilterCategory(str, Enum):
    """Functional grouping of a filter preset.

    Used by the preset browser to group presets into color correction,
    stylized, cinematic, retro, artistic, and accessibility buckets.
    """

    COLOR_CORRECTION = "color_correction"
    STYLIZED = "stylized"
    CINEMATIC = "cinematic"
    RETRO = "retro"
    ARTISTIC = "artistic"
    ACCESSIBILITY = "accessibility"
    CUSTOM = "custom"


class FilterBlendMode(str, Enum):
    """Blend mode used when compositing a filter onto the viewport."""

    NORMAL = "normal"
    OVERLAY = "overlay"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    ADD = "add"
    SUBTRACT = "subtract"


class FilterQuality(str, Enum):
    """Quality tier of a filter preset.

    Higher tiers apply more expensive passes (full-resolution bloom,
    high-sample depth of field) while lower tiers skip or downsample them.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class FilterStatus(str, Enum):
    """Lifecycle state of a filter preset."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    ERROR = "error"


class FilterLUTFormat(str, Enum):
    """File format of a color grading LUT asset."""

    LUT_1D = "lut_1d"
    LUT_3D = "lut_3d"
    CUBE = "cube"
    PNG_STRIP = "png_strip"


class FilterTarget(str, Enum):
    """Render target that a filter or stack applies to."""

    VIEWPORT = "viewport"
    SCREENSHOT = "screenshot"
    CUTSCENE = "cutscene"
    PHOTO_MODE = "photo_mode"
    UI_ONLY = "ui_only"


class VisualFilterEventKind(str, Enum):
    """Audit event kinds emitted by the visual filter system."""

    CREATED = "created"
    UPDATED = "updated"
    REMOVED = "removed"
    APPLIED = "applied"
    REVERTED = "reverted"
    EXPORTED = "exported"
    IMPORTED = "imported"


# ---------------------------------------------------------------------------
# Parameter Bounds Table
# ---------------------------------------------------------------------------

# Default (min, max, default) bounds for every FilterParameter. Centralizing
# the bounds here keeps the seed data and the per-parameter setters
# consistent and avoids magic numbers scattered through the code.
_PARAMETER_BOUNDS: Dict[str, Tuple[float, float, float]] = {
    FilterParameter.BRIGHTNESS.value: (0.0, 2.0, 1.0),
    FilterParameter.CONTRAST.value: (0.0, 2.0, 1.0),
    FilterParameter.SATURATION.value: (0.0, 2.0, 1.0),
    FilterParameter.HUE_SHIFT.value: (-1.0, 1.0, 0.0),
    FilterParameter.GAMMA.value: (0.1, 3.0, 1.0),
    FilterParameter.EXPOSURE.value: (-2.0, 2.0, 0.0),
    FilterParameter.TEMPERATURE.value: (-1.0, 1.0, 0.0),
    FilterParameter.TINT.value: (-1.0, 1.0, 0.0),
    FilterParameter.GRAIN.value: (0.0, 1.0, 0.0),
    FilterParameter.VIGNETTE.value: (0.0, 1.0, 0.0),
    FilterParameter.BLOOM.value: (0.0, 1.0, 0.0),
    FilterParameter.CHROMATIC_ABERRATION.value: (0.0, 1.0, 0.0),
    FilterParameter.DEPTH_OF_FIELD.value: (0.0, 1.0, 0.0),
    FilterParameter.MOTION_BLUR.value: (0.0, 1.0, 0.0),
    FilterParameter.SHARPNESS.value: (0.0, 2.0, 1.0),
    FilterParameter.NOISE.value: (0.0, 1.0, 0.0),
    FilterParameter.SCANLINE.value: (0.0, 1.0, 0.0),
    FilterParameter.PIXELATE.value: (0.0, 1.0, 0.0),
    FilterParameter.COLOR_INVERT.value: (0.0, 1.0, 0.0),
    FilterParameter.POSTERIZE.value: (0.0, 1.0, 0.0),
}


def _parameter_bounds(parameter: str) -> Tuple[float, float, float]:
    """Return ``(min_value, max_value, default_value)`` for a parameter.

    Falls back to a generic ``(0.0, 1.0, 0.0)`` range when the parameter
    is not in the canonical table so unknown parameters remain usable.
    """
    return _PARAMETER_BOUNDS.get(parameter, (0.0, 1.0, 0.0))


def _make_parameter_entry(
    parameter: str, value: float, enabled: bool = True
) -> "FilterParameterEntry":
    """Build a FilterParameterEntry with correct bounds and default.

    The value is clamped to the parameter's min/max range. The default
    value is taken from the bounds table so ``reset_parameter`` can
    restore the original baseline.
    """
    lo, hi, default = _parameter_bounds(parameter)
    return FilterParameterEntry(
        parameter=parameter,
        value=_clamp(_safe_float(value, default), lo, hi),
        min_value=lo,
        max_value=hi,
        default_value=default,
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class FilterParameterEntry:
    """A single typed parameter on a filter preset.

    Attributes:
        parameter: The FilterParameter value name (e.g. "brightness").
        value: The current value clamped to ``[min_value, max_value]``.
        min_value: Lower bound for the value.
        max_value: Upper bound for the value.
        default_value: The baseline value the parameter resets to.
        enabled: Whether the parameter contributes to the rendered filter.
    """

    parameter: str
    value: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    default_value: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FilterPreset:
    """A named visual filter preset composed of typed parameters.

    A preset bundles a set of FilterParameterEntry values, a blend mode,
    a quality tier, an intensity multiplier, and optional LUT and
    thumbnail assets. Presets are the primary unit of filter management.

    Attributes:
        preset_id: Unique preset identifier.
        name: Display name.
        description: Human-readable description.
        preset_type: The FilterPresetType value name.
        category: The FilterCategory value name.
        parameters: Typed parameter entries keyed by parameter name.
        blend_mode: The FilterBlendMode value name.
        quality: The FilterQuality value name.
        intensity: Multiplier applied to the overall filter strength.
        enabled: Whether the preset is eligible for application.
        tags: Searchable tags for filtering.
        thumbnail_url: Optional thumbnail asset URL.
        lut_path: Optional LUT asset path bound to this preset.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    preset_id: str
    name: str
    description: str = ""
    preset_type: str = FilterPresetType.CUSTOM.value
    category: str = FilterCategory.CUSTOM.value
    parameters: Dict[str, FilterParameterEntry] = field(default_factory=dict)
    blend_mode: str = FilterBlendMode.NORMAL.value
    quality: str = FilterQuality.MEDIUM.value
    intensity: float = 1.0
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    thumbnail_url: str = ""
    lut_path: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FilterStack:
    """An ordered composition of presets applied to a render target.

    A stack holds an ordered list of preset ids that are blended together
    when rendering the target. Only one stack per target should be active
    at a time; ``blend_strength`` scales the combined contribution.

    Attributes:
        stack_id: Unique stack identifier.
        name: Display name.
        description: Human-readable description.
        target: The FilterTarget value name this stack applies to.
        preset_ids: Ordered list of preset ids in the stack.
        active: Whether the stack is currently active for its target.
        sort_order: Ordering hint for stack selection.
        blend_strength: Multiplier on the combined preset contribution.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        metadata: Free-form extension data.
    """

    stack_id: str
    name: str
    description: str = ""
    target: str = FilterTarget.VIEWPORT.value
    preset_ids: List[str] = field(default_factory=list)
    active: bool = False
    sort_order: float = 0.0
    blend_strength: float = 1.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FilterLUT:
    """A color grading LUT asset.

    Attributes:
        lut_id: Unique LUT identifier.
        name: Display name.
        format: The FilterLUTFormat value name.
        size: The LUT size (e.g. 32 for a 32x32x32 3D LUT).
        data_path: Path to the LUT data file.
        dimensions: The (width, height, depth) dimensions of the LUT.
        color_space: The color space the LUT operates in (e.g. "sRGB").
        created_at: Creation timestamp.
        metadata: Free-form extension data.
    """

    lut_id: str
    name: str
    format: str = FilterLUTFormat.LUT_3D.value
    size: int = 32
    data_path: str = ""
    dimensions: Tuple[int, int, int] = (32, 32, 32)
    color_space: str = "sRGB"
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FilterCapture:
    """A record of a filter applied to a captured frame.

    Captures are produced by ``apply_filter`` and ``capture_filtered``
    and serve as proof that a given filter configuration was rendered for
    a specific frame and target.

    Attributes:
        capture_id: Unique capture identifier.
        preset_id: The preset that was applied.
        target: The FilterTarget value name.
        frame_number: The frame index at capture time.
        timestamp: Capture timestamp.
        parameters_snapshot: A snapshot of the parameter values at capture.
        result_url: Optional URL to the captured image.
        metadata: Free-form extension data.
    """

    capture_id: str
    preset_id: str
    target: str = FilterTarget.VIEWPORT.value
    frame_number: int = 0
    timestamp: str = field(default_factory=_now)
    parameters_snapshot: Dict[str, Any] = field(default_factory=dict)
    result_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FilterTransition:
    """A smooth transition between two filter presets.

    Transitions interpolate the active filter from a source preset to a
    target preset over a duration using an easing function. The progress
    field tracks how far the transition has advanced (0.0 to 1.0).

    Attributes:
        transition_id: Unique transition identifier.
        from_preset_id: The source preset id.
        to_preset_id: The destination preset id.
        duration: Transition duration in seconds.
        easing: Easing function name (e.g. "linear", "ease_in_out").
        active: Whether the transition is currently in progress.
        progress: Current progress from 0.0 to 1.0.
        created_at: Creation timestamp.
    """

    transition_id: str
    from_preset_id: str
    to_preset_id: str
    duration: float = 1.0
    easing: str = "linear"
    active: bool = False
    progress: float = 0.0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FilterComparison:
    """A side-by-side comparison of parameter values across presets.

    Attributes:
        comparison_id: Unique comparison identifier.
        preset_ids: The list of preset ids that were compared.
        parameter_deltas: Mapping of parameter name to a tuple of values
            (one per preset) so a designer can see the spread at a glance.
        created_at: Creation timestamp.
    """

    comparison_id: str
    preset_ids: List[str] = field(default_factory=list)
    parameter_deltas: Dict[str, Tuple[float, ...]] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VisualFilterConfig:
    """Global tuning parameters for the visual filter system.

    Attributes:
        max_presets: Maximum number of presets retained before FIFO eviction.
        max_stacks: Maximum number of stacks retained.
        max_luts: Maximum number of LUTs retained.
        max_captures: Maximum number of captures retained.
        max_events: Maximum number of audit events retained.
        auto_apply_default: Whether to auto-apply the default preset on init.
        default_quality: Default quality tier for new presets.
        default_target: Default render target for new stacks.
        enable_grain: Whether the grain effect is globally enabled.
        enable_vignette: Whether the vignette effect is globally enabled.
        metadata: Free-form extension data.
    """

    max_presets: int = _MAX_FILTERS
    max_stacks: int = _MAX_STACKS
    max_luts: int = _MAX_LUTS
    max_captures: int = _MAX_CAPTURES
    max_events: int = _MAX_EVENTS
    auto_apply_default: bool = False
    default_quality: str = FilterQuality.MEDIUM.value
    default_target: str = FilterTarget.VIEWPORT.value
    enable_grain: bool = True
    enable_vignette: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VisualFilterStats:
    """Aggregate statistics for the visual filter system.

    Attributes:
        total_presets: Total number of registered presets.
        total_stacks: Total number of registered stacks.
        total_luts: Total number of registered LUTs.
        total_captures: Total number of captured frames.
        active_presets: Number of presets currently enabled.
        active_stacks: Number of stacks currently active.
        total_applied: Cumulative count of filter applications.
        total_reverted: Cumulative count of filter reverts.
        tick_count: Number of ticks processed.
    """

    total_presets: int = 0
    total_stacks: int = 0
    total_luts: int = 0
    total_captures: int = 0
    active_presets: int = 0
    active_stacks: int = 0
    total_applied: int = 0
    total_reverted: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VisualFilterSnapshot:
    """Full state snapshot of the visual filter system.

    Attributes:
        timestamp: Snapshot timestamp.
        presets: Serialized preset list (bounded for size).
        stacks: Serialized stack list.
        luts: Serialized LUT list.
        captures: Serialized capture list (bounded for size).
        events: Serialized event list (bounded for size).
        stats: Serialized statistics.
    """

    timestamp: str = field(default_factory=_now)
    presets: List[Dict[str, Any]] = field(default_factory=list)
    stacks: List[Dict[str, Any]] = field(default_factory=list)
    luts: List[Dict[str, Any]] = field(default_factory=list)
    captures: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VisualFilterEvent:
    """An audit event emitted by the visual filter system.

    Attributes:
        event_id: Unique event identifier.
        timestamp: Event timestamp.
        event_type: The VisualFilterEventKind value name.
        preset_id: The preset id the event concerns (when applicable).
        description: Human-readable summary of the event.
        metadata: Free-form extension data.
    """

    event_id: str
    timestamp: str = field(default_factory=_now)
    event_type: str = ""
    preset_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Visual Filter System
# ---------------------------------------------------------------------------


class VisualFilterSystem:
    """Manages visual filter presets, stacks, LUTs, captures, transitions,
    comparisons, and the AI filter generation pipeline.

    The system is a thread-safe singleton. All public methods take the
    instance lock before mutating shared state so that concurrent calls
    from render, gameplay, and editor threads remain consistent.
    """

    _instance: Optional["VisualFilterSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        # Primary stores
        self._presets: Dict[str, FilterPreset] = {}
        self._stacks: Dict[str, FilterStack] = {}
        self._luts: Dict[str, FilterLUT] = {}
        self._captures: Dict[str, FilterCapture] = {}
        self._transitions: Dict[str, FilterTransition] = {}
        self._comparisons: Dict[str, FilterComparison] = {}
        self._events: List[VisualFilterEvent] = []
        # Active filter per target (target -> preset_id)
        self._active_filters: Dict[str, str] = {}
        # Config and stats
        self._config = VisualFilterConfig()
        self._stats = VisualFilterStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._capture_counter: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "VisualFilterSystem":
        """Return the singleton VisualFilterSystem instance.

        Uses double-checked locking so the instance is created exactly
        once even when multiple threads call this concurrently on first
        use.
        """
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the system with seed data (idempotent).

        Guarded by the init lock so repeated calls are no-ops after the
        first successful seed. This is invoked from ``__init__`` and from
        ``reset`` to repopulate the default data set.
        """
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed()
            self._initialized = True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with seed data.

        Seeds eight filter presets covering the canonical look families,
        three filter stacks (one per primary render target), four color
        grading LUTs, three preset transitions, and six audit events.
        """
        now = _now()

        # --- Filter Presets (8) ---
        # Each preset is built from a small set of parameters chosen to
        # evoke its named style. Parameters not listed here fall back to
        # their default values when looked up via get_parameter.
        cinematic_params = {
            FilterParameter.CONTRAST.value: 1.15,
            FilterParameter.SATURATION.value: 1.1,
            FilterParameter.TEMPERATURE.value: 0.1,
            FilterParameter.TINT.value: -0.05,
            FilterParameter.VIGNETTE.value: 0.3,
            FilterParameter.BLOOM.value: 0.15,
            FilterParameter.SHARPNESS.value: 1.05,
        }
        noir_params = {
            FilterParameter.SATURATION.value: 0.0,
            FilterParameter.CONTRAST.value: 1.4,
            FilterParameter.BRIGHTNESS.value: 0.95,
            FilterParameter.GRAIN.value: 0.4,
            FilterParameter.VIGNETTE.value: 0.5,
            FilterParameter.SHARPNESS.value: 1.1,
        }
        vintage_params = {
            FilterParameter.SATURATION.value: 0.75,
            FilterParameter.CONTRAST.value: 0.9,
            FilterParameter.TEMPERATURE.value: 0.3,
            FilterParameter.VIGNETTE.value: 0.35,
            FilterParameter.GRAIN.value: 0.25,
            FilterParameter.GAMMA.value: 1.1,
        }
        vibrant_params = {
            FilterParameter.SATURATION.value: 1.5,
            FilterParameter.CONTRAST.value: 1.2,
            FilterParameter.BRIGHTNESS.value: 1.05,
            FilterParameter.SHARPNESS.value: 1.1,
        }
        dreamy_params = {
            FilterParameter.CONTRAST.value: 0.85,
            FilterParameter.SATURATION.value: 1.1,
            FilterParameter.BRIGHTNESS.value: 1.1,
            FilterParameter.BLOOM.value: 0.4,
            FilterParameter.DEPTH_OF_FIELD.value: 0.3,
        }
        horror_params = {
            FilterParameter.BRIGHTNESS.value: 0.8,
            FilterParameter.CONTRAST.value: 1.5,
            FilterParameter.SATURATION.value: 0.6,
            FilterParameter.GRAIN.value: 0.5,
            FilterParameter.VIGNETTE.value: 0.6,
            FilterParameter.NOISE.value: 0.2,
        }
        retro_params = {
            FilterParameter.SATURATION.value: 1.2,
            FilterParameter.TEMPERATURE.value: 0.4,
            FilterParameter.SCANLINE.value: 0.3,
            FilterParameter.PIXELATE.value: 0.1,
            FilterParameter.CONTRAST.value: 1.1,
        }
        watercolor_params = {
            FilterParameter.SATURATION.value: 1.15,
            FilterParameter.CONTRAST.value: 0.8,
            FilterParameter.BRIGHTNESS.value: 1.05,
            FilterParameter.POSTERIZE.value: 0.2,
            FilterParameter.BLOOM.value: 0.2,
        }

        preset_seeds: List[Tuple[str, str, str, str, str, Dict[str, float], str, str, List[str]]] = [
            (
                "preset_cinematic", "Cinematic Teal-Orange", "Teal and orange blockbuster grade.",
                FilterPresetType.CINEMATIC.value, FilterCategory.CINEMATIC.value,
                cinematic_params, FilterBlendMode.NORMAL.value, FilterQuality.HIGH.value,
                ["cinematic", "film", "teal-orange"],
            ),
            (
                "preset_noir", "Film Noir", "High-contrast black and white with grain.",
                FilterPresetType.NOIR.value, FilterCategory.STYLIZED.value,
                noir_params, FilterBlendMode.NORMAL.value, FilterQuality.HIGH.value,
                ["noir", "monochrome", "drama"],
            ),
            (
                "preset_vintage", "Vintage Film", "Faded warm retro film look.",
                FilterPresetType.VINTAGE.value, FilterCategory.RETRO.value,
                vintage_params, FilterBlendMode.NORMAL.value, FilterQuality.MEDIUM.value,
                ["vintage", "retro", "warm"],
            ),
            (
                "preset_vibrant", "Vibrant Pop", "Punchy saturated colors.",
                FilterPresetType.VIBRANT.value, FilterCategory.STYLIZED.value,
                vibrant_params, FilterBlendMode.NORMAL.value, FilterQuality.HIGH.value,
                ["vibrant", "saturated", "bright"],
            ),
            (
                "preset_dreamy", "Dreamy Soft Focus", "Soft glowing dreamlike look.",
                FilterPresetType.DREAMY.value, FilterCategory.ARTISTIC.value,
                dreamy_params, FilterBlendMode.SCREEN.value, FilterQuality.HIGH.value,
                ["dreamy", "soft", "bloom"],
            ),
            (
                "preset_horror", "Horror Dread", "Dark high-contrast grainy nightmare.",
                FilterPresetType.HORROR.value, FilterCategory.STYLIZED.value,
                horror_params, FilterBlendMode.MULTIPLY.value, FilterQuality.MEDIUM.value,
                ["horror", "dark", "grain"],
            ),
            (
                "preset_retro", "Retro 80s Synthwave", "Scanline and warm retro arcade look.",
                FilterPresetType.RETRO.value, FilterCategory.RETRO.value,
                retro_params, FilterBlendMode.NORMAL.value, FilterQuality.MEDIUM.value,
                ["retro", "80s", "scanline"],
            ),
            (
                "preset_watercolor", "Watercolor Paint", "Painted watercolor effect.",
                FilterPresetType.WATERCOLOR.value, FilterCategory.ARTISTIC.value,
                watercolor_params, FilterBlendMode.OVERLAY.value, FilterQuality.HIGH.value,
                ["watercolor", "paint", "artistic"],
            ),
        ]

        for (
            pid, name, desc, ptype, category, params, blend, quality, tags,
        ) in preset_seeds:
            preset = FilterPreset(
                preset_id=pid,
                name=name,
                description=desc,
                preset_type=ptype,
                category=category,
                parameters={
                    pname: _make_parameter_entry(pname, pval)
                    for pname, pval in params.items()
                },
                blend_mode=blend,
                quality=quality,
                intensity=1.0,
                enabled=True,
                tags=list(tags),
                thumbnail_url=f"assets://filters/{pid}.png",
                lut_path=f"assets://luts/{pid}.cube",
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            )
            self._presets[pid] = preset

        # --- Filter Stacks (3) ---
        stack_seeds: List[Tuple[str, str, str, str, List[str], bool, float, float]] = [
            (
                "stack_viewport", "Viewport Stack",
                "Default stack applied to the live game viewport.",
                FilterTarget.VIEWPORT.value,
                ["preset_cinematic", "preset_vibrant"],
                True, 0.0, 1.0,
            ),
            (
                "stack_cutscene", "Cutscene Stack",
                "Stack applied during cinematic cutscenes.",
                FilterTarget.CUTSCENE.value,
                ["preset_cinematic", "preset_dreamy"],
                False, 1.0, 0.8,
            ),
            (
                "stack_photo_mode", "Photo Mode Stack",
                "Stack applied in the photo mode capture pipeline.",
                FilterTarget.PHOTO_MODE.value,
                ["preset_watercolor", "preset_vintage"],
                False, 2.0, 1.0,
            ),
        ]
        for (
            sid, name, desc, target, preset_ids, active, order, strength,
        ) in stack_seeds:
            stack = FilterStack(
                stack_id=sid,
                name=name,
                description=desc,
                target=target,
                preset_ids=list(preset_ids),
                active=active,
                sort_order=order,
                blend_strength=strength,
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            )
            self._stacks[sid] = stack

        # --- LUTs (4) ---
        lut_seeds: List[Tuple[str, str, str, int, str, Tuple[int, int, int], str]] = [
            (
                "lut_cinematic", "Cinematic LUT", FilterLUTFormat.CUBE.value,
                32, "assets://luts/cinematic.cube", (32, 32, 32), "sRGB",
            ),
            (
                "lut_noir", "Noir LUT", FilterLUTFormat.LUT_3D.value,
                32, "assets://luts/noir.lut3d", (32, 32, 32), "sRGB",
            ),
            (
                "lut_vintage", "Vintage LUT", FilterLUTFormat.PNG_STRIP.value,
                256, "assets://luts/vintage_strip.png", (256, 1, 1), "sRGB",
            ),
            (
                "lut_vibrant", "Vibrant LUT", FilterLUTFormat.LUT_1D.value,
                1024, "assets://luts/vibrant.lut1d", (1024, 1, 1), "Linear",
            ),
        ]
        for (
            lid, name, fmt, size, path, dims, color_space,
        ) in lut_seeds:
            lut = FilterLUT(
                lut_id=lid,
                name=name,
                format=fmt,
                size=size,
                data_path=path,
                dimensions=dims,
                color_space=color_space,
                created_at=now,
                metadata={"seed": True},
            )
            self._luts[lid] = lut

        # --- Transitions (3) ---
        transition_seeds: List[Tuple[str, str, str, float, str, bool, float]] = [
            (
                "trans_cinematic_to_noir", "preset_cinematic", "preset_noir",
                1.5, "ease_in_out", True, 0.0,
            ),
            (
                "trans_vintage_to_vibrant", "preset_vintage", "preset_vibrant",
                1.0, "linear", False, 0.0,
            ),
            (
                "trans_dreamy_to_horror", "preset_dreamy", "preset_horror",
                2.0, "ease_in", False, 0.0,
            ),
        ]
        for (
            tid, from_id, to_id, duration, easing, active, progress,
        ) in transition_seeds:
            transition = FilterTransition(
                transition_id=tid,
                from_preset_id=from_id,
                to_preset_id=to_id,
                duration=duration,
                easing=easing,
                active=active,
                progress=progress,
                created_at=now,
            )
            self._transitions[tid] = transition

        # --- Active Filters ---
        # Seed the viewport with the cinematic preset as the default active
        # filter so the system has a sensible starting state.
        self._active_filters[FilterTarget.VIEWPORT.value] = "preset_cinematic"

        # --- Events (6) ---
        event_seeds: List[Tuple[str, str, str, str]] = [
            (
                VisualFilterEventKind.CREATED.value, "preset_cinematic",
                "Seeded preset 'Cinematic Teal-Orange'",
            ),
            (
                VisualFilterEventKind.CREATED.value, "preset_noir",
                "Seeded preset 'Film Noir'",
            ),
            (
                VisualFilterEventKind.APPLIED.value, "preset_cinematic",
                "Applied 'Cinematic Teal-Orange' to viewport",
            ),
            (
                VisualFilterEventKind.CREATED.value, "stack_viewport",
                "Seeded stack 'Viewport Stack'",
            ),
            (
                VisualFilterEventKind.CREATED.value, "lut_cinematic",
                "Seeded LUT 'Cinematic LUT'",
            ),
            (
                VisualFilterEventKind.EXPORTED.value, "preset_vintage",
                "Exported preset 'Vintage Film'",
            ),
        ]
        for (etype, pid, desc) in event_seeds:
            self._event_counter += 1
            self._events.append(
                VisualFilterEvent(
                    event_id=f"fevt_{self._event_counter:08d}",
                    timestamp=now,
                    event_type=etype,
                    preset_id=pid,
                    description=desc,
                    metadata={"seed": True},
                )
            )

        # --- Stats ---
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        preset_id: str = "",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event and trim the event log to capacity."""
        self._event_counter += 1
        event = VisualFilterEvent(
            event_id=f"fevt_{self._event_counter:08d}",
            timestamp=_now(),
            event_type=event_type,
            preset_id=preset_id,
            description=description,
            metadata=metadata or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from the current stores."""
        self._stats.total_presets = len(self._presets)
        self._stats.total_stacks = len(self._stacks)
        self._stats.total_luts = len(self._luts)
        self._stats.total_captures = len(self._captures)
        self._stats.active_presets = sum(
            1 for p in self._presets.values() if p.enabled
        )
        self._stats.active_stacks = sum(
            1 for s in self._stacks.values() if s.active
        )
        self._stats.tick_count = self._tick_count

    def _resolve_preset(self, preset_id: str) -> Optional[FilterPreset]:
        """Return a preset or None, taking the lock is the caller's job."""
        return self._presets.get(preset_id)

    def _resolve_stack(self, stack_id: str) -> Optional[FilterStack]:
        return self._stacks.get(stack_id)

    def _resolve_lut(self, lut_id: str) -> Optional[FilterLUT]:
        return self._luts.get(lut_id)

    def _normalize_parameter_name(self, parameter: str) -> str:
        """Return the canonical parameter name for a given input.

        Accepts either a FilterParameter member, its value, or a raw
        string. Unknown strings are returned as-is so custom parameters
        remain usable.
        """
        if isinstance(parameter, FilterParameter):
            return parameter.value
        return str(parameter)

    # ------------------------------------------------------------------
    # Preset Management
    # ------------------------------------------------------------------

    def register_preset(
        self,
        preset_id: str,
        name: str,
        preset_type: str,
        description: str = "",
        category: str = FilterCategory.CUSTOM.value,
        parameters: Optional[Dict[str, Any]] = None,
        blend_mode: str = FilterBlendMode.NORMAL.value,
        quality: str = FilterQuality.MEDIUM.value,
        intensity: float = 1.0,
        enabled: bool = True,
        tags: Optional[List[str]] = None,
        thumbnail_url: str = "",
        lut_path: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FilterPreset]]:
        """Register a new filter preset.

        Args:
            preset_id: Unique preset identifier.
            name: Display name.
            preset_type: The FilterPresetType value name.
            description: Human-readable description.
            category: The FilterCategory value name.
            parameters: Optional mapping of parameter name to value. Each
                value is clamped to the parameter's bounds and wrapped in
                a FilterParameterEntry.
            blend_mode: The FilterBlendMode value name.
            quality: The FilterQuality value name.
            intensity: Multiplier on the overall filter strength.
            enabled: Whether the preset is eligible for application.
            tags: Searchable tags.
            thumbnail_url: Optional thumbnail asset URL.
            lut_path: Optional LUT asset path.
            metadata: Free-form extension data.

        Returns:
            A ``(ok, message, preset)`` tuple. ``ok`` is False when the id
            already exists or the id is empty.
        """
        if not preset_id:
            return False, "preset_id is required", None
        with self._lock:
            if preset_id in self._presets:
                return False, "preset_id already exists", None
            if len(self._presets) >= self._config.max_presets:
                _evict_fifo_dict(self._presets, self._config.max_presets)

            type_enum = _coerce_enum(
                FilterPresetType, preset_type, FilterPresetType.CUSTOM
            )
            category_enum = _coerce_enum(
                FilterCategory, category, FilterCategory.CUSTOM
            )
            blend_enum = _coerce_enum(
                FilterBlendMode, blend_mode, FilterBlendMode.NORMAL
            )
            quality_enum = _coerce_enum(
                FilterQuality, quality, FilterQuality.MEDIUM
            )

            now = _now()
            param_entries: Dict[str, FilterParameterEntry] = {}
            if parameters:
                for pname, pval in parameters.items():
                    canonical = self._normalize_parameter_name(pname)
                    param_entries[canonical] = _make_parameter_entry(
                        canonical, pval
                    )

            preset = FilterPreset(
                preset_id=preset_id,
                name=name or preset_id,
                description=description,
                preset_type=type_enum.value,
                category=category_enum.value,
                parameters=param_entries,
                blend_mode=blend_enum.value,
                quality=quality_enum.value,
                intensity=_clamp(
                    _safe_float(intensity, 1.0),
                    _INTENSITY_MIN, _INTENSITY_MAX,
                ),
                enabled=bool(enabled),
                tags=list(tags or []),
                thumbnail_url=thumbnail_url,
                lut_path=lut_path,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._presets[preset_id] = preset
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.CREATED.value,
                preset_id,
                f"Registered preset '{preset.name}'",
                {"preset_type": preset.preset_type, "category": preset.category},
            )
            return True, "registered", preset

    def get_preset(self, preset_id: str) -> Optional[FilterPreset]:
        """Retrieve a preset by its identifier."""
        with self._lock:
            return self._resolve_preset(preset_id)

    def list_presets(
        self,
        preset_type: Optional[str] = None,
        category: Optional[str] = None,
        enabled: Optional[bool] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[FilterPreset]:
        """List presets with optional filters.

        Args:
            preset_type: Filter by FilterPresetType value name.
            category: Filter by FilterCategory value name.
            enabled: Filter by enabled state.
            limit: Maximum number of presets to return.

        Returns:
            A list of matching FilterPreset objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            type_value = None
            if preset_type is not None:
                type_enum = _coerce_enum(FilterPresetType, preset_type, None)
                type_value = type_enum.value if type_enum else preset_type
            cat_value = None
            if category is not None:
                cat_enum = _coerce_enum(FilterCategory, category, None)
                cat_value = cat_enum.value if cat_enum else category
            results: List[FilterPreset] = []
            for preset in self._presets.values():
                if type_value is not None and preset.preset_type != type_value:
                    continue
                if cat_value is not None and preset.category != cat_value:
                    continue
                if enabled is not None and preset.enabled != enabled:
                    continue
                results.append(preset)
                if len(results) >= cap:
                    break
            return results

    def remove_preset(self, preset_id: str) -> Tuple[bool, str]:
        """Remove a preset by its identifier.

        Also clears the preset from any stacks and active filters that
        hold a handle to it.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            preset = self._presets.get(preset_id)
            if preset is None:
                return False, "not found"
            del self._presets[preset_id]
            # Detach from stacks.
            for stack in self._stacks.values():
                if preset_id in stack.preset_ids:
                    stack.preset_ids.remove(preset_id)
                    stack.updated_at = _now()
            # Detach from active filters.
            for target, active_id in list(self._active_filters.items()):
                if active_id == preset_id:
                    self._active_filters.pop(target, None)
            # Detach from transitions.
            for transition in self._transitions.values():
                if transition.from_preset_id == preset_id:
                    transition.from_preset_id = ""
                if transition.to_preset_id == preset_id:
                    transition.to_preset_id = ""
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.REMOVED.value,
                preset_id,
                f"Removed preset '{preset.name}'",
            )
            return True, "removed"

    def update_preset(
        self, preset_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[FilterPreset]]:
        """Update mutable fields on an existing preset.

        Accepts any subset of FilterPreset fields. Enum-typed fields
        (``preset_type``, ``category``, ``blend_mode``, ``quality``) are
        coerced via their respective enums. The ``parameters`` field, when
        provided as a dict, is merged into the existing parameters (each
        value clamped and wrapped). The ``updated_at`` timestamp is
        refreshed.

        Returns:
            A ``(ok, message, preset)`` tuple.
        """
        with self._lock:
            preset = self._resolve_preset(preset_id)
            if preset is None:
                return False, "not found", None
            # Scalar fields.
            for key in ("name", "description", "thumbnail_url", "lut_path"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(preset, key, kwargs[key])
            for key in ("enabled",):
                if key in kwargs and kwargs[key] is not None:
                    setattr(preset, key, bool(kwargs[key]))
            if "intensity" in kwargs and kwargs["intensity"] is not None:
                preset.intensity = _clamp(
                    _safe_float(kwargs["intensity"], preset.intensity),
                    _INTENSITY_MIN, _INTENSITY_MAX,
                )
            if "tags" in kwargs and kwargs["tags"] is not None:
                preset.tags = list(kwargs["tags"])
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                if isinstance(kwargs["metadata"], dict):
                    preset.metadata.update(kwargs["metadata"])
            # Enum fields.
            if "preset_type" in kwargs and kwargs["preset_type"] is not None:
                enum_val = _coerce_enum(
                    FilterPresetType, kwargs["preset_type"], None
                )
                if enum_val is not None:
                    preset.preset_type = enum_val.value
            if "category" in kwargs and kwargs["category"] is not None:
                enum_val = _coerce_enum(
                    FilterCategory, kwargs["category"], None
                )
                if enum_val is not None:
                    preset.category = enum_val.value
            if "blend_mode" in kwargs and kwargs["blend_mode"] is not None:
                enum_val = _coerce_enum(
                    FilterBlendMode, kwargs["blend_mode"], None
                )
                if enum_val is not None:
                    preset.blend_mode = enum_val.value
            if "quality" in kwargs and kwargs["quality"] is not None:
                enum_val = _coerce_enum(
                    FilterQuality, kwargs["quality"], None
                )
                if enum_val is not None:
                    preset.quality = enum_val.value
            # Parameters merge.
            if "parameters" in kwargs and kwargs["parameters"] is not None:
                if isinstance(kwargs["parameters"], dict):
                    for pname, pval in kwargs["parameters"].items():
                        canonical = self._normalize_parameter_name(pname)
                        preset.parameters[canonical] = _make_parameter_entry(
                            canonical, pval
                        )
            preset.updated_at = _now()
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                preset_id,
                f"Updated preset '{preset.name}'",
            )
            return True, "updated", preset

    # ------------------------------------------------------------------
    # Parameter Management
    # ------------------------------------------------------------------

    def set_parameter(
        self,
        preset_id: str,
        parameter: str,
        value: float,
        enabled: Optional[bool] = None,
    ) -> Tuple[bool, str, Optional[FilterParameterEntry]]:
        """Set a single parameter on a preset.

        If the parameter does not yet exist on the preset it is created
        using the canonical bounds. The value is clamped to the parameter
        range. When ``enabled`` is provided the entry's enabled flag is
        also updated.

        Returns:
            A ``(ok, message, entry)`` tuple.
        """
        with self._lock:
            preset = self._resolve_preset(preset_id)
            if preset is None:
                return False, "preset not found", None
            canonical = self._normalize_parameter_name(parameter)
            lo, hi, default = _parameter_bounds(canonical)
            clamped = _clamp(_safe_float(value, default), lo, hi)
            entry = preset.parameters.get(canonical)
            if entry is None:
                entry = FilterParameterEntry(
                    parameter=canonical,
                    value=clamped,
                    min_value=lo,
                    max_value=hi,
                    default_value=default,
                    enabled=True if enabled is None else bool(enabled),
                )
                preset.parameters[canonical] = entry
            else:
                entry.value = clamped
                if enabled is not None:
                    entry.enabled = bool(enabled)
            preset.updated_at = _now()
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                preset_id,
                f"Set parameter '{canonical}' to {clamped} on '{preset.name}'",
                {"parameter": canonical, "value": clamped},
            )
            return True, "set", entry

    def get_parameter(
        self, preset_id: str, parameter: str
    ) -> Optional[FilterParameterEntry]:
        """Return a parameter entry for a preset, or None.

        When the parameter is not present on the preset but is a known
        canonical parameter, a default entry is returned so callers always
        see a usable value.
        """
        with self._lock:
            preset = self._resolve_preset(preset_id)
            if preset is None:
                return None
            canonical = self._normalize_parameter_name(parameter)
            entry = preset.parameters.get(canonical)
            if entry is not None:
                return entry
            # Return a default entry for known canonical parameters.
            if canonical in _PARAMETER_BOUNDS:
                return _make_parameter_entry(canonical, _parameter_bounds(canonical)[2])
            return None

    def reset_parameter(
        self, preset_id: str, parameter: str
    ) -> Tuple[bool, str, Optional[FilterParameterEntry]]:
        """Reset a parameter on a preset to its default value.

        Returns:
            A ``(ok, message, entry)`` tuple.
        """
        with self._lock:
            preset = self._resolve_preset(preset_id)
            if preset is None:
                return False, "preset not found", None
            canonical = self._normalize_parameter_name(parameter)
            entry = preset.parameters.get(canonical)
            if entry is None:
                # Create the entry at its default.
                entry = _make_parameter_entry(canonical, _parameter_bounds(canonical)[2])
                preset.parameters[canonical] = entry
            else:
                entry.value = entry.default_value
                entry.enabled = True
            preset.updated_at = _now()
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                preset_id,
                f"Reset parameter '{canonical}' on '{preset.name}'",
                {"parameter": canonical},
            )
            return True, "reset", entry

    # ------------------------------------------------------------------
    # Stack Management
    # ------------------------------------------------------------------

    def create_stack(
        self,
        stack_id: str,
        name: str,
        target: str = FilterTarget.VIEWPORT.value,
        description: str = "",
        preset_ids: Optional[List[str]] = None,
        active: bool = False,
        sort_order: float = 0.0,
        blend_strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FilterStack]]:
        """Create a new filter stack for a render target.

        Args:
            stack_id: Unique stack identifier.
            name: Display name.
            target: The FilterTarget value name.
            description: Human-readable description.
            preset_ids: Initial ordered list of preset ids.
            active: Whether the stack is active. When True, other stacks
                for the same target are deactivated.
            sort_order: Ordering hint.
            blend_strength: Multiplier on the combined contribution.
            metadata: Free-form extension data.

        Returns:
            A ``(ok, message, stack)`` tuple.
        """
        if not stack_id:
            return False, "stack_id is required", None
        with self._lock:
            if stack_id in self._stacks:
                return False, "stack_id already exists", None
            if len(self._stacks) >= self._config.max_stacks:
                _evict_fifo_dict(self._stacks, self._config.max_stacks)
            target_enum = _coerce_enum(FilterTarget, target, FilterTarget.VIEWPORT)
            now = _now()
            stack = FilterStack(
                stack_id=stack_id,
                name=name or stack_id,
                description=description,
                target=target_enum.value,
                preset_ids=list(preset_ids or []),
                active=bool(active),
                sort_order=_clamp(
                    _safe_float(sort_order, 0.0),
                    _SORT_ORDER_MIN, _SORT_ORDER_MAX,
                ),
                blend_strength=_clamp(
                    _safe_float(blend_strength, 1.0),
                    _BLEND_STRENGTH_MIN, _BLEND_STRENGTH_MAX,
                ),
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._stacks[stack_id] = stack
            if stack.active:
                self._deactivate_other_stacks(stack_id, stack.target)
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.CREATED.value,
                "",
                f"Created stack '{stack.name}'",
                {"stack_id": stack_id, "target": stack.target},
            )
            return True, "created", stack

    def get_stack(self, stack_id: str) -> Optional[FilterStack]:
        """Retrieve a stack by its identifier."""
        with self._lock:
            return self._resolve_stack(stack_id)

    def list_stacks(
        self,
        target: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[FilterStack]:
        """List stacks with optional filters.

        Args:
            target: Filter by FilterTarget value name.
            active: Filter by active state.
            limit: Maximum number of stacks to return.

        Returns:
            A list of matching FilterStack objects sorted by sort_order.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            target_value = None
            if target is not None:
                target_enum = _coerce_enum(FilterTarget, target, None)
                target_value = target_enum.value if target_enum else target
            stacks = list(self._stacks.values())
            stacks.sort(key=lambda s: s.sort_order)
            results: List[FilterStack] = []
            for stack in stacks:
                if target_value is not None and stack.target != target_value:
                    continue
                if active is not None and stack.active != active:
                    continue
                results.append(stack)
                if len(results) >= cap:
                    break
            return results

    def remove_stack(self, stack_id: str) -> Tuple[bool, str]:
        """Remove a stack by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            stack = self._stacks.get(stack_id)
            if stack is None:
                return False, "not found"
            del self._stacks[stack_id]
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.REMOVED.value,
                "",
                f"Removed stack '{stack.name}'",
                {"stack_id": stack_id},
            )
            return True, "removed"

    def add_preset_to_stack(
        self, stack_id: str, preset_id: str
    ) -> Tuple[bool, str, Optional[FilterStack]]:
        """Append a preset to a stack.

        Returns:
            A ``(ok, message, stack)`` tuple. Fails when the stack or
            preset is missing, or the preset is already in the stack.
        """
        with self._lock:
            stack = self._resolve_stack(stack_id)
            if stack is None:
                return False, "stack not found", None
            if preset_id not in self._presets:
                return False, "preset not found", stack
            if preset_id in stack.preset_ids:
                return False, "preset already in stack", stack
            stack.preset_ids.append(preset_id)
            stack.updated_at = _now()
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                preset_id,
                f"Added preset '{preset_id}' to stack '{stack.name}'",
                {"stack_id": stack_id},
            )
            return True, "added", stack

    def remove_preset_from_stack(
        self, stack_id: str, preset_id: str
    ) -> Tuple[bool, str, Optional[FilterStack]]:
        """Remove a preset from a stack.

        Returns:
            A ``(ok, message, stack)`` tuple.
        """
        with self._lock:
            stack = self._resolve_stack(stack_id)
            if stack is None:
                return False, "stack not found", None
            if preset_id not in stack.preset_ids:
                return False, "preset not in stack", stack
            stack.preset_ids.remove(preset_id)
            stack.updated_at = _now()
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                preset_id,
                f"Removed preset '{preset_id}' from stack '{stack.name}'",
                {"stack_id": stack_id},
            )
            return True, "removed", stack

    def activate_stack(self, stack_id: str) -> Tuple[bool, str]:
        """Activate a stack, deactivating other stacks for the same target.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            stack = self._resolve_stack(stack_id)
            if stack is None:
                return False, "not found"
            self._deactivate_other_stacks(stack_id, stack.target)
            stack.active = True
            stack.updated_at = _now()
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                "",
                f"Activated stack '{stack.name}'",
                {"stack_id": stack_id, "target": stack.target},
            )
            return True, "activated"

    def deactivate_stack(self, stack_id: str) -> Tuple[bool, str]:
        """Deactivate a stack.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            stack = self._resolve_stack(stack_id)
            if stack is None:
                return False, "not found"
            stack.active = False
            stack.updated_at = _now()
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                "",
                f"Deactivated stack '{stack.name}'",
                {"stack_id": stack_id},
            )
            return True, "deactivated"

    def _deactivate_other_stacks(self, active_stack_id: str, target: str) -> None:
        """Deactivate every other stack bound to the same target."""
        for other_id, other in self._stacks.items():
            if other_id == active_stack_id:
                continue
            if other.target == target and other.active:
                other.active = False
                other.updated_at = _now()

    # ------------------------------------------------------------------
    # LUT Management
    # ------------------------------------------------------------------

    def register_lut(
        self,
        lut_id: str,
        name: str,
        format: str = FilterLUTFormat.LUT_3D.value,
        size: int = 32,
        data_path: str = "",
        dimensions: Tuple[int, int, int] = (32, 32, 32),
        color_space: str = "sRGB",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FilterLUT]]:
        """Register a new color grading LUT asset.

        Returns:
            A ``(ok, message, lut)`` tuple.
        """
        if not lut_id:
            return False, "lut_id is required", None
        with self._lock:
            if lut_id in self._luts:
                return False, "lut_id already exists", None
            if len(self._luts) >= self._config.max_luts:
                _evict_fifo_dict(self._luts, self._config.max_luts)
            format_enum = _coerce_enum(
                FilterLUTFormat, format, FilterLUTFormat.LUT_3D
            )
            lut = FilterLUT(
                lut_id=lut_id,
                name=name or lut_id,
                format=format_enum.value,
                size=max(1, _safe_int(size, 32)),
                data_path=data_path,
                dimensions=(
                    max(1, _safe_int(dimensions[0], 32)),
                    max(1, _safe_int(dimensions[1], 32)),
                    max(1, _safe_int(dimensions[2], 32)),
                ),
                color_space=color_space or "sRGB",
                created_at=_now(),
                metadata=metadata or {},
            )
            self._luts[lut_id] = lut
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.CREATED.value,
                "",
                f"Registered LUT '{lut.name}'",
                {"lut_id": lut_id, "format": lut.format},
            )
            return True, "registered", lut

    def get_lut(self, lut_id: str) -> Optional[FilterLUT]:
        """Retrieve a LUT by its identifier."""
        with self._lock:
            return self._resolve_lut(lut_id)

    def list_luts(
        self, format: Optional[str] = None, limit: int = _DEFAULT_LIST_LIMIT
    ) -> List[FilterLUT]:
        """List LUTs with optional format filter.

        Args:
            format: Filter by FilterLUTFormat value name.
            limit: Maximum number of LUTs to return.

        Returns:
            A list of matching FilterLUT objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            format_value = None
            if format is not None:
                format_enum = _coerce_enum(FilterLUTFormat, format, None)
                format_value = format_enum.value if format_enum else format
            results: List[FilterLUT] = []
            for lut in self._luts.values():
                if format_value is not None and lut.format != format_value:
                    continue
                results.append(lut)
                if len(results) >= cap:
                    break
            return results

    def remove_lut(self, lut_id: str) -> Tuple[bool, str]:
        """Remove a LUT by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            lut = self._luts.get(lut_id)
            if lut is None:
                return False, "not found"
            del self._luts[lut_id]
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.REMOVED.value,
                "",
                f"Removed LUT '{lut.name}'",
                {"lut_id": lut_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Apply / Revert / Capture
    # ------------------------------------------------------------------

    def apply_filter(
        self,
        preset_id: str,
        target: str = FilterTarget.VIEWPORT.value,
        intensity: float = 1.0,
    ) -> Tuple[bool, str, Optional[FilterCapture]]:
        """Apply a preset to a render target and record a capture.

        Sets the active filter for the target, scales the preset intensity
        by the given multiplier, and produces a FilterCapture recording
        the parameter snapshot at apply time.

        Returns:
            A ``(ok, message, capture)`` tuple.
        """
        with self._lock:
            preset = self._resolve_preset(preset_id)
            if preset is None:
                return False, "preset not found", None
            if not preset.enabled:
                return False, "preset is disabled", None
            target_enum = _coerce_enum(FilterTarget, target, FilterTarget.VIEWPORT)
            # Scale intensity for the duration of the apply.
            original_intensity = preset.intensity
            preset.intensity = _clamp(
                original_intensity * _safe_float(intensity, 1.0),
                _INTENSITY_MIN, _INTENSITY_MAX,
            )
            self._active_filters[target_enum.value] = preset_id
            self._capture_counter += 1
            capture = FilterCapture(
                capture_id=f"fcap_{self._capture_counter:08d}",
                preset_id=preset_id,
                target=target_enum.value,
                frame_number=self._tick_count,
                timestamp=_now(),
                parameters_snapshot={
                    pname: _to_jsonable(pentry)
                    for pname, pentry in preset.parameters.items()
                },
                result_url=f"assets://captures/{preset_id}_{self._capture_counter}.png",
                metadata={
                    "intensity": preset.intensity,
                    "blend_mode": preset.blend_mode,
                    "quality": preset.quality,
                },
            )
            self._captures[capture.capture_id] = capture
            _evict_fifo_dict(self._captures, self._config.max_captures)
            self._stats.total_applied += 1
            self._refresh_stats()
            # Restore the original intensity so the apply does not mutate
            # the preset permanently; callers that want a persistent
            # change should use update_preset.
            preset.intensity = original_intensity
            preset.updated_at = _now()
            self._emit(
                VisualFilterEventKind.APPLIED.value,
                preset_id,
                f"Applied preset '{preset.name}' to {target_enum.value}",
                {"target": target_enum.value, "capture_id": capture.capture_id},
            )
            return True, "applied", capture

    def revert_filter(self, target: str = FilterTarget.VIEWPORT.value) -> Tuple[bool, str]:
        """Revert the active filter for a target.

        Returns:
            A ``(ok, message)`` tuple. Fails when no filter is active.
        """
        with self._lock:
            target_enum = _coerce_enum(FilterTarget, target, FilterTarget.VIEWPORT)
            active_id = self._active_filters.get(target_enum.value)
            if not active_id:
                return False, "no active filter for target"
            del self._active_filters[target_enum.value]
            self._stats.total_reverted += 1
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.REVERTED.value,
                active_id,
                f"Reverted filter on {target_enum.value}",
                {"target": target_enum.value},
            )
            return True, "reverted"

    def capture_filtered(
        self,
        target: str = "viewport",
        preset_id: str = "",
        frame_number: int = 0,
    ) -> Tuple[bool, str, Optional[FilterCapture]]:
        """Capture a filtered frame for a target.

        When ``preset_id`` is empty the currently active filter for the
        target is captured. When ``preset_id`` is provided that preset is
        captured without changing the active filter.

        Returns:
            A ``(ok, message, capture)`` tuple.
        """
        with self._lock:
            target_enum = _coerce_enum(FilterTarget, target, FilterTarget.VIEWPORT)
            effective_preset_id = preset_id or self._active_filters.get(
                target_enum.value, ""
            )
            if not effective_preset_id:
                return False, "no preset to capture", None
            preset = self._resolve_preset(effective_preset_id)
            if preset is None:
                return False, "preset not found", None
            self._capture_counter += 1
            capture = FilterCapture(
                capture_id=f"fcap_{self._capture_counter:08d}",
                preset_id=effective_preset_id,
                target=target_enum.value,
                frame_number=_safe_int(frame_number, self._tick_count),
                timestamp=_now(),
                parameters_snapshot={
                    pname: _to_jsonable(pentry)
                    for pname, pentry in preset.parameters.items()
                },
                result_url=f"assets://captures/{effective_preset_id}_{self._capture_counter}.png",
                metadata={
                    "intensity": preset.intensity,
                    "blend_mode": preset.blend_mode,
                    "quality": preset.quality,
                },
            )
            self._captures[capture.capture_id] = capture
            _evict_fifo_dict(self._captures, self._config.max_captures)
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.APPLIED.value,
                effective_preset_id,
                f"Captured filtered frame for {target_enum.value}",
                {"target": target_enum.value, "capture_id": capture.capture_id},
            )
            return True, "captured", capture

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def create_transition(
        self,
        transition_id: str,
        from_preset_id: str,
        to_preset_id: str,
        duration: float = 1.0,
        easing: str = "linear",
    ) -> Tuple[bool, str, Optional[FilterTransition]]:
        """Create a transition between two presets.

        Returns:
            A ``(ok, message, transition)`` tuple.
        """
        if not transition_id:
            return False, "transition_id is required", None
        with self._lock:
            if transition_id in self._transitions:
                return False, "transition_id already exists", None
            if len(self._transitions) >= _MAX_TRANSITIONS:
                _evict_fifo_dict(self._transitions, _MAX_TRANSITIONS)
            if from_preset_id and from_preset_id not in self._presets:
                return False, "from_preset not found", None
            if to_preset_id and to_preset_id not in self._presets:
                return False, "to_preset not found", None
            transition = FilterTransition(
                transition_id=transition_id,
                from_preset_id=from_preset_id,
                to_preset_id=to_preset_id,
                duration=max(0.0, _safe_float(duration, 1.0)),
                easing=easing or "linear",
                active=False,
                progress=0.0,
                created_at=_now(),
            )
            self._transitions[transition_id] = transition
            self._emit(
                VisualFilterEventKind.CREATED.value,
                "",
                f"Created transition '{transition_id}'",
                {"transition_id": transition_id},
            )
            return True, "created", transition

    def get_transition(self, transition_id: str) -> Optional[FilterTransition]:
        """Retrieve a transition by its identifier."""
        with self._lock:
            return self._transitions.get(transition_id)

    def list_transitions(
        self,
        active_only: Optional[bool] = None,
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> List[FilterTransition]:
        """List transitions with an optional active-state filter.

        Args:
            active_only: When ``True`` return only active transitions; when
                ``False`` return only inactive ones; when ``None`` return
                all transitions regardless of active state.
            limit: Maximum number of transitions to return.

        Returns:
            A list of matching FilterTransition objects.
        """
        with self._lock:
            cap = max(1, min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT))
            results: List[FilterTransition] = []
            for transition in self._transitions.values():
                if active_only is True and not transition.active:
                    continue
                if active_only is False and transition.active:
                    continue
                results.append(transition)
                if len(results) >= cap:
                    break
            return results

    def update_transition(
        self, transition_id: str, progress: float
    ) -> Tuple[bool, str, Optional[FilterTransition]]:
        """Update the progress of a transition.

        Progress is clamped to ``[0.0, 1.0]``. When progress reaches 1.0
        the transition is marked inactive. When progress moves above 0.0
        the transition is marked active.

        Returns:
            A ``(ok, message, transition)`` tuple.
        """
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return False, "not found", None
            transition.progress = _clamp(_safe_float(progress, 0.0), 0.0, 1.0)
            transition.active = 0.0 < transition.progress < 1.0
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                "",
                f"Updated transition '{transition_id}' progress to {transition.progress}",
                {"transition_id": transition_id, "progress": transition.progress},
            )
            return True, "updated", transition

    def remove_transition(self, transition_id: str) -> Tuple[bool, str]:
        """Remove a transition by its identifier.

        Returns:
            A ``(ok, message)`` tuple.
        """
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return False, "not found"
            del self._transitions[transition_id]
            self._emit(
                VisualFilterEventKind.REMOVED.value,
                "",
                f"Removed transition '{transition_id}'",
                {"transition_id": transition_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Comparisons
    # ------------------------------------------------------------------

    def compare_presets(
        self, preset_ids: List[str]
    ) -> Tuple[bool, str, Optional[FilterComparison]]:
        """Compute parameter deltas across two or more presets.

        Produces a FilterComparison mapping each parameter name to a
        tuple of values (one per preset, in input order). Parameters
        absent from a preset contribute their default value.

        Returns:
            A ``(ok, message, comparison)`` tuple. Fails when fewer than
            two valid presets are provided.
        """
        with self._lock:
            if not preset_ids or len(preset_ids) < 2:
                return False, "at least two preset ids are required", None
            resolved: List[FilterPreset] = []
            missing: List[str] = []
            for pid in preset_ids:
                preset = self._resolve_preset(pid)
                if preset is None:
                    missing.append(pid)
                else:
                    resolved.append(preset)
            if missing:
                return False, f"presets not found: {', '.join(missing)}", None
            if len(resolved) < 2:
                return False, "at least two valid presets are required", None
            # Gather the union of parameter names across all presets.
            all_params: set = set()
            for preset in resolved:
                all_params.update(preset.parameters.keys())
            # Also include every canonical parameter so the comparison
            # always shows the full tunable surface.
            all_params.update(_PARAMETER_BOUNDS.keys())
            deltas: Dict[str, Tuple[float, ...]] = {}
            for pname in sorted(all_params):
                values: List[float] = []
                for preset in resolved:
                    entry = preset.parameters.get(pname)
                    if entry is not None:
                        values.append(entry.value)
                    else:
                        values.append(_parameter_bounds(pname)[2])
                deltas[pname] = tuple(values)
            comparison = FilterComparison(
                comparison_id=_new_id("cmp"),
                preset_ids=[p.preset_id for p in resolved],
                parameter_deltas=deltas,
                created_at=_now(),
            )
            self._comparisons[comparison.comparison_id] = comparison
            _evict_fifo_dict(self._comparisons, _MAX_COMPARISONS)
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                "",
                f"Compared presets {[p.preset_id for p in resolved]}",
                {"comparison_id": comparison.comparison_id},
            )
            return True, "compared", comparison

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_preset(
        self, preset_id: str, fmt: str = "json"
    ) -> Optional[Dict[str, Any]]:
        """Export a preset to a serializable dict.

        Args:
            preset_id: The preset to export.
            fmt: Serialization format. Only "json" is supported.

        Returns:
            A dict representation of the preset, or None when the preset
            is missing or the format is unsupported.
        """
        with self._lock:
            preset = self._resolve_preset(preset_id)
            if preset is None:
                return None
            if fmt.lower() != "json":
                return None
            data = preset.to_dict()
            data["_export_format"] = "json"
            data["_export_version"] = "1.0.0"
            self._emit(
                VisualFilterEventKind.EXPORTED.value,
                preset_id,
                f"Exported preset '{preset.name}' as {fmt}",
                {"format": fmt},
            )
            return data

    def import_preset(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[FilterPreset]]:
        """Import a preset from a serialized dict.

        The dict must contain at least ``preset_id`` and ``name``. Any
        ``parameters`` mapping is reconstructed as FilterParameterEntry
        objects. A new preset id is generated when the incoming id
        already exists to avoid clobbering.

        Returns:
            A ``(ok, message, preset)`` tuple.
        """
        if not isinstance(data, dict):
            return False, "data must be a dict", None
        with self._lock:
            preset_id = str(data.get("preset_id", "")).strip()
            if not preset_id:
                preset_id = _new_id("preset")
            # Avoid clobbering an existing preset.
            if preset_id in self._presets:
                preset_id = f"{preset_id}_{_new_id()}"
            name = str(data.get("name", preset_id))
            preset_type = data.get("preset_type", FilterPresetType.CUSTOM.value)
            description = str(data.get("description", ""))
            category = data.get("category", FilterCategory.CUSTOM.value)
            blend_mode = data.get("blend_mode", FilterBlendMode.NORMAL.value)
            quality = data.get("quality", FilterQuality.MEDIUM.value)
            intensity = data.get("intensity", 1.0)
            enabled = bool(data.get("enabled", True))
            tags = list(data.get("tags", []))
            thumbnail_url = str(data.get("thumbnail_url", ""))
            lut_path = str(data.get("lut_path", ""))
            metadata = dict(data.get("metadata", {}))
            metadata["imported"] = True
            parameters = data.get("parameters")
            ok, msg, preset = self.register_preset(
                preset_id=preset_id,
                name=name,
                preset_type=preset_type,
                description=description,
                category=category,
                parameters=parameters if isinstance(parameters, dict) else None,
                blend_mode=blend_mode,
                quality=quality,
                intensity=intensity,
                enabled=enabled,
                tags=tags,
                thumbnail_url=thumbnail_url,
                lut_path=lut_path,
                metadata=metadata,
            )
            if not ok or preset is None:
                return False, msg, None
            self._emit(
                VisualFilterEventKind.IMPORTED.value,
                preset_id,
                f"Imported preset '{preset.name}'",
                {"preset_id": preset_id},
            )
            return True, "imported", preset

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def auto_generate_filter(
        self,
        description: str,
        name: str = "",
        category: str = FilterCategory.CUSTOM.value,
    ) -> Tuple[bool, str, Optional[FilterPreset]]:
        """AI-generate a filter preset from a natural-language description.

        The generator inspects the description for keywords (horror,
        vibrant, retro, dreamy, watercolor, cinematic, noir, vintage,
        cyberpunk, pastel, warm, cool, dark, bright, cheerful, cartoon,
        synthwave) and assembles a preset with parameters appropriate to
        the detected theme. When no theme is recognized a neutral preset
        is produced with mild color correction.

        Args:
            description: A natural-language description of the desired look
                (e.g. "dark and moody horror", "bright cheerful cartoon",
                "retro 80s synthwave").
            name: Optional display name. When empty a name is derived from
                the description.
            category: The FilterCategory value name for the new preset.

        Returns:
            A ``(ok, message, preset)`` tuple.
        """
        with self._lock:
            if not description or not description.strip():
                return False, "description must not be empty", None
            desc_lower = description.lower()
            preset_id = _new_id("ai_filter")
            derived_name = name or f"AI Filter {preset_id[:8]}"
            now = _now()

            # Determine theme and parameter set from keywords. Each theme
            # contributes a dict of parameter -> value that evokes the
            # named style. Multiple matching keywords accumulate so a
            # description like "dark retro" combines both influences.
            theme_parts: List[str] = []
            params: Dict[str, float] = {}

            if "horror" in desc_lower or "dread" in desc_lower or "nightmare" in desc_lower:
                theme_parts.append("horror")
                params.update({
                    FilterParameter.BRIGHTNESS.value: 0.8,
                    FilterParameter.CONTRAST.value: 1.5,
                    FilterParameter.SATURATION.value: 0.6,
                    FilterParameter.GRAIN.value: 0.5,
                    FilterParameter.VIGNETTE.value: 0.6,
                    FilterParameter.NOISE.value: 0.2,
                })
            if "dark" in desc_lower or "moody" in desc_lower or "gloomy" in desc_lower:
                theme_parts.append("dark")
                params[FilterParameter.BRIGHTNESS.value] = min(
                    params.get(FilterParameter.BRIGHTNESS.value, 1.0), 0.85
                )
                params[FilterParameter.CONTRAST.value] = max(
                    params.get(FilterParameter.CONTRAST.value, 1.0), 1.3
                )
                params[FilterParameter.VIGNETTE.value] = max(
                    params.get(FilterParameter.VIGNETTE.value, 0.0), 0.4
                )
            if "vibrant" in desc_lower or "saturated" in desc_lower or "punchy" in desc_lower:
                theme_parts.append("vibrant")
                params.update({
                    FilterParameter.SATURATION.value: 1.5,
                    FilterParameter.CONTRAST.value: 1.2,
                    FilterParameter.BRIGHTNESS.value: 1.05,
                    FilterParameter.SHARPNESS.value: 1.1,
                })
            if "bright" in desc_lower or "cheerful" in desc_lower or "cartoon" in desc_lower:
                theme_parts.append("bright")
                params[FilterParameter.BRIGHTNESS.value] = max(
                    params.get(FilterParameter.BRIGHTNESS.value, 1.0), 1.1
                )
                params[FilterParameter.SATURATION.value] = max(
                    params.get(FilterParameter.SATURATION.value, 1.0), 1.3
                )
                params[FilterParameter.CONTRAST.value] = max(
                    params.get(FilterParameter.CONTRAST.value, 1.0), 1.15
                )
            if "retro" in desc_lower or "80s" in desc_lower or "synthwave" in desc_lower:
                theme_parts.append("retro")
                params.update({
                    FilterParameter.SCANLINE.value: 0.3,
                    FilterParameter.PIXELATE.value: 0.1,
                    FilterParameter.TEMPERATURE.value: 0.4,
                    FilterParameter.SATURATION.value: max(
                        params.get(FilterParameter.SATURATION.value, 1.0), 1.2
                    ),
                    FilterParameter.CONTRAST.value: max(
                        params.get(FilterParameter.CONTRAST.value, 1.0), 1.1
                    ),
                })
            if "dreamy" in desc_lower or "soft" in desc_lower or "ethereal" in desc_lower:
                theme_parts.append("dreamy")
                params.update({
                    FilterParameter.BLOOM.value: 0.4,
                    FilterParameter.DEPTH_OF_FIELD.value: 0.3,
                    FilterParameter.CONTRAST.value: 0.85,
                    FilterParameter.BRIGHTNESS.value: 1.1,
                    FilterParameter.SATURATION.value: 1.1,
                })
            if "watercolor" in desc_lower or "paint" in desc_lower or "painted" in desc_lower:
                theme_parts.append("watercolor")
                params.update({
                    FilterParameter.POSTERIZE.value: 0.2,
                    FilterParameter.BLOOM.value: 0.2,
                    FilterParameter.SATURATION.value: 1.15,
                    FilterParameter.CONTRAST.value: 0.8,
                    FilterParameter.BRIGHTNESS.value: 1.05,
                })
            if "cinematic" in desc_lower or "film" in desc_lower or "movie" in desc_lower:
                theme_parts.append("cinematic")
                params.update({
                    FilterParameter.CONTRAST.value: 1.15,
                    FilterParameter.SATURATION.value: 1.1,
                    FilterParameter.TEMPERATURE.value: 0.1,
                    FilterParameter.TINT.value: -0.05,
                    FilterParameter.VIGNETTE.value: 0.3,
                    FilterParameter.BLOOM.value: 0.15,
                    FilterParameter.SHARPNESS.value: 1.05,
                })
            if "noir" in desc_lower or "monochrome" in desc_lower or "black and white" in desc_lower:
                theme_parts.append("noir")
                params.update({
                    FilterParameter.SATURATION.value: 0.0,
                    FilterParameter.CONTRAST.value: 1.4,
                    FilterParameter.GRAIN.value: 0.4,
                    FilterParameter.VIGNETTE.value: 0.5,
                    FilterParameter.SHARPNESS.value: 1.1,
                })
            if "vintage" in desc_lower or "faded" in desc_lower or " old " in f" {desc_lower} ":
                theme_parts.append("vintage")
                params.update({
                    FilterParameter.SATURATION.value: 0.75,
                    FilterParameter.CONTRAST.value: 0.9,
                    FilterParameter.TEMPERATURE.value: 0.3,
                    FilterParameter.VIGNETTE.value: 0.35,
                    FilterParameter.GRAIN.value: 0.25,
                    FilterParameter.GAMMA.value: 1.1,
                })
            if "cyberpunk" in desc_lower or "neon" in desc_lower:
                theme_parts.append("cyberpunk")
                params.update({
                    FilterParameter.CONTRAST.value: 1.4,
                    FilterParameter.SATURATION.value: 1.6,
                    FilterParameter.BRIGHTNESS.value: 0.9,
                    FilterParameter.CHROMATIC_ABERRATION.value: 0.3,
                    FilterParameter.BLOOM.value: 0.35,
                    FilterParameter.TINT.value: 0.1,
                })
            if "pastel" in desc_lower:
                theme_parts.append("pastel")
                params.update({
                    FilterParameter.SATURATION.value: 0.85,
                    FilterParameter.BRIGHTNESS.value: 1.1,
                    FilterParameter.CONTRAST.value: 0.8,
                    FilterParameter.BLOOM.value: 0.15,
                })
            if "warm" in desc_lower or "golden" in desc_lower or "sunset" in desc_lower:
                theme_parts.append("warm")
                params[FilterParameter.TEMPERATURE.value] = max(
                    params.get(FilterParameter.TEMPERATURE.value, 0.0), 0.35
                )
                params[FilterParameter.TINT.value] = min(
                    params.get(FilterParameter.TINT.value, 0.0), -0.05
                )
            if "cool" in desc_lower or "cold" in desc_lower or "blue" in desc_lower:
                theme_parts.append("cool")
                params[FilterParameter.TEMPERATURE.value] = min(
                    params.get(FilterParameter.TEMPERATURE.value, 0.0), -0.35
                )
                params[FilterParameter.TINT.value] = max(
                    params.get(FilterParameter.TINT.value, 0.0), 0.05
                )

            if not theme_parts:
                # Neutral fallback: mild color correction baseline.
                theme_parts.append("neutral")
                params.update({
                    FilterParameter.CONTRAST.value: 1.05,
                    FilterParameter.SATURATION.value: 1.05,
                    FilterParameter.SHARPNESS.value: 1.02,
                })

            theme = "-".join(theme_parts)
            # Choose a preset type from the dominant theme.
            preset_type = self._theme_to_preset_type(theme_parts[0])
            quality = FilterQuality.MEDIUM.value
            if any(t in theme_parts for t in ("cinematic", "noir", "horror", "cyberpunk")):
                quality = FilterQuality.HIGH.value
            # Apply global grain/vignette toggles from config.
            if not self._config.enable_grain:
                params.pop(FilterParameter.GRAIN.value, None)
            if not self._config.enable_vignette:
                params.pop(FilterParameter.VIGNETTE.value, None)

            preset = FilterPreset(
                preset_id=preset_id,
                name=derived_name,
                description=f"AI-generated {theme} filter: {description[:140]}",
                preset_type=preset_type,
                category=category,
                parameters={
                    pname: _make_parameter_entry(pname, pval)
                    for pname, pval in params.items()
                },
                blend_mode=FilterBlendMode.NORMAL.value,
                quality=quality,
                intensity=1.0,
                enabled=True,
                tags=["ai_generated"] + theme_parts,
                thumbnail_url="",
                lut_path="",
                created_at=now,
                updated_at=now,
                metadata={
                    "ai_generated": True,
                    "ai_theme": theme,
                    "ai_description": description[:200],
                },
            )
            self._presets[preset_id] = preset
            _evict_fifo_dict(self._presets, self._config.max_presets)
            self._refresh_stats()
            self._emit(
                VisualFilterEventKind.CREATED.value,
                preset_id,
                f"AI generated {theme} filter '{derived_name}'",
                {"theme": theme, "parameter_count": len(params)},
            )
            return True, "generated", preset

    def _theme_to_preset_type(self, theme: str) -> str:
        """Map a detected theme keyword to a FilterPresetType value."""
        mapping = {
            "horror": FilterPresetType.HORROR.value,
            "dark": FilterPresetType.HORROR.value,
            "vibrant": FilterPresetType.VIBRANT.value,
            "bright": FilterPresetType.VIBRANT.value,
            "retro": FilterPresetType.RETRO.value,
            "dreamy": FilterPresetType.DREAMY.value,
            "watercolor": FilterPresetType.WATERCOLOR.value,
            "cinematic": FilterPresetType.CINEMATIC.value,
            "noir": FilterPresetType.NOIR.value,
            "vintage": FilterPresetType.VINTAGE.value,
            "cyberpunk": FilterPresetType.CYBERPUNK.value,
            "pastel": FilterPresetType.PASTEL.value,
            "warm": FilterPresetType.WARM.value,
            "cool": FilterPresetType.COOL.value,
            "neutral": FilterPresetType.NEUTRAL.value,
        }
        return mapping.get(theme, FilterPresetType.CUSTOM.value)

    def suggest_parameters(
        self, preset_id: str
    ) -> Tuple[bool, str, List[str]]:
        """AI-suggest which parameters a designer should adjust next.

        Inspects the current parameter values of a preset and proposes
        the next parameters to tune. The heuristic prefers parameters
        that are at their default value (untouched), then parameters
        whose effect would round out the preset's look (for example,
        suggesting vignette when contrast is high, or grain when a
        stylized preset has none).

        Args:
            preset_id: The preset to inspect.

        Returns:
            A ``(ok, message, parameters)`` tuple where ``parameters`` is
            a list of parameter names ordered by suggestion priority.
        """
        with self._lock:
            preset = self._resolve_preset(preset_id)
            if preset is None:
                return False, "preset not found", []
            suggestions: List[str] = []
            reasons: Dict[str, int] = {}
            # Collect every canonical parameter and its current value.
            current_values: Dict[str, float] = {}
            for pname in _PARAMETER_BOUNDS.keys():
                entry = preset.parameters.get(pname)
                if entry is not None:
                    current_values[pname] = entry.value
                else:
                    current_values[pname] = _parameter_bounds(pname)[2]
            # 1. Suggest untouched stylized parameters first (still at
            #    their default value), since those are the most impactful
            #    next edits for a designer shaping a look.
            stylized_params = [
                FilterParameter.VIGNETTE.value,
                FilterParameter.BLOOM.value,
                FilterParameter.GRAIN.value,
                FilterParameter.CHROMATIC_ABERRATION.value,
                FilterParameter.DEPTH_OF_FIELD.value,
                FilterParameter.SCANLINE.value,
                FilterParameter.POSTERIZE.value,
            ]
            for pname in stylized_params:
                default = _parameter_bounds(pname)[2]
                if abs(current_values.get(pname, default) - default) < 1e-6:
                    reasons[pname] = reasons.get(pname, 0) + 3
            # 2. Suggest vignette when the preset is high-contrast.
            contrast_val = current_values.get(
                FilterParameter.CONTRAST.value, 1.0
            )
            if contrast_val > 1.2 and current_values.get(
                FilterParameter.VIGNETTE.value, 0.0
            ) < 0.05:
                reasons[FilterParameter.VIGNETTE.value] = (
                    reasons.get(FilterParameter.VIGNETTE.value, 0) + 2
                )
            # 3. Suggest grain for stylized presets that have none.
            preset_type = preset.preset_type
            if preset_type in (
                FilterPresetType.NOIR.value,
                FilterPresetType.HORROR.value,
                FilterPresetType.VINTAGE.value,
                FilterPresetType.RETRO.value,
            ):
                if current_values.get(FilterParameter.GRAIN.value, 0.0) < 0.1:
                    reasons[FilterParameter.GRAIN.value] = (
                        reasons.get(FilterParameter.GRAIN.value, 0) + 2
                    )
            # 4. Suggest temperature/tint for color-graded presets that
            #    are still neutral.
            if preset_type in (
                FilterPresetType.CINEMATIC.value,
                FilterPresetType.VINTAGE.value,
                FilterPresetType.WARM.value,
                FilterPresetType.COOL.value,
            ):
                if abs(current_values.get(
                    FilterParameter.TEMPERATURE.value, 0.0
                )) < 0.05:
                    reasons[FilterParameter.TEMPERATURE.value] = (
                        reasons.get(FilterParameter.TEMPERATURE.value, 0) + 2
                    )
            # 5. Suggest saturation for monochrome-leaning presets.
            sat_val = current_values.get(FilterParameter.SATURATION.value, 1.0)
            if sat_val < 0.2 and preset_type != FilterPresetType.NOIR.value:
                reasons[FilterParameter.SATURATION.value] = (
                    reasons.get(FilterParameter.SATURATION.value, 0) + 2
                )
            # 6. Suggest sharpness when bloom or depth of field is high
            #    (to recover perceived detail).
            if current_values.get(FilterParameter.BLOOM.value, 0.0) > 0.3 or \
               current_values.get(FilterParameter.DEPTH_OF_FIELD.value, 0.0) > 0.3:
                reasons[FilterParameter.SHARPNESS.value] = (
                    reasons.get(FilterParameter.SHARPNESS.value, 0) + 1
                )
            # 7. Suggest exposure when brightness is at an extreme.
            bright_val = current_values.get(FilterParameter.BRIGHTNESS.value, 1.0)
            if bright_val < 0.85 or bright_val > 1.15:
                reasons[FilterParameter.EXPOSURE.value] = (
                    reasons.get(FilterParameter.EXPOSURE.value, 0) + 1
                )
            # Order suggestions by descending priority then by canonical
            # parameter order.
            ordered = sorted(
                reasons.items(),
                key=lambda kv: (-kv[1], kv[0]),
            )
            suggestions = [pname for pname, _ in ordered]
            # Always ensure at least one suggestion.
            if not suggestions:
                suggestions = [FilterParameter.CONTRAST.value]
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                preset_id,
                f"Suggested {len(suggestions)} parameters for '{preset.name}'",
                {"suggestions": suggestions[:8]},
            )
            return True, "suggested", suggestions

    def optimize_filter(
        self, preset_id: str, target_fps: int = 60
    ) -> Tuple[bool, str, Optional[FilterPreset]]:
        """AI-optimize a filter for performance at a target frame rate.

        Reduces or disables the most expensive effects (bloom, depth of
        field, motion blur, chromatic aberration, pixelate) so the filter
        is likely to hit the target frame rate. Higher target frame rates
        trigger more aggressive reductions. The preset's quality tier is
        also lowered when the target is demanding.

        Args:
            preset_id: The preset to optimize.
            target_fps: The frame rate the filter should be optimized for.

        Returns:
            A ``(ok, message, preset)`` tuple.
        """
        with self._lock:
            preset = self._resolve_preset(preset_id)
            if preset is None:
                return False, "preset not found", None
            fps = max(1, _safe_int(target_fps, 60))
            now = _now()
            # Expensive effects and how aggressively to scale them.
            expensive_params = [
                FilterParameter.BLOOM.value,
                FilterParameter.DEPTH_OF_FIELD.value,
                FilterParameter.MOTION_BLUR.value,
                FilterParameter.CHROMATIC_ABERRATION.value,
                FilterParameter.PIXELATE.value,
                FilterParameter.NOISE.value,
            ]
            # Reduction factor: higher target fps -> more reduction.
            if fps >= 120:
                factor = 0.3
                new_quality = FilterQuality.LOW.value
            elif fps >= 90:
                factor = 0.5
                new_quality = FilterQuality.LOW.value
            elif fps >= 60:
                factor = 0.7
                new_quality = FilterQuality.MEDIUM.value
            else:
                factor = 0.9
                new_quality = FilterQuality.MEDIUM.value
            changes: List[str] = []
            for pname in expensive_params:
                entry = preset.parameters.get(pname)
                if entry is None:
                    continue
                if entry.value <= 0.0:
                    continue
                original = entry.value
                entry.value = round(_clamp(original * factor, 0.0, entry.max_value), 4)
                if entry.value < 0.05:
                    entry.enabled = False
                    entry.value = 0.0
                changes.append(
                    f"{pname}: {original:.3f}->{entry.value:.3f}"
                )
            # Lower the quality tier when the target is demanding.
            old_quality = preset.quality
            preset.quality = new_quality
            if old_quality != new_quality:
                changes.append(f"quality: {old_quality}->{new_quality}")
            preset.metadata["ai_optimized"] = True
            preset.metadata["ai_target_fps"] = fps
            preset.metadata["ai_changes"] = changes
            preset.updated_at = now
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                preset_id,
                f"AI optimized '{preset.name}' for {fps} fps",
                {"target_fps": fps, "changes": changes},
            )
            return True, "optimized", preset

    # ------------------------------------------------------------------
    # System Lifecycle
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_presets": len(self._presets),
                "total_stacks": len(self._stacks),
                "total_luts": len(self._luts),
                "total_captures": len(self._captures),
                "total_transitions": len(self._transitions),
                "total_comparisons": len(self._comparisons),
                "total_events": len(self._events),
                "active_filters": dict(self._active_filters),
                "active_stacks": sum(
                    1 for s in self._stacks.values() if s.active
                ),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> VisualFilterStats:
        """Return aggregate statistics (refreshed before return)."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> VisualFilterSnapshot:
        """Return an immutable snapshot of the whole system.

        The preset, capture, and event lists are bounded so the snapshot
        stays reasonably sized for transmission and logging.
        """
        with self._lock:
            self._refresh_stats()
            return VisualFilterSnapshot(
                timestamp=_now(),
                presets=[
                    p.to_dict() for p in list(self._presets.values())[:50]
                ],
                stacks=[
                    s.to_dict() for s in list(self._stacks.values())[:50]
                ],
                luts=[
                    l.to_dict() for l in list(self._luts.values())[:50]
                ],
                captures=[
                    c.to_dict() for c in list(self._captures.values())[:50]
                ],
                events=[
                    e.to_dict() for e in list(self._events)[-50:]
                ],
                stats=self._stats.to_dict(),
            )

    def get_config(self) -> VisualFilterConfig:
        """Return the current runtime configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, VisualFilterConfig]:
        """Update runtime configuration fields.

        Accepts any subset of VisualFilterConfig fields. Numeric fields
        are coerced; boolean fields are coerced; enum-typed fields
        (``default_quality``, ``default_target``) are coerced via their
        respective enums.
        """
        with self._lock:
            for key in ("max_presets", "max_stacks", "max_luts",
                        "max_captures", "max_events"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(
                        self._config, key,
                        max(1, _safe_int(kwargs[key], getattr(self._config, key))),
                    )
            for key in ("auto_apply_default", "enable_grain", "enable_vignette"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key, bool(kwargs[key]))
            if "default_quality" in kwargs and kwargs["default_quality"] is not None:
                enum_val = _coerce_enum(
                    FilterQuality, kwargs["default_quality"], None
                )
                if enum_val is not None:
                    self._config.default_quality = enum_val.value
            if "default_target" in kwargs and kwargs["default_target"] is not None:
                enum_val = _coerce_enum(
                    FilterTarget, kwargs["default_target"], None
                )
                if enum_val is not None:
                    self._config.default_target = enum_val.value
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                if isinstance(kwargs["metadata"], dict):
                    self._config.metadata.update(kwargs["metadata"])
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                "",
                "Configuration updated",
            )
            return True, "updated", self._config

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the system by one frame.

        Performs housekeeping: refreshes statistics, trims the event log
        and capture store to capacity, advances active transitions by the
        elapsed time, and reports the current frame state.

        Args:
            dt: Delta time in seconds since the last tick.

        Returns:
            A dict describing the post-tick system state.
        """
        with self._lock:
            self._tick_count += 1
            _evict_fifo_list(self._events, self._config.max_events)
            _evict_fifo_dict(self._captures, self._config.max_captures)
            self._refresh_stats()
            dt_value = _safe_float(dt, 0.016)
            # Advance active transitions.
            completed_transitions = 0
            for transition in self._transitions.values():
                if not transition.active:
                    continue
                if transition.duration <= 0.0:
                    transition.progress = 1.0
                else:
                    transition.progress = _clamp(
                        transition.progress + (dt_value / transition.duration),
                        0.0, 1.0,
                    )
                if transition.progress >= 1.0:
                    transition.active = False
                    completed_transitions += 1
            result = {
                "tick": self._tick_count,
                "dt": dt_value,
                "total_presets": len(self._presets),
                "total_stacks": len(self._stacks),
                "total_captures": len(self._captures),
                "active_transitions": sum(
                    1 for t in self._transitions.values() if t.active
                ),
                "completed_transitions": completed_transitions,
                "total_applied": self._stats.total_applied,
                "total_reverted": self._stats.total_reverted,
            }
            self._emit(
                VisualFilterEventKind.UPDATED.value,
                "",
                f"Tick {self._tick_count}",
                result,
            )
            return result

    def reset(self) -> None:
        """Clear all stores and re-seed with default data."""
        with self._lock:
            self._presets.clear()
            self._stacks.clear()
            self._luts.clear()
            self._captures.clear()
            self._transitions.clear()
            self._comparisons.clear()
            self._events.clear()
            self._active_filters.clear()
            self._config = VisualFilterConfig()
            self._stats = VisualFilterStats()
            self._tick_count = 0
            self._event_counter = 0
            self._capture_counter = 0
            self._initialized = False
            self._emit(
                VisualFilterEventKind.REMOVED.value,
                "",
                "System reset",
            )
            self._seed()
            self._initialized = True

    def list_events(self, limit: int = 100) -> List[VisualFilterEvent]:
        """Return the most recent audit events (newest last)."""
        with self._lock:
            cap = min(
                _safe_int(limit, _DEFAULT_LIST_LIMIT), self._config.max_events
            )
            cap = max(1, cap)
            return list(self._events[-cap:])


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_visual_filter_system() -> VisualFilterSystem:
    """Return the shared VisualFilterSystem singleton instance."""
    return VisualFilterSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "FilterPresetType",
    "FilterParameter",
    "FilterCategory",
    "FilterBlendMode",
    "FilterQuality",
    "FilterStatus",
    "FilterLUTFormat",
    "FilterTarget",
    "VisualFilterEventKind",
    # Data classes
    "FilterParameterEntry",
    "FilterPreset",
    "FilterStack",
    "FilterLUT",
    "FilterCapture",
    "VisualFilterConfig",
    "VisualFilterStats",
    "VisualFilterSnapshot",
    "VisualFilterEvent",
    "FilterTransition",
    "FilterComparison",
    # Main system
    "VisualFilterSystem",
    "get_visual_filter_system",
]
