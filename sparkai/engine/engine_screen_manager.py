"""
SparkLabs Engine - Screen Manager and Scale System

A comprehensive screen management subsystem for the SparkLabs AI-native
game engine. It provides responsive game design across different screen
resolutions, aspect ratios, device orientations, and DPI scales, with
viewport management, letterboxing, and dynamic layout adaptation.

The screen manager is the single source of truth for how the game's
rendered content is mapped onto a physical (or simulated) display. It
addresses five overlapping concerns that every modern multi-platform
game engine must solve:

  1. Resolution Management
     ----------------------
     Different target devices expose wildly different native resolutions,
     from 1280x720 entry-level desktops up to 3840x2160 (4K) and even
     7680x4320 (8K) panels. The manager registers named ``ScreenMode``
     entries that capture the width, height, refresh rate, DPI and
     derived metadata (resolution tier, orientation, aspect ratio). A
     single mode is designated the *primary* mode and is used as the
     default reference for scaling and viewport placement.

  2. Aspect Ratio Handling
     ----------------------
     Two devices may share the same vertical resolution yet differ in
     aspect ratio (for example 1920x1080 at 16:9 versus 1920x1200 at
     16:10). The manager reduces every (width, height) pair to a
     simplified ratio such as "16:9" or "21:9" via a greatest-common-
     divisor computation, so layout code can branch on a stable string
     rather than fragile floating-point comparisons.

  3. Orientation
     ------------
     Mobile and tablet devices may be rotated freely between landscape
     and portrait. The manager tracks the *current* orientation of the
     game, derives a per-mode orientation from its dimensions, and emits
     an event whenever the global orientation is changed so that layout
     adaptations can be re-applied.

  4. DPI Scaling
     ------------
     A 4K panel driven at native resolution renders the same number of
     pixels as a 1080p panel at 200% OS scaling, yet the physical size
     of UI elements differs dramatically. Each screen mode records its
     physical DPI and a derived ``dpi_scale`` (dpi / 96.0). Layout
     adaptation and profiles consult the DPI awareness policy to decide
     whether elements are rendered at logical or physical sizes.

  5. Viewport, Letterboxing and Layout Adaptation
     ---------------------------------------------
     Fitting a design resolution into an arbitrary screen mode is solved
     by six classical scale modes (``ScaleMode``): EXACT_FIT, NO_BORDER,
     SHOW_ALL, RESIZE, FIT_WIDTH and FIT_HEIGHT. Each produces a
     ``ScaleResult`` describing the x/y scale factors, the rendered
     viewport dimensions, the sub-pixel offsets, and the letterbox bands
     on every edge. ``LetterboxPolicy`` controls what is drawn in the
     unused bands (nothing, black bars, a blurred copy of the frame, a
     stretched fill, or a gradient). ``Viewport`` entries describe
     independent sub-rectangles of the screen (the main game view, a
     minimap, a split-screen pane) and ``LayoutAdaptation`` entries
     describe how individual HUD elements are re-anchored, rescaled,
     shown, hidden or repositioned for a given mode and orientation.

Architecture:
  ScreenManagerEngine (Singleton)
    |-- ScreenMode          -- a registered display mode (resolution + DPI)
    |-- Viewport            -- an independent render sub-rectangle
    |-- LayoutAdaptation    -- per-mode/orientation element layout rules
    |-- ScreenProfile       -- a reusable bundle of mode + scale policy
    |-- ScaleResult         -- the computed scale/offset/letterbox for a fit
    |-- ScreenStats         -- aggregate counters describing the engine state
    |-- ScreenSnapshot      -- immutable snapshot of the whole engine
    |-- ScreenEvent         -- audit log entry for lifecycle changes
    |-- Orientation         -- landscape / portrait / auto
    |-- ScaleMode           -- six classical fit strategies
    |-- ResolutionTier      -- SD / HD / FULL_HD / QHD / UHD_4K / UHD_8K / CUSTOM
    |-- LetterboxPolicy     -- how to fill unused screen bands
    |-- DPIAwareness        -- unaware / aware / perceptible
    |-- ScreenEventKind     -- audit event kinds

Core Capabilities:
  - register_mode / list_modes / get_mode / get_primary_mode /
    set_primary_mode: screen mode registry with tier and aspect derivation.
  - create_viewport / list_viewports / get_viewport / update_viewport /
    remove_viewport: viewport sub-rectangle management with FIFO eviction.
  - compute_scale: compute scale factors, offsets and letterbox bands for
    any of the six scale modes against a target (design) resolution.
  - create_layout / list_layouts / get_layout: per-mode layout adaptations
    with anchor points, element scales, visibility and repositioning.
  - create_profile / list_profiles / get_profile / apply_profile: reusable
    scale/letterbox/DPI policy bundles.
  - get_orientation / set_orientation / get_aspect_ratio: orientation and
    aspect-ratio introspection.
  - list_events / get_stats / get_status / get_snapshot: observability.
  - reset: clear all stores and re-seed with default data.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ScreenManagerEngine.get_instance` or the module-level
:func:`get_screen_manager` factory. All public methods are guarded by
the re-entrant lock.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry
# is evicted in FIFO order to keep memory growth predictable under heavy
# dynamic use (for example a game that registers a new mode on every
# resolution change event).
_MAX_MODES: int = 500
_MAX_VIEWPORTS: int = 200
_MAX_LAYOUTS: int = 500
_MAX_PROFILES: int = 100
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    """Return the current time as a Unix epoch float.

    Used as the default factory for ``created_at`` / ``updated_at``
    fields and for event timestamps throughout the module.
    """
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with
            an underscore. When omitted, the bare hexadecimal id is
            returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to the inclusive ``[low, high]`` range.

    Args:
        value: The value to clamp.
        low: The inclusive lower bound.
        high: The inclusive upper bound.

    Returns:
        The clamped value.
    """
    if value < low:
        return low
    if value > high:
        return high
    return value


def _gcd(a: int, b: int) -> int:
    """Compute the greatest common divisor of two non-negative integers.

    Uses the iterative Euclidean algorithm. The result is used to reduce
    a (width, height) pair to a simplified aspect-ratio pair such as
    ``(16, 9)``. ``gcd(0, 0)`` is defined as ``0`` so that a degenerate
    zero-area mode collapses to ``"0:0"`` rather than raising.

    Args:
        a: First non-negative integer.
        b: Second non-negative integer.

    Returns:
        The greatest common divisor of ``a`` and ``b``.
    """
    a = abs(int(a))
    b = abs(int(b))
    while b:
        a, b = b, a % b
    return a


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class Orientation(Enum):
    """Screen orientation classification.

    ``AUTO`` indicates that the orientation should be derived from the
    active mode's dimensions rather than being forced.
    """

    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    AUTO = "auto"


class ScaleMode(Enum):
    """Strategies for fitting a design resolution into a screen mode.

    - ``EXACT_FIT``: scale x and y independently to fill the screen;
      distortion is acceptable and there is no letterbox.
    - ``NO_BORDER``: scale uniformly by the larger of the x/y factors so
      the screen is fully covered; overflow is cropped, no letterbox.
    - ``SHOW_ALL``: scale uniformly by the smaller factor so all content
      is visible; the remaining bands are letterboxed.
    - ``RESIZE``: do not scale; the viewport equals the screen size and
      the layout is expected to adapt to the available pixels.
    - ``FIT_WIDTH``: scale uniformly to match the screen width; excess
      vertical space is letterboxed top/bottom.
    - ``FIT_HEIGHT``: scale uniformly to match the screen height; excess
      horizontal space is letterboxed left/right.
    """

    EXACT_FIT = "exact_fit"
    NO_BORDER = "no_border"
    SHOW_ALL = "show_all"
    RESIZE = "resize"
    FIT_WIDTH = "fit_width"
    FIT_HEIGHT = "fit_height"


class ResolutionTier(Enum):
    """Coarse resolution classification by short-edge pixel count.

    The tier is derived from ``min(width, height)`` so that a portrait
    1080x1920 panel is still classified as ``FULL_HD`` (its short edge
    is 1080). ``CUSTOM`` covers anything that does not match a known
    tier boundary.
    """

    SD = "sd"
    HD = "hd"
    FULL_HD = "full_hd"
    QHD = "qhd"
    UHD_4K = "uhd_4k"
    UHD_8K = "uhd_8k"
    CUSTOM = "custom"


class LetterboxPolicy(Enum):
    """How the unused screen bands are rendered when content is letterboxed.

    - ``NONE``: no fill; the bands are left untouched (transparent).
    - ``BLACK_BARS``: classic cinematic black bars.
    - ``BLUR_FILL``: a blurred copy of the last rendered frame.
    - ``STRETCH_FILL``: the frame edges are stretched outward.
    - ``GRADIENT_FILL``: a themed gradient fading to the bars.
    """

    NONE = "none"
    BLACK_BARS = "black_bars"
    BLUR_FILL = "blur_fill"
    STRETCH_FILL = "stretch_fill"
    GRADIENT_FILL = "gradient_fill"


class DPIAwareness(Enum):
    """How the layout reacts to the physical DPI of a screen mode.

    - ``UNAWARE``: render at logical pixels; ignore DPI entirely.
    - ``AWARE``: account for DPI when sizing fixed-size elements.
    - ``PERCEPTIBLE``: DPI drives perceptible sizing so that a 4K panel
      shows more content rather than larger content.
    """

    UNAWARE = "unaware"
    AWARE = "aware"
    PERCEPTIBLE = "perceptible"


class ScreenEventKind(Enum):
    """Audit event kinds emitted by the screen manager."""

    MODE_CHANGED = "mode_changed"
    VIEWPORT_UPDATED = "viewport_updated"
    LAYOUT_ADAPTED = "layout_adapted"
    PROFILE_APPLIED = "profile_applied"
    ORIENTATION_CHANGED = "orientation_changed"
    SCALE_RECOMPUTED = "scale_recomputed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ScreenMode:
    """A registered display mode.

    Captures the physical properties of a screen configuration together
    with derived metadata (resolution tier, orientation, aspect ratio
    and DPI scale). Exactly one mode may be marked as the engine's
    primary mode at any time.

    Attributes:
        mode_id: Unique identifier for the mode.
        width: Horizontal resolution in pixels.
        height: Vertical resolution in pixels.
        refresh_rate: Nominal refresh rate in hertz.
        resolution_tier: Coarse resolution classification.
        orientation: Derived orientation from the dimensions.
        dpi: Physical dots-per-inch of the panel.
        dpi_scale: Derived scale factor (dpi / 96.0).
        aspect_ratio: Simplified aspect ratio string such as "16:9".
        is_primary: Whether this mode is the current primary mode.
        created_at: Timestamp when the mode was registered.
        metadata: Free-form extension data.
    """

    mode_id: str = field(default_factory=lambda: _new_id("mode"))
    width: int = 0
    height: int = 0
    refresh_rate: float = 60.0
    resolution_tier: ResolutionTier = ResolutionTier.CUSTOM
    orientation: Orientation = Orientation.LANDSCAPE
    dpi: float = 96.0
    dpi_scale: float = 1.0
    aspect_ratio: str = "16:9"
    is_primary: bool = False
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode_id": self.mode_id,
            "width": self.width,
            "height": self.height,
            "refresh_rate": self.refresh_rate,
            "resolution_tier": self.resolution_tier.value,
            "orientation": self.orientation.value,
            "dpi": self.dpi,
            "dpi_scale": self.dpi_scale,
            "aspect_ratio": self.aspect_ratio,
            "is_primary": self.is_primary,
            "created_at": self.created_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class Viewport:
    """An independent render sub-rectangle on the screen.

    A viewport describes where on the screen a particular camera or UI
    layer is rendered. Multiple viewports may share a single screen mode
    (for example a main game view plus a minimap). Viewports carry their
    own scale and rotation so that the same content can be rendered at
    different zoom levels in different rectangles.

    Attributes:
        viewport_id: Unique identifier for the viewport.
        name: Human-readable name of the viewport.
        x: Left edge of the viewport in screen pixels.
        y: Top edge of the viewport in screen pixels.
        width: Viewport width in screen pixels.
        height: Viewport height in screen pixels.
        scale_x: Horizontal render scale applied within the viewport.
        scale_y: Vertical render scale applied within the viewport.
        rotation: Viewport rotation in degrees.
        mode_id: Identifier of the screen mode this viewport belongs to.
        created_at: Timestamp when the viewport was created.
        updated_at: Timestamp when the viewport was last updated.
    """

    viewport_id: str = field(default_factory=lambda: _new_id("viewport"))
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    mode_id: str = ""
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "viewport_id": self.viewport_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "rotation": self.rotation,
            "mode_id": self.mode_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class LayoutAdaptation:
    """Per-mode/orientation layout rules for individual UI elements.

    A layout adaptation describes how the engine should re-anchor,
    rescale, show, hide or reposition named HUD/UI elements when a
    particular screen mode and orientation is active. Anchor points are
    expressed as dictionaries so that callers can attach arbitrary
    positioning metadata (for example ``{"x": 0.5, "y": 0.0}``).

    Attributes:
        layout_id: Unique identifier for the layout adaptation.
        name: Human-readable name of the layout.
        mode_id: Identifier of the screen mode this layout targets.
        orientation: Orientation this layout is designed for.
        anchor_points: Mapping of element name to anchor metadata.
        element_scales: Mapping of element name to a scale multiplier.
        visible_elements: Element names that should be shown.
        hidden_elements: Element names that should be hidden.
        repositioned_elements: Mapping of element name to new position.
        created_at: Timestamp when the layout was created.
    """

    layout_id: str = field(default_factory=lambda: _new_id("layout"))
    name: str = ""
    mode_id: str = ""
    orientation: Orientation = Orientation.LANDSCAPE
    anchor_points: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    element_scales: Dict[str, float] = field(default_factory=dict)
    visible_elements: List[str] = field(default_factory=list)
    hidden_elements: List[str] = field(default_factory=list)
    repositioned_elements: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "name": self.name,
            "mode_id": self.mode_id,
            "orientation": self.orientation.value,
            "anchor_points": {
                k: dict(v) if v else {} for k, v in self.anchor_points.items()
            },
            "element_scales": dict(self.element_scales) if self.element_scales else {},
            "visible_elements": list(self.visible_elements),
            "hidden_elements": list(self.hidden_elements),
            "repositioned_elements": {
                k: dict(v) if v else {} for k, v in self.repositioned_elements.items()
            },
            "created_at": self.created_at,
        }


@dataclass
class ScreenProfile:
    """A reusable bundle of screen policy settings.

    A profile ties a default screen mode to a scale mode, letterbox
    policy and DPI awareness policy, together with min/max supported
    dimensions. Applying a profile promotes its default mode to primary
    so that subsequent scaling and viewport operations use it.

    Attributes:
        profile_id: Unique identifier for the profile.
        name: Human-readable name of the profile.
        description: Long-form description of the profile.
        default_mode_id: Identifier of the mode to promote on apply.
        scale_mode: The default scale mode for the profile.
        letterbox_policy: The default letterbox policy for the profile.
        dpi_awareness: The DPI awareness policy for the profile.
        min_width: Minimum supported horizontal resolution.
        min_height: Minimum supported vertical resolution.
        max_width: Maximum supported horizontal resolution.
        max_height: Maximum supported vertical resolution.
        created_at: Timestamp when the profile was created.
        updated_at: Timestamp when the profile was last updated.
    """

    profile_id: str = field(default_factory=lambda: _new_id("profile"))
    name: str = ""
    description: str = ""
    default_mode_id: str = ""
    scale_mode: ScaleMode = ScaleMode.SHOW_ALL
    letterbox_policy: LetterboxPolicy = LetterboxPolicy.BLACK_BARS
    dpi_awareness: DPIAwareness = DPIAwareness.AWARE
    min_width: int = 320
    min_height: int = 240
    max_width: int = 7680
    max_height: int = 4320
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "default_mode_id": self.default_mode_id,
            "scale_mode": self.scale_mode.value,
            "letterbox_policy": self.letterbox_policy.value,
            "dpi_awareness": self.dpi_awareness.value,
            "min_width": self.min_width,
            "min_height": self.min_height,
            "max_width": self.max_width,
            "max_height": self.max_height,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ScaleResult:
    """The computed scale, offset and letterbox values for a fit.

    Returned by :meth:`ScreenManagerEngine.compute_scale`. The viewport
    width/height describe the rendered content rectangle inside the
    screen; the four letterbox values describe the unused bands on each
    edge. Offsets are the position of the viewport's top-left corner
    relative to the screen's top-left corner.

    Attributes:
        mode_id: Identifier of the screen mode used as the container.
        scale_x: Horizontal scale factor applied to the content.
        scale_y: Vertical scale factor applied to the content.
        offset_x: Horizontal offset of the viewport in screen pixels.
        offset_y: Vertical offset of the viewport in screen pixels.
        viewport_width: Rendered content width in screen pixels.
        viewport_height: Rendered content height in screen pixels.
        letterbox_top: Unused band height at the top edge.
        letterbox_bottom: Unused band height at the bottom edge.
        letterbox_left: Unused band width at the left edge.
        letterbox_right: Unused band width at the right edge.
        scale_mode: The scale mode that produced this result.
    """

    mode_id: str = ""
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    viewport_width: float = 0.0
    viewport_height: float = 0.0
    letterbox_top: float = 0.0
    letterbox_bottom: float = 0.0
    letterbox_left: float = 0.0
    letterbox_right: float = 0.0
    scale_mode: ScaleMode = ScaleMode.SHOW_ALL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode_id": self.mode_id,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "letterbox_top": self.letterbox_top,
            "letterbox_bottom": self.letterbox_bottom,
            "letterbox_left": self.letterbox_left,
            "letterbox_right": self.letterbox_right,
            "scale_mode": self.scale_mode.value,
        }


@dataclass
class ScreenStats:
    """Aggregate counters describing the screen manager state.

    Attributes:
        total_modes: Number of registered screen modes.
        total_viewports: Number of registered viewports.
        total_layouts: Number of registered layout adaptations.
        total_profiles: Number of registered profiles.
        primary_mode: The primary mode, or None when none is set.
        current_orientation: The engine's current orientation.
        current_aspect_ratio: Aspect ratio of the primary mode, or "unknown".
    """

    total_modes: int = 0
    total_viewports: int = 0
    total_layouts: int = 0
    total_profiles: int = 0
    primary_mode: Optional[ScreenMode] = None
    current_orientation: Orientation = Orientation.LANDSCAPE
    current_aspect_ratio: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_modes": self.total_modes,
            "total_viewports": self.total_viewports,
            "total_layouts": self.total_layouts,
            "total_profiles": self.total_profiles,
            "primary_mode": self.primary_mode.to_dict() if self.primary_mode else None,
            "current_orientation": self.current_orientation.value,
            "current_aspect_ratio": self.current_aspect_ratio,
        }


@dataclass
class ScreenSnapshot:
    """An immutable snapshot of the entire screen manager state.

    Attributes:
        initialized: Whether the engine has completed initialization.
        modes: List of all registered screen modes.
        viewports: List of all registered viewports.
        layouts: List of all registered layout adaptations.
        profiles: List of all registered profiles.
        events: List of all audit events.
        stats: Aggregate statistics.
    """

    initialized: bool = False
    modes: List[ScreenMode] = field(default_factory=list)
    viewports: List[Viewport] = field(default_factory=list)
    layouts: List[LayoutAdaptation] = field(default_factory=list)
    profiles: List[ScreenProfile] = field(default_factory=list)
    events: List["ScreenEvent"] = field(default_factory=list)
    stats: ScreenStats = field(default_factory=ScreenStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "modes": [m.to_dict() for m in self.modes],
            "viewports": [v.to_dict() for v in self.viewports],
            "layouts": [l.to_dict() for l in self.layouts],
            "profiles": [p.to_dict() for p in self.profiles],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class ScreenEvent:
    """An audit event emitted by the screen manager.

    Attributes:
        event_id: Unique identifier for the event.
        kind: The ScreenEventKind classification.
        timestamp: When the event occurred.
        payload: Event-specific payload data.
    """

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: ScreenEventKind = ScreenEventKind.MODE_CHANGED
    timestamp: float = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


# ---------------------------------------------------------------------------
# Screen Manager Engine (Singleton)
# ---------------------------------------------------------------------------


class ScreenManagerEngine:
    """Screen Manager and Scale System orchestration engine.

    Maintains the registry of screen modes, viewports, layout
    adaptations and profiles, computes scale/letterbox results for the
    classical scale modes, tracks the current orientation, and emits
    audit events for lifecycle changes.

    The class implements the singleton pattern with double-checked
    locking using ``threading.RLock`` for thread-safe access. All
    public methods are guarded by the re-entrant lock. Consumers should
    obtain the instance through :meth:`get_instance` or the module-level
    :func:`get_screen_manager` factory.
    """

    _instance: Optional["ScreenManagerEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "ScreenManagerEngine":
        # Double-checked locking: acquire the lock only when the
        # instance has not yet been created. The freshly allocated
        # instance is marked as not-yet-initialized so that __init__
        # performs the real one-time setup.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ScreenManagerEngine":
        """Return the singleton ScreenManagerEngine instance (thread-safe).

        Does not reset the ``_initialized`` flag; only constructs the
        instance if it has not been created yet.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # One-time initialization guard. The outer check avoids taking
        # the lock on the hot path once initialization is complete; the
        # inner check prevents a race between two threads that both
        # observed _initialized as False.
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Primary registries.
            # Modes keyed by mode id.
            self._modes: Dict[str, ScreenMode] = {}
            # Viewports keyed by viewport id.
            self._viewports: Dict[str, Viewport] = {}
            # Layout adaptations keyed by layout id.
            self._layouts: Dict[str, LayoutAdaptation] = {}
            # Profiles keyed by profile id.
            self._profiles: Dict[str, ScreenProfile] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: List[ScreenEvent] = []

            # Currently active primary mode id and global orientation.
            self._primary_mode_id: str = ""
            self._current_orientation: Orientation = Orientation.LANDSCAPE

            # Counters maintained for fast stats retrieval.
            self._mode_counter: int = 0
            self._viewport_counter: int = 0
            self._layout_counter: int = 0
            self._profile_counter: int = 0
            self._event_counter: int = 0

            self._initialized: bool = True

            # Populate the default seed screen data.
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with default screen modes, viewports, layouts and profiles.

        The seed data represents a typical multi-platform game target
        matrix: a desktop primary mode at 1080p, a 1440p and a 4K
        landscape mode, a portrait mobile mode, and a low-end 720p
        landscape mode; two viewports sharing the primary mode (the main
        game view and a minimap); a desktop and a mobile layout
        adaptation; and two reusable profiles (desktop standard and
        mobile responsive).
        """
        # 1. Primary desktop mode - 1920x1080 @ 60Hz, 96 DPI.
        primary = self.register_mode(
            width=1920,
            height=1080,
            refresh_rate=60.0,
            dpi=96.0,
            is_primary=True,
            metadata={"seed": True, "label": "Desktop Primary"},
        )

        # 2. QHD desktop mode - 2560x1440 @ 60Hz, 109 DPI.
        self.register_mode(
            width=2560,
            height=1440,
            refresh_rate=60.0,
            dpi=109.0,
            metadata={"seed": True, "label": "Desktop QHD"},
        )

        # 3. UHD 4K mode - 3840x2160 @ 60Hz, 163 DPI.
        self.register_mode(
            width=3840,
            height=2160,
            refresh_rate=60.0,
            dpi=163.0,
            metadata={"seed": True, "label": "Desktop 4K"},
        )

        # 4. Mobile portrait mode - 1080x1920 @ 60Hz, 96 DPI.
        mobile_mode = self.register_mode(
            width=1080,
            height=1920,
            refresh_rate=60.0,
            dpi=96.0,
            metadata={"seed": True, "label": "Mobile Portrait"},
        )

        # 5. Low-end desktop mode - 1280x720 @ 60Hz, 96 DPI.
        self.register_mode(
            width=1280,
            height=720,
            refresh_rate=60.0,
            dpi=96.0,
            metadata={"seed": True, "label": "Desktop 720p"},
        )

        # Viewport 1: the main game view filling the whole primary mode.
        self.create_viewport(
            name="Main Game View",
            x=0.0,
            y=0.0,
            width=1920.0,
            height=1080.0,
            scale_x=1.0,
            scale_y=1.0,
            rotation=0.0,
            mode_id=primary.mode_id,
        )

        # Viewport 2: a minimap in the top-right corner of the primary mode.
        self.create_viewport(
            name="Minimap View",
            x=1620.0,
            y=20.0,
            width=280.0,
            height=280.0,
            scale_x=0.15,
            scale_y=0.15,
            rotation=0.0,
            mode_id=primary.mode_id,
        )

        # Layout 1: desktop HUD layout for the primary landscape mode.
        self.create_layout(
            name="Desktop Layout",
            mode_id=primary.mode_id,
            orientation=Orientation.LANDSCAPE,
            anchor_points={
                "health_bar": {"anchor": "top_left", "offset_x": 20.0, "offset_y": 20.0},
                "minimap": {"anchor": "top_right", "offset_x": -20.0, "offset_y": 20.0},
                "ability_bar": {"anchor": "bottom_center", "offset_x": 0.0, "offset_y": -20.0},
                "quest_tracker": {"anchor": "right", "offset_x": -20.0, "offset_y": 320.0},
            },
            element_scales={
                "health_bar": 1.0,
                "minimap": 1.0,
                "ability_bar": 1.0,
                "quest_tracker": 1.0,
            },
            visible_elements=["health_bar", "minimap", "ability_bar", "quest_tracker"],
            hidden_elements=["touch_controls"],
            repositioned_elements={
                "inventory_button": {"anchor": "bottom_right", "offset_x": -20.0, "offset_y": -20.0},
            },
        )

        # Layout 2: mobile HUD layout for the portrait mobile mode.
        self.create_layout(
            name="Mobile Layout",
            mode_id=mobile_mode.mode_id,
            orientation=Orientation.PORTRAIT,
            anchor_points={
                "health_bar": {"anchor": "top_center", "offset_x": 0.0, "offset_y": 10.0},
                "minimap": {"anchor": "top_right", "offset_x": -10.0, "offset_y": 10.0},
                "ability_bar": {"anchor": "bottom_center", "offset_x": 0.0, "offset_y": -10.0},
            },
            element_scales={
                "health_bar": 0.7,
                "minimap": 0.5,
                "ability_bar": 0.8,
                "touch_controls": 1.0,
            },
            visible_elements=["health_bar", "minimap", "ability_bar", "touch_controls"],
            hidden_elements=["quest_tracker"],
            repositioned_elements={
                "inventory_button": {"anchor": "bottom_right", "offset_x": -10.0, "offset_y": -120.0},
                "quest_tracker": {"anchor": "hidden"},
            },
        )

        # Profile 1: desktop standard profile targeting the primary mode.
        self.create_profile(
            name="Desktop Standard",
            description=(
                "Standard desktop profile: 1080p primary mode with "
                "SHOW_ALL scaling, black-bar letterboxing and DPI-aware "
                "element sizing. Suitable for most desktop play."
            ),
            default_mode_id=primary.mode_id,
            scale_mode=ScaleMode.SHOW_ALL,
            letterbox_policy=LetterboxPolicy.BLACK_BARS,
            dpi_awareness=DPIAwareness.AWARE,
            min_width=1280,
            min_height=720,
            max_width=7680,
            max_height=4320,
        )

        # Profile 2: mobile responsive profile targeting the portrait mode.
        self.create_profile(
            name="Mobile Responsive",
            description=(
                "Responsive mobile profile: portrait primary mode with "
                "RESIZE scaling, no letterboxing and DPI-perceptible "
                "element sizing so high-DPI phones show more content."
            ),
            default_mode_id=mobile_mode.mode_id,
            scale_mode=ScaleMode.RESIZE,
            letterbox_policy=LetterboxPolicy.NONE,
            dpi_awareness=DPIAwareness.PERCEPTIBLE,
            min_width=320,
            min_height=240,
            max_width=2560,
            max_height=4320,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_resolution_tier(self, width: int, height: int) -> ResolutionTier:
        """Classify a (width, height) pair into a resolution tier.

        Classification is based on the short edge so that portrait modes
        (for example 1080x1920) are still classified by their 1080 line
        count rather than the rotated 1920.

        Args:
            width: Horizontal resolution in pixels.
            height: Vertical resolution in pixels.

        Returns:
            The matching ResolutionTier, or CUSTOM if neither dimension
            is positive.
        """
        short_edge = min(int(width), int(height))
        if short_edge <= 0:
            return ResolutionTier.CUSTOM
        if short_edge >= 4320:
            return ResolutionTier.UHD_8K
        if short_edge >= 2160:
            return ResolutionTier.UHD_4K
        if short_edge >= 1440:
            return ResolutionTier.QHD
        if short_edge >= 1080:
            return ResolutionTier.FULL_HD
        if short_edge >= 720:
            return ResolutionTier.HD
        return ResolutionTier.SD

    def _compute_aspect_ratio(self, width: int, height: int) -> str:
        """Reduce a (width, height) pair to a simplified aspect-ratio string.

        Uses the greatest common divisor to produce a string such as
        "16:9". A degenerate zero-area pair collapses to "0:0".

        Args:
            width: Horizontal resolution in pixels.
            height: Vertical resolution in pixels.

        Returns:
            The simplified aspect-ratio string.
        """
        divisor = _gcd(width, height)
        if divisor == 0:
            return "0:0"
        return f"{int(width) // divisor}:{int(height) // divisor}"

    def _record_event(
        self,
        kind: ScreenEventKind,
        payload: Dict[str, Any],
    ) -> ScreenEvent:
        """Record an audit event (caller must hold ``self._lock``).

        Args:
            kind: The ScreenEventKind classification.
            payload: Event-specific payload data.

        Returns:
            The created ScreenEvent.
        """
        event = ScreenEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        if len(self._events) >= _MAX_EVENTS:
            # FIFO eviction: drop the oldest event.
            self._events.pop(0)
        self._events.append(event)
        self._event_counter += 1
        return event

    # ------------------------------------------------------------------
    # Screen mode management
    # ------------------------------------------------------------------

    def register_mode(
        self,
        width: int,
        height: int,
        refresh_rate: float = 60.0,
        dpi: float = 96.0,
        is_primary: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScreenMode:
        """Register a new screen mode.

        Derives the resolution tier (from the short edge), the
        orientation (from the relative dimensions), the aspect ratio
        (via GCD) and the DPI scale (dpi / 96.0). When ``is_primary`` is
        true the new mode becomes the engine's primary mode, demoting
        any previously primary mode.

        Args:
            width: Horizontal resolution in pixels.
            height: Vertical resolution in pixels.
            refresh_rate: Nominal refresh rate in hertz.
            dpi: Physical dots-per-inch of the panel.
            is_primary: Whether this mode should become the primary mode.
            metadata: Optional free-form extension data.

        Returns:
            The newly created ScreenMode.
        """
        with self._lock:
            # Enforce the bounded store cap via FIFO eviction.
            if len(self._modes) >= _MAX_MODES:
                oldest_id = next(iter(self._modes), None)
                if oldest_id is not None:
                    self._modes.pop(oldest_id, None)

            # Derive orientation from the relative dimensions.
            if width > height:
                orientation = Orientation.LANDSCAPE
            elif width < height:
                orientation = Orientation.PORTRAIT
            else:
                # Square panels are treated as landscape by convention.
                orientation = Orientation.LANDSCAPE

            mode = ScreenMode(
                width=int(width),
                height=int(height),
                refresh_rate=float(refresh_rate),
                resolution_tier=self._compute_resolution_tier(width, height),
                orientation=orientation,
                dpi=float(dpi),
                dpi_scale=float(dpi) / 96.0,
                aspect_ratio=self._compute_aspect_ratio(width, height),
                is_primary=bool(is_primary),
                metadata=dict(metadata) if metadata else {},
            )
            self._modes[mode.mode_id] = mode
            self._mode_counter += 1

            if is_primary:
                # Demote any previously primary mode before promoting.
                for existing in self._modes.values():
                    if existing.is_primary and existing.mode_id != mode.mode_id:
                        existing.is_primary = False
                self._primary_mode_id = mode.mode_id

            self._record_event(
                ScreenEventKind.MODE_CHANGED,
                payload={
                    "mode_id": mode.mode_id,
                    "width": mode.width,
                    "height": mode.height,
                    "resolution_tier": mode.resolution_tier.value,
                    "orientation": mode.orientation.value,
                    "aspect_ratio": mode.aspect_ratio,
                    "is_primary": mode.is_primary,
                },
            )
            return mode

    def list_modes(
        self,
        resolution_tier: Optional[ResolutionTier] = None,
        orientation: Optional[Orientation] = None,
    ) -> List[ScreenMode]:
        """List registered screen modes, optionally filtered.

        Args:
            resolution_tier: Optional tier to filter by.
            orientation: Optional orientation to filter by.

        Returns:
            A list of ScreenMode objects matching the filters.
        """
        with self._lock:
            modes = list(self._modes.values())
        result: List[ScreenMode] = []
        for mode in modes:
            if resolution_tier is not None and mode.resolution_tier != resolution_tier:
                continue
            if orientation is not None and mode.orientation != orientation:
                continue
            result.append(mode)
        return result

    def get_mode(self, mode_id: str) -> Optional[ScreenMode]:
        """Return the screen mode with the given identifier.

        Args:
            mode_id: The unique identifier of the mode.

        Returns:
            The matching ScreenMode, or None if not found.
        """
        with self._lock:
            return self._modes.get(mode_id)

    def get_primary_mode(self) -> Optional[ScreenMode]:
        """Return the current primary screen mode.

        Returns:
            The primary ScreenMode, or None if no primary is set.
        """
        with self._lock:
            if not self._primary_mode_id:
                return None
            return self._modes.get(self._primary_mode_id)

    def set_primary_mode(self, mode_id: str) -> Optional[ScreenMode]:
        """Promote an existing mode to be the primary mode.

        Demotes any previously primary mode. Records a MODE_CHANGED
        event.

        Args:
            mode_id: The unique identifier of the mode to promote.

        Returns:
            The promoted ScreenMode, or None if the id was not found.
        """
        with self._lock:
            mode = self._modes.get(mode_id)
            if mode is None:
                return None
            # Demote any previously primary mode.
            for existing in self._modes.values():
                if existing.is_primary and existing.mode_id != mode_id:
                    existing.is_primary = False
            mode.is_primary = True
            self._primary_mode_id = mode_id
            self._record_event(
                ScreenEventKind.MODE_CHANGED,
                payload={
                    "mode_id": mode_id,
                    "is_primary": True,
                    "width": mode.width,
                    "height": mode.height,
                },
            )
            return mode

    # ------------------------------------------------------------------
    # Viewport management
    # ------------------------------------------------------------------

    def create_viewport(
        self,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        rotation: float = 0.0,
        mode_id: Optional[str] = None,
    ) -> Viewport:
        """Create a new viewport sub-rectangle.

        Args:
            name: Human-readable name of the viewport.
            x: Left edge of the viewport in screen pixels.
            y: Top edge of the viewport in screen pixels.
            width: Viewport width in screen pixels.
            height: Viewport height in screen pixels.
            scale_x: Horizontal render scale.
            scale_y: Vertical render scale.
            rotation: Viewport rotation in degrees.
            mode_id: Identifier of the screen mode this viewport belongs
                to. When None the current primary mode is used.

        Returns:
            The newly created Viewport.
        """
        with self._lock:
            # Resolve the owning mode id, falling back to the primary.
            resolved_mode_id = mode_id if mode_id is not None else self._primary_mode_id

            # Enforce the bounded store cap via FIFO eviction.
            if len(self._viewports) >= _MAX_VIEWPORTS:
                oldest_id = next(iter(self._viewports), None)
                if oldest_id is not None:
                    self._viewports.pop(oldest_id, None)

            viewport = Viewport(
                name=name,
                x=float(x),
                y=float(y),
                width=float(width),
                height=float(height),
                scale_x=float(scale_x),
                scale_y=float(scale_y),
                rotation=float(rotation),
                mode_id=resolved_mode_id if resolved_mode_id else "",
            )
            self._viewports[viewport.viewport_id] = viewport
            self._viewport_counter += 1

            self._record_event(
                ScreenEventKind.VIEWPORT_UPDATED,
                payload={
                    "viewport_id": viewport.viewport_id,
                    "name": viewport.name,
                    "mode_id": viewport.mode_id,
                    "width": viewport.width,
                    "height": viewport.height,
                },
            )
            return viewport

    def list_viewports(self, mode_id: Optional[str] = None) -> List[Viewport]:
        """List registered viewports, optionally filtered by owning mode.

        Args:
            mode_id: Optional mode id to filter by.

        Returns:
            A list of Viewport objects matching the filter.
        """
        with self._lock:
            viewports = list(self._viewports.values())
        if mode_id is None:
            return viewports
        return [v for v in viewports if v.mode_id == mode_id]

    def get_viewport(self, viewport_id: str) -> Optional[Viewport]:
        """Return the viewport with the given identifier.

        Args:
            viewport_id: The unique identifier of the viewport.

        Returns:
            The matching Viewport, or None if not found.
        """
        with self._lock:
            return self._viewports.get(viewport_id)

    def update_viewport(self, viewport_id: str, **kwargs: Any) -> Optional[Viewport]:
        """Update any viewport fields by keyword arguments.

        Accepts name, x, y, width, height, scale_x, scale_y, rotation
        and mode_id. The updated_at timestamp is refreshed and a
        VIEWPORT_UPDATED event is recorded.

        Args:
            viewport_id: The unique identifier of the viewport.
            **kwargs: Field names mapped to their new values.

        Returns:
            The updated Viewport, or None if not found.
        """
        with self._lock:
            viewport = self._viewports.get(viewport_id)
            if viewport is None:
                return None

            # Whitelisted mutable fields that may be updated via kwargs.
            allowed_fields = {
                "name",
                "x",
                "y",
                "width",
                "height",
                "scale_x",
                "scale_y",
                "rotation",
                "mode_id",
            }
            changed = False
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                setattr(viewport, key, value)
                changed = True

            if changed:
                viewport.updated_at = _now()
                self._record_event(
                    ScreenEventKind.VIEWPORT_UPDATED,
                    payload={
                        "viewport_id": viewport_id,
                        "updated_fields": [k for k in kwargs if k in allowed_fields],
                    },
                )
            return viewport

    def remove_viewport(self, viewport_id: str) -> bool:
        """Remove a viewport from the registry.

        Args:
            viewport_id: The unique identifier of the viewport.

        Returns:
            True if the viewport was removed, False if it was not found.
        """
        with self._lock:
            if viewport_id not in self._viewports:
                return False
            self._viewports.pop(viewport_id, None)
            self._record_event(
                ScreenEventKind.VIEWPORT_UPDATED,
                payload={"viewport_id": viewport_id, "removed": True},
            )
            return True

    # ------------------------------------------------------------------
    # Scale computation
    # ------------------------------------------------------------------

    def compute_scale(
        self,
        target_width: float,
        target_height: float,
        mode_id: Optional[str] = None,
        scale_mode: ScaleMode = ScaleMode.SHOW_ALL,
        letterbox_policy: LetterboxPolicy = LetterboxPolicy.BLACK_BARS,
    ) -> ScaleResult:
        """Compute the scale factors and letterbox offsets for a fit.

        Fits a target (design) resolution into the given screen mode
        using the specified scale mode. When ``mode_id`` is None the
        primary mode is used; if no primary mode is set the target
        dimensions are treated as a 1:1 container (scale 1.0, no
        letterbox).

        Scale modes:
          - EXACT_FIT: scale x and y independently to fill the screen;
            distortion is acceptable, no letterbox.
          - NO_BORDER: scale uniformly by the larger factor to cover the
            screen; overflow is cropped, no letterbox.
          - SHOW_ALL: scale uniformly by the smaller factor to show all
            content; the remaining bands are letterboxed.
          - RESIZE: scale 1.0; the viewport equals the screen size, no
            letterbox (the layout adapts to the available pixels).
          - FIT_WIDTH: scale uniformly to match the screen width; excess
            vertical space is letterboxed top/bottom.
          - FIT_HEIGHT: scale uniformly to match the screen height;
            excess horizontal space is letterboxed left/right.

        The ``letterbox_policy`` is recorded on the result so that the
        renderer knows how to fill the unused bands; it does not change
        the computed geometry.

        Args:
            target_width: Design resolution width in pixels.
            target_height: Design resolution height in pixels.
            mode_id: Identifier of the screen mode to fit into. When
                None the primary mode is used.
            scale_mode: The scale strategy to apply.
            letterbox_policy: How unused bands should be rendered.

        Returns:
            A ScaleResult describing the scale, offsets, viewport
            dimensions and letterbox bands.
        """
        with self._lock:
            # Resolve the container mode, falling back to the primary.
            if mode_id is not None:
                mode = self._modes.get(mode_id)
            else:
                mode = self._modes.get(self._primary_mode_id) if self._primary_mode_id else None

            if mode is None:
                # No container available: treat the target as a 1:1 fit.
                return ScaleResult(
                    mode_id="",
                    scale_x=1.0,
                    scale_y=1.0,
                    offset_x=0.0,
                    offset_y=0.0,
                    viewport_width=float(target_width),
                    viewport_height=float(target_height),
                    letterbox_top=0.0,
                    letterbox_bottom=0.0,
                    letterbox_left=0.0,
                    letterbox_right=0.0,
                    scale_mode=scale_mode,
                )

            mode_w = float(mode.width)
            mode_h = float(mode.height)
            tgt_w = float(target_width)
            tgt_h = float(target_height)

            # Guard against degenerate zero-area targets.
            if tgt_w <= 0.0 or tgt_h <= 0.0:
                return ScaleResult(
                    mode_id=mode.mode_id,
                    scale_x=1.0,
                    scale_y=1.0,
                    offset_x=0.0,
                    offset_y=0.0,
                    viewport_width=mode_w,
                    viewport_height=mode_h,
                    letterbox_top=0.0,
                    letterbox_bottom=0.0,
                    letterbox_left=0.0,
                    letterbox_right=0.0,
                    scale_mode=scale_mode,
                )

            if scale_mode == ScaleMode.EXACT_FIT:
                # Scale x and y independently to fill the screen; may
                # distort the content. No letterbox.
                scale_x = mode_w / tgt_w
                scale_y = mode_h / tgt_h
                result = ScaleResult(
                    mode_id=mode.mode_id,
                    scale_x=scale_x,
                    scale_y=scale_y,
                    offset_x=0.0,
                    offset_y=0.0,
                    viewport_width=mode_w,
                    viewport_height=mode_h,
                    letterbox_top=0.0,
                    letterbox_bottom=0.0,
                    letterbox_left=0.0,
                    letterbox_right=0.0,
                    scale_mode=scale_mode,
                )

            elif scale_mode == ScaleMode.NO_BORDER:
                # Scale uniformly by the larger factor so the screen is
                # fully covered; overflow is cropped, no letterbox.
                scale = max(mode_w / tgt_w, mode_h / tgt_h)
                vp_w = tgt_w * scale
                vp_h = tgt_h * scale
                offset_x = (mode_w - vp_w) / 2.0
                offset_y = (mode_h - vp_h) / 2.0
                result = ScaleResult(
                    mode_id=mode.mode_id,
                    scale_x=scale,
                    scale_y=scale,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    viewport_width=vp_w,
                    viewport_height=vp_h,
                    letterbox_top=0.0,
                    letterbox_bottom=0.0,
                    letterbox_left=0.0,
                    letterbox_right=0.0,
                    scale_mode=scale_mode,
                )

            elif scale_mode == ScaleMode.RESIZE:
                # No scaling; the viewport equals the screen size. The
                # layout is expected to adapt to the available pixels.
                result = ScaleResult(
                    mode_id=mode.mode_id,
                    scale_x=1.0,
                    scale_y=1.0,
                    offset_x=0.0,
                    offset_y=0.0,
                    viewport_width=mode_w,
                    viewport_height=mode_h,
                    letterbox_top=0.0,
                    letterbox_bottom=0.0,
                    letterbox_left=0.0,
                    letterbox_right=0.0,
                    scale_mode=scale_mode,
                )

            elif scale_mode == ScaleMode.FIT_WIDTH:
                # Scale uniformly to match the screen width; excess
                # vertical space is letterboxed top/bottom.
                scale = mode_w / tgt_w
                vp_w = mode_w
                vp_h = tgt_h * scale
                offset_x = 0.0
                offset_y = (mode_h - vp_h) / 2.0
                top = max(0.0, offset_y)
                bottom = max(0.0, mode_h - vp_h - offset_y)
                result = ScaleResult(
                    mode_id=mode.mode_id,
                    scale_x=scale,
                    scale_y=scale,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    viewport_width=vp_w,
                    viewport_height=vp_h,
                    letterbox_top=top,
                    letterbox_bottom=bottom,
                    letterbox_left=0.0,
                    letterbox_right=0.0,
                    scale_mode=scale_mode,
                )

            elif scale_mode == ScaleMode.FIT_HEIGHT:
                # Scale uniformly to match the screen height; excess
                # horizontal space is letterboxed left/right.
                scale = mode_h / tgt_h
                vp_w = tgt_w * scale
                vp_h = mode_h
                offset_x = (mode_w - vp_w) / 2.0
                offset_y = 0.0
                left = max(0.0, offset_x)
                right = max(0.0, mode_w - vp_w - offset_x)
                result = ScaleResult(
                    mode_id=mode.mode_id,
                    scale_x=scale,
                    scale_y=scale,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    viewport_width=vp_w,
                    viewport_height=vp_h,
                    letterbox_top=0.0,
                    letterbox_bottom=0.0,
                    letterbox_left=left,
                    letterbox_right=right,
                    scale_mode=scale_mode,
                )

            else:
                # Default: SHOW_ALL. Scale uniformly by the smaller
                # factor so all content is visible; the remaining bands
                # are letterboxed symmetrically.
                scale = min(mode_w / tgt_w, mode_h / tgt_h)
                vp_w = tgt_w * scale
                vp_h = tgt_h * scale
                offset_x = (mode_w - vp_w) / 2.0
                offset_y = (mode_h - vp_h) / 2.0
                left = max(0.0, offset_x)
                right = max(0.0, mode_w - vp_w - offset_x)
                top = max(0.0, offset_y)
                bottom = max(0.0, mode_h - vp_h - offset_y)
                result = ScaleResult(
                    mode_id=mode.mode_id,
                    scale_x=scale,
                    scale_y=scale,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    viewport_width=vp_w,
                    viewport_height=vp_h,
                    letterbox_top=top,
                    letterbox_bottom=bottom,
                    letterbox_left=left,
                    letterbox_right=right,
                    scale_mode=ScaleMode.SHOW_ALL,
                )

            # The letterbox policy is informational; NONE policies zero
            # the rendered bands conceptually but the geometry is kept
            # so that callers can switch policies without recomputing.
            # Record an event for observability.
            self._record_event(
                ScreenEventKind.SCALE_RECOMPUTED,
                payload={
                    "mode_id": result.mode_id,
                    "scale_mode": result.scale_mode.value,
                    "letterbox_policy": letterbox_policy.value,
                    "scale_x": result.scale_x,
                    "scale_y": result.scale_y,
                    "viewport_width": result.viewport_width,
                    "viewport_height": result.viewport_height,
                },
            )
            return result

    # ------------------------------------------------------------------
    # Layout adaptation management
    # ------------------------------------------------------------------

    def create_layout(
        self,
        name: str,
        mode_id: str,
        orientation: Orientation,
        anchor_points: Optional[Dict[str, Dict[str, Any]]] = None,
        element_scales: Optional[Dict[str, float]] = None,
        visible_elements: Optional[List[str]] = None,
        hidden_elements: Optional[List[str]] = None,
        repositioned_elements: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> LayoutAdaptation:
        """Create a new layout adaptation for a mode and orientation.

        Args:
            name: Human-readable name of the layout.
            mode_id: Identifier of the screen mode this layout targets.
            orientation: Orientation this layout is designed for.
            anchor_points: Mapping of element name to anchor metadata.
            element_scales: Mapping of element name to a scale multiplier.
            visible_elements: Element names that should be shown.
            hidden_elements: Element names that should be hidden.
            repositioned_elements: Mapping of element name to new position.

        Returns:
            The newly created LayoutAdaptation.
        """
        with self._lock:
            # Enforce the bounded store cap via FIFO eviction.
            if len(self._layouts) >= _MAX_LAYOUTS:
                oldest_id = next(iter(self._layouts), None)
                if oldest_id is not None:
                    self._layouts.pop(oldest_id, None)

            layout = LayoutAdaptation(
                name=name,
                mode_id=mode_id,
                orientation=orientation,
                anchor_points={k: dict(v) for k, v in (anchor_points or {}).items()},
                element_scales=dict(element_scales) if element_scales else {},
                visible_elements=list(visible_elements) if visible_elements else [],
                hidden_elements=list(hidden_elements) if hidden_elements else [],
                repositioned_elements={
                    k: dict(v) for k, v in (repositioned_elements or {}).items()
                },
            )
            self._layouts[layout.layout_id] = layout
            self._layout_counter += 1

            self._record_event(
                ScreenEventKind.LAYOUT_ADAPTED,
                payload={
                    "layout_id": layout.layout_id,
                    "name": layout.name,
                    "mode_id": layout.mode_id,
                    "orientation": layout.orientation.value,
                },
            )
            return layout

    def list_layouts(
        self,
        mode_id: Optional[str] = None,
        orientation: Optional[Orientation] = None,
    ) -> List[LayoutAdaptation]:
        """List registered layout adaptations, optionally filtered.

        Args:
            mode_id: Optional mode id to filter by.
            orientation: Optional orientation to filter by.

        Returns:
            A list of LayoutAdaptation objects matching the filters.
        """
        with self._lock:
            layouts = list(self._layouts.values())
        result: List[LayoutAdaptation] = []
        for layout in layouts:
            if mode_id is not None and layout.mode_id != mode_id:
                continue
            if orientation is not None and layout.orientation != orientation:
                continue
            result.append(layout)
        return result

    def get_layout(self, layout_id: str) -> Optional[LayoutAdaptation]:
        """Return the layout adaptation with the given identifier.

        Args:
            layout_id: The unique identifier of the layout.

        Returns:
            The matching LayoutAdaptation, or None if not found.
        """
        with self._lock:
            return self._layouts.get(layout_id)

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        description: str,
        default_mode_id: str,
        scale_mode: ScaleMode,
        letterbox_policy: LetterboxPolicy,
        dpi_awareness: DPIAwareness,
        min_width: int = 320,
        min_height: int = 240,
        max_width: int = 7680,
        max_height: int = 4320,
    ) -> ScreenProfile:
        """Create a new screen profile.

        Args:
            name: Human-readable name of the profile.
            description: Long-form description of the profile.
            default_mode_id: Identifier of the mode to promote on apply.
            scale_mode: The default scale mode for the profile.
            letterbox_policy: The default letterbox policy for the profile.
            dpi_awareness: The DPI awareness policy for the profile.
            min_width: Minimum supported horizontal resolution.
            min_height: Minimum supported vertical resolution.
            max_width: Maximum supported horizontal resolution.
            max_height: Maximum supported vertical resolution.

        Returns:
            The newly created ScreenProfile.
        """
        with self._lock:
            # Enforce the bounded store cap via FIFO eviction.
            if len(self._profiles) >= _MAX_PROFILES:
                oldest_id = next(iter(self._profiles), None)
                if oldest_id is not None:
                    self._profiles.pop(oldest_id, None)

            profile = ScreenProfile(
                name=name,
                description=description,
                default_mode_id=default_mode_id,
                scale_mode=scale_mode,
                letterbox_policy=letterbox_policy,
                dpi_awareness=dpi_awareness,
                min_width=int(min_width),
                min_height=int(min_height),
                max_width=int(max_width),
                max_height=int(max_height),
            )
            self._profiles[profile.profile_id] = profile
            self._profile_counter += 1

            self._record_event(
                ScreenEventKind.PROFILE_APPLIED,
                payload={
                    "profile_id": profile.profile_id,
                    "name": profile.name,
                    "default_mode_id": profile.default_mode_id,
                    "scale_mode": profile.scale_mode.value,
                    "created": True,
                },
            )
            return profile

    def list_profiles(self) -> List[ScreenProfile]:
        """List all registered screen profiles.

        Returns:
            A list of ScreenProfile objects.
        """
        with self._lock:
            return list(self._profiles.values())

    def get_profile(self, profile_id: str) -> Optional[ScreenProfile]:
        """Return the screen profile with the given identifier.

        Args:
            profile_id: The unique identifier of the profile.

        Returns:
            The matching ScreenProfile, or None if not found.
        """
        with self._lock:
            return self._profiles.get(profile_id)

    def apply_profile(self, profile_id: str) -> Optional[ScreenProfile]:
        """Apply a screen profile by promoting its default mode to primary.

        Args:
            profile_id: The unique identifier of the profile to apply.

        Returns:
            The applied ScreenProfile, or None if not found.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None

            # Promote the profile's default mode to primary when present.
            if profile.default_mode_id:
                mode = self._modes.get(profile.default_mode_id)
                if mode is not None:
                    for existing in self._modes.values():
                        if existing.is_primary and existing.mode_id != profile.default_mode_id:
                            existing.is_primary = False
                    mode.is_primary = True
                    self._primary_mode_id = profile.default_mode_id

            profile.updated_at = _now()
            self._record_event(
                ScreenEventKind.PROFILE_APPLIED,
                payload={
                    "profile_id": profile_id,
                    "name": profile.name,
                    "default_mode_id": profile.default_mode_id,
                    "scale_mode": profile.scale_mode.value,
                    "letterbox_policy": profile.letterbox_policy.value,
                    "dpi_awareness": profile.dpi_awareness.value,
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Orientation and aspect ratio
    # ------------------------------------------------------------------

    def get_orientation(self) -> Orientation:
        """Return the engine's current orientation.

        Returns:
            The current Orientation.
        """
        with self._lock:
            return self._current_orientation

    def set_orientation(self, orientation: Orientation) -> Orientation:
        """Set the engine's current orientation.

        Records an ORIENTATION_CHANGED event.

        Args:
            orientation: The new orientation to apply.

        Returns:
            The newly applied Orientation.
        """
        with self._lock:
            previous = self._current_orientation
            self._current_orientation = orientation
            self._record_event(
                ScreenEventKind.ORIENTATION_CHANGED,
                payload={
                    "previous": previous.value,
                    "current": orientation.value,
                },
            )
            return self._current_orientation

    def get_aspect_ratio(self, mode_id: Optional[str] = None) -> str:
        """Return the aspect ratio string for a screen mode.

        When ``mode_id`` is None the primary mode is used. Returns
        "unknown" when the mode cannot be resolved.

        Args:
            mode_id: Optional identifier of the mode to inspect.

        Returns:
            The simplified aspect-ratio string, or "unknown".
        """
        with self._lock:
            if mode_id is not None:
                mode = self._modes.get(mode_id)
            else:
                mode = self._modes.get(self._primary_mode_id) if self._primary_mode_id else None
            if mode is None:
                return "unknown"
            return mode.aspect_ratio

    # ------------------------------------------------------------------
    # Events, stats, status and snapshot
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[ScreenEvent]:
        """Return audit events limited to the most recent ``limit`` entries.

        Args:
            limit: Maximum number of events to return.

        Returns:
            A list of ScreenEvent objects ordered from oldest to newest.
        """
        with self._lock:
            events = list(self._events)
        if limit > 0:
            events = events[-limit:]
        return events

    def get_stats(self) -> ScreenStats:
        """Compute aggregate statistics from the current engine state.

        Returns:
            A ScreenStats describing the current store counts, primary
            mode, orientation and aspect ratio.
        """
        with self._lock:
            primary_mode = None
            if self._primary_mode_id:
                primary_mode = self._modes.get(self._primary_mode_id)
            current_aspect = "unknown"
            if primary_mode is not None:
                current_aspect = primary_mode.aspect_ratio
            return ScreenStats(
                total_modes=len(self._modes),
                total_viewports=len(self._viewports),
                total_layouts=len(self._layouts),
                total_profiles=len(self._profiles),
                primary_mode=primary_mode,
                current_orientation=self._current_orientation,
                current_aspect_ratio=current_aspect,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current screen manager state.

        The ``initialized`` flag is always the first key in the returned
        dictionary, followed by store counts and aggregate statistics.

        Returns:
            A dictionary with the system status.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_modes": len(self._modes),
                "total_viewports": len(self._viewports),
                "total_layouts": len(self._layouts),
                "total_profiles": len(self._profiles),
                "total_events": len(self._events),
                "mode_counter": self._mode_counter,
                "viewport_counter": self._viewport_counter,
                "layout_counter": self._layout_counter,
                "profile_counter": self._profile_counter,
                "event_counter": self._event_counter,
                "primary_mode_id": self._primary_mode_id,
                "current_orientation": self._current_orientation.value,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> ScreenSnapshot:
        """Capture an immutable snapshot of the screen manager state.

        Returns:
            A ScreenSnapshot capturing the system state at this moment.
        """
        with self._lock:
            stats = self.get_stats()
            return ScreenSnapshot(
                initialized=self._initialized,
                modes=list(self._modes.values()),
                viewports=list(self._viewports.values()),
                layouts=list(self._layouts.values()),
                profiles=list(self._profiles.values()),
                events=list(self._events),
                stats=stats,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data.

        Restores the engine to its initial state, including the seed
        modes, viewports, layouts and profiles.
        """
        with self._lock:
            self._modes.clear()
            self._viewports.clear()
            self._layouts.clear()
            self._profiles.clear()
            self._events.clear()
            self._primary_mode_id = ""
            self._current_orientation = Orientation.LANDSCAPE
            self._mode_counter = 0
            self._viewport_counter = 0
            self._layout_counter = 0
            self._profile_counter = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_screen_manager() -> ScreenManagerEngine:
    """Return the singleton ScreenManagerEngine instance."""
    return ScreenManagerEngine.get_instance()
