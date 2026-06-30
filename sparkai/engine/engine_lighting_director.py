"""
SparkLabs Engine - Lighting Director

Engine-side cinematic lighting director that orchestrates dynamic lighting
for game scenes. It manages light sources (directional, point, spot, area,
ambient, hemisphere), light groups, lighting moods/presets, time-of-day
mood transitions, and shadow casting configuration. Similar to how a film's
gaffer and director of photography collaborate on lighting design, this
system coordinates all light sources to achieve a desired visual atmosphere.

The lighting director maintains a registry of light sources, light groups
(which reference sets of lights), lighting moods (named presets that pin a
state onto each referenced light), and mood transitions that blend from
one mood to another over a duration with an easing curve. Light sources
progress through the ``LightState`` lifecycle (OFF / ON / FADING_IN /
FADING_OUT / FLICKERING). When a mood is activated the director applies
each referenced light's mood-pinned state, optional color overrides, and
optional intensity multipliers. Mood transitions record a start and
completion timestamp and drive a progress value from 0.0 to 1.0.

This subsystem focuses on director-level lighting orchestration. Low-level
GPU light culling, shadow map rendering, and shader integration are
delegated to the engine's lighting system; this module decides which light
sources exist, what state they are in, how they are grouped, and which
mood is currently driving the scene's atmosphere.

Architecture:
  LightingDirectorEngine (Singleton)
    |-- LightSource       (a single light source with position/color/state)
    |-- LightGroup        (a named group of light source ids)
    |-- LightingMood       (a named preset of per-light state/overrides)
    |-- MoodTransition     (a timed blend between two moods)
    |-- LightingStats      (aggregate statistic counters)
    |-- LightingSnapshot   (immutable snapshot of director state)
    |-- LightEvent         (an emitted director lifecycle event)

Lifecycle:
  1. create_light(name, light_type, ...)             -> LightSource
  2. create_group(name, light_ids, ...)               -> LightGroup
  3. create_mood(name, mood_type, light_states, ...)   -> LightingMood
  4. create_mood_transition(from_mood_id, to_mood_id) -> MoodTransition
  5. set_light_state(light_id, state) / set_light_intensity(...) / set_light_color(...)
  6. activate_mood(mood_id)                           -> LightingMood
  7. execute_mood_transition(transition_id)           -> MoodTransition
  8. compute_lighting(position, radius)               -> Dict
  9. get_active_lights() / get_snapshot() / get_status() / reset()
"""

from __future__ import annotations

import datetime
import math
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Capacity Constants
# =============================================================================

# Maximum number of registered entities of each kind before creation is
# refused. These bounds keep the director's memory footprint predictable
# even when driven by an agent generating large volumes of lighting data.
_MAX_LIGHTS: int = 2000
_MAX_GROUPS: int = 200
_MAX_MOODS: int = 500
_MAX_TRANSITIONS: int = 500
_MAX_EVENTS: int = 2000

# Maximum number of concurrently registered event handlers across all
# event kinds. Keeps dispatch cost bounded.
_MAX_EVENT_HANDLERS: int = 64


# =============================================================================
# Enumerations
# =============================================================================


class LightType(Enum):
    """The kind of light source a ``LightSource`` represents.

    ``DIRECTIONAL`` is an infinitely far light (e.g. the sun) with no
    position falloff. ``POINT`` radiates in all directions from a position.
    ``SPOT`` is a cone-shaped light from a position with a beam angle.
    ``AREA`` approximates a planar light emitter. ``AMBIENT`` contributes a
    flat base level of light everywhere. ``HEMISPHERE`` blends two colors
    across the sky/ground hemisphere.
    """

    DIRECTIONAL = "directional"
    POINT = "point"
    SPOT = "spot"
    AREA = "area"
    AMBIENT = "ambient"
    HEMISPHERE = "hemisphere"


class LightState(Enum):
    """Lifecycle states for a light source.

    ``OFF`` is fully unlit, ``ON`` is fully lit, ``FADING_IN`` is ramping
    up from off toward on, ``FADING_OUT`` is ramping down toward off, and
    ``FLICKERING`` oscillates around its intensity (e.g. a torch flame).
    """

    OFF = "off"
    ON = "on"
    FADING_IN = "fading_in"
    FADING_OUT = "fading_out"
    FLICKERING = "flickering"


class ShadowMode(Enum):
    """The shadow casting configuration for a light source.

    ``NONE`` casts no shadows, ``HARD`` casts sharp-edged shadows, ``SOFT``
    casts penumbra-blurred shadows, and ``VOLUMETRIC`` casts shadows that
    also scatter light through participating media (fog, smoke, dust).
    """

    NONE = "none"
    HARD = "hard"
    SOFT = "soft"
    VOLUMETRIC = "volumetric"


class MoodType(Enum):
    """Named atmospheric moods that a ``LightingMood`` can represent.

    The ``DAWN`` / ``NOON`` / ``DUSK`` / ``NIGHT`` values map to natural
    time-of-day lighting, while ``STORMY`` / ``MYSTERIOUS`` / ``DRAMATIC``
    / ``SERENE`` / ``TENSE`` describe emotional tone moods. ``CUSTOM`` is
    used for authored moods that do not fit a named category.
    """

    DAWN = "dawn"
    NOON = "noon"
    DUSK = "dusk"
    NIGHT = "night"
    STORMY = "stormy"
    MYSTERIOUS = "mysterious"
    DRAMATIC = "dramatic"
    SERENE = "serene"
    TENSE = "tense"
    CUSTOM = "custom"


class LightEventKind(Enum):
    """Kinds of events emitted by the lighting director."""

    LIGHT_CREATED = "light_created"
    LIGHT_REMOVED = "light_removed"
    LIGHT_STATE_CHANGED = "light_state_changed"
    MOOD_ACTIVATED = "mood_activated"
    MOOD_TRANSITION_STARTED = "mood_transition_started"
    MOOD_TRANSITION_COMPLETED = "mood_transition_completed"
    GROUP_CREATED = "group_created"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class LightSource:
    """A single light source within the scene.

    A light source carries its spatial placement (position and direction),
    its emitted color (linear RGB in the 0.0-1.0 range), its intensity, an
    attenuation range (for point/spot/area lights), a spot cone angle (for
    spot lights), the shadow casting mode, an enabled flag, a rendering
    priority (lower values are rendered first), and free-form metadata.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the light.
        light_type: The ``LightType`` of this source.
        state: Current ``LightState`` lifecycle state.
        position: World position ``(x, y, z)``.
        direction: World direction ``(x, y, z)`` (normalized for
            directional/spot/area lights).
        color: Emitted color ``(r, g, b)`` in the range 0.0 to 1.0.
        intensity: Emitted brightness (lumens, engine-defined scale).
        range: Attenuation range for point/spot/area lights.
        spot_angle: Cone half-angle in degrees for spot lights.
        shadow_mode: The ``ShadowMode`` for shadow casting.
        enabled: Whether the light contributes to the scene.
        priority: Rendering priority (lower renders first).
        metadata: Free-form extension data.
        timestamp: Time at which the light was created.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    light_type: LightType = LightType.POINT
    state: LightState = LightState.OFF
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: Tuple[float, float, float] = (0.0, -1.0, 0.0)
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    range: float = 0.0
    spot_angle: float = 0.0
    shadow_mode: ShadowMode = ShadowMode.NONE
    enabled: bool = True
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "light_type": self.light_type.value,
            "state": self.state.value,
            "position": list(self.position),
            "direction": list(self.direction),
            "color": list(self.color),
            "intensity": self.intensity,
            "range": self.range,
            "spot_angle": self.spot_angle,
            "shadow_mode": self.shadow_mode.value,
            "enabled": self.enabled,
            "priority": self.priority,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class LightGroup:
    """A named group of light source ids.

    Groups allow sets of lights to be toggled or queried together (e.g.
    "all torches in the east wing"). A group carries an enabled flag that
    callers may use to bulk-toggle member lights, and free-form metadata.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the group.
        light_ids: Ordered list of member light source ids.
        enabled: Whether the group is currently enabled.
        metadata: Free-form extension data.
        timestamp: Time at which the group was created.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    light_ids: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "light_ids": list(self.light_ids),
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class LightingMood:
    """A named preset that pins a desired state onto each referenced light.

    A mood maps each light id to a target ``LightState``, optionally
    overrides the emitted color per light, and optionally scales each
    light's intensity via a multiplier. Activating a mood applies these
    mappings to every referenced light in one coordinated pass - similar
    to a cinematographer calling for a lighting setup.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name of the mood.
        mood_type: The ``MoodType`` category of this mood.
        light_states: Mapping of light id -> target ``LightState``.
        color_overrides: Mapping of light id -> ``(r, g, b)`` override.
        intensity_multipliers: Mapping of light id -> multiplier float.
        description: Human-readable description of the mood.
        metadata: Free-form extension data.
        timestamp: Time at which the mood was created.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    mood_type: MoodType = MoodType.CUSTOM
    light_states: Dict[str, LightState] = field(default_factory=dict)
    color_overrides: Dict[str, Tuple[float, float, float]] = field(
        default_factory=dict
    )
    intensity_multipliers: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mood_type": self.mood_type.value,
            "light_states": {
                lid: s.value for lid, s in self.light_states.items()
            },
            "color_overrides": {
                lid: list(c) for lid, c in self.color_overrides.items()
            },
            "intensity_multipliers": dict(self.intensity_multipliers),
            "description": self.description,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class MoodTransition:
    """A timed blend from one lighting mood to another.

    A transition records the source and destination mood ids, the blend
    duration in seconds, the easing curve name, and the start and
    completion timestamps once executed. The ``progress`` field holds the
    most recent computed blend progress in the range 0.0 to 1.0.

    Attributes:
        id: Unique identifier (auto-generated).
        from_mood_id: Identifier of the source mood.
        to_mood_id: Identifier of the destination mood.
        duration: Blend length in seconds.
        easing: Name of the easing curve (e.g. ``linear``, ``ease_in_out``).
        started_at: Timestamp when execution began.
        completed_at: Timestamp when execution finished.
        progress: Most recent computed blend progress (0.0 to 1.0).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_mood_id: str = ""
    to_mood_id: str = ""
    duration: float = 0.0
    easing: str = "linear"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_mood_id": self.from_mood_id,
            "to_mood_id": self.to_mood_id,
            "duration": self.duration,
            "easing": self.easing,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
        }


@dataclass
class LightingStats:
    """Aggregate statistic counters for the lighting director.

    Attributes:
        total_lights: Lifetime count of lights created.
        total_groups: Lifetime count of groups created.
        total_moods: Lifetime count of moods created.
        active_lights: Number of lights currently in an active state.
        active_mood: Identifier of the currently active mood, if any.
        last_updated: Timestamp of the most recent counter update.
    """

    total_lights: int = 0
    total_groups: int = 0
    total_moods: int = 0
    active_lights: int = 0
    active_mood: Optional[str] = None
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_lights": self.total_lights,
            "total_groups": self.total_groups,
            "total_moods": self.total_moods,
            "active_lights": self.active_lights,
            "active_mood": self.active_mood,
            "last_updated": self.last_updated,
        }


@dataclass
class LightingSnapshot:
    """An immutable snapshot of the lighting director state.

    Attributes:
        total_lights: Total number of registered light sources.
        active_lights: Number of lights currently in an active state.
        group_count: Total number of registered light groups.
        mood_count: Total number of registered lighting moods.
        stats: Aggregated statistic counters.
        timestamp: Time at which the snapshot was taken.
    """

    total_lights: int = 0
    active_lights: int = 0
    group_count: int = 0
    mood_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_lights": self.total_lights,
            "active_lights": self.active_lights,
            "group_count": self.group_count,
            "mood_count": self.mood_count,
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


@dataclass
class LightEvent:
    """An immutable record of a lighting director lifecycle event.

    Attributes:
        id: Unique identifier (auto-generated).
        kind: The ``LightEventKind`` of the event.
        payload: Free-form payload describing the event.
        timestamp: Time at which the event was emitted.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: LightEventKind = LightEventKind.LIGHT_CREATED
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


# =============================================================================
# Lighting Director Engine (Singleton)
# =============================================================================


class LightingDirectorEngine:
    """Engine-side cinematic lighting director.

    Maintains a registry of light sources, light groups, lighting moods,
    and mood transitions. Coordinates light activation through the
    ``LightState`` lifecycle, applies mood presets to referenced lights,
    executes timed mood transitions, computes aggregate lighting
    contributions at a point in space, and emits lifecycle events to
    subscribed handlers.

    All public methods are thread-safe. The class implements the singleton
    pattern with double-checked locking; consumers should obtain the
    instance through :meth:`get_instance` or :func:`get_lighting_director`.
    """

    _instance: Optional["LightingDirectorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "LightingDirectorEngine":
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
    def get_instance(cls) -> "LightingDirectorEngine":
        """Return the singleton LightingDirectorEngine instance (thread-safe).

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
        self._lights: Dict[str, LightSource] = {}
        self._groups: Dict[str, LightGroup] = {}
        self._moods: Dict[str, LightingMood] = {}
        self._transitions: Dict[str, MoodTransition] = {}

        # Currently active mood id (the last successfully activated mood).
        self._active_mood_id: Optional[str] = None

        # Event log and subscriber registry. Handlers are stored both in
        # a kind-keyed dispatch map and in a handler-id registry so that
        # individual handlers can be unregistered by id.
        self._events: List[LightEvent] = []
        self._event_handlers: Dict[str, List[Callable[[LightEvent], None]]] = {}
        self._handler_registry: Dict[
            str, Tuple[str, Callable[[LightEvent], None]]
        ] = {}
        self._total_events_emitted: int = 0

        # Aggregate statistic counters (lifetime totals).
        self._total_lights: int = 0
        self._total_groups: int = 0
        self._total_moods: int = 0
        self._total_transitions: int = 0

        # Populate the default seed lighting data.
        self._seed_default_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_kind(kind: Any) -> str:
        """Normalize an event kind argument to its string value.

        ``None`` maps to the wildcard ``"*"`` so a handler subscribed with
        ``None`` receives every event kind.
        """
        if kind is None:
            return "*"
        if isinstance(kind, LightEventKind):
            return kind.value
        return str(kind)

    def _dispatch_event(self, event: LightEvent) -> None:
        """Deliver an event to all matching registered handlers.

        Handlers subscribed to the event's kind and handlers subscribed
        to the wildcard ``"*"`` are both invoked. A failing handler is
        silently skipped so a single bad handler cannot break dispatch.
        """
        kind_value = event.kind.value
        for key in (kind_value, "*"):
            handlers = self._event_handlers.get(key)
            if not handlers:
                continue
            for handler in list(handlers):
                try:
                    handler(event)
                except Exception:
                    # A failing handler must not break event dispatch.
                    pass

    def _emit_event(
        self,
        kind: LightEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> LightEvent:
        """Create, log, and dispatch a lighting event (internal use only).

        The event log is capped at ``_MAX_EVENTS`` entries; the oldest
        entries are evicted when the cap is exceeded.
        """
        event = LightEvent(
            kind=kind,
            payload=payload or {},
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            del self._events[: len(self._events) - _MAX_EVENTS]
        self._total_events_emitted += 1
        self._dispatch_event(event)
        return event

    def _count_active_lights(self) -> int:
        """Return the number of enabled lights currently in an active state.

        A light is considered active when it is enabled and not in the
        ``OFF`` state - i.e. it is contributing light to the scene (on,
        fading, or flickering).
        """
        return sum(
            1
            for light in self._lights.values()
            if light.enabled and light.state != LightState.OFF
        )

    def _compute_stats(self) -> Dict[str, Any]:
        """Compute the aggregate statistic counters from current state."""
        return {
            "total_lights": self._total_lights,
            "total_groups": self._total_groups,
            "total_moods": self._total_moods,
            "active_lights": self._count_active_lights(),
            "active_mood": self._active_mood_id,
            "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        }

    @staticmethod
    def _ease(easing: str, t: float) -> float:
        """Apply a named easing curve to a normalized progress value.

        Supported curves are ``linear``, ``ease_in``, ``ease_out``,
        ``ease_in_out`` and ``smoothstep``. Unknown curves fall back to a
        linear progression.
        """
        t = max(0.0, min(1.0, t))
        name = easing or "linear"
        if name == "linear":
            return t
        if name == "ease_in":
            return t * t
        if name == "ease_out":
            return 1.0 - (1.0 - t) * (1.0 - t)
        if name == "ease_in_out":
            return t * t * (3.0 - 2.0 * t)
        if name == "smoothstep":
            return t * t * (3.0 - 2.0 * t)
        # Unknown easing falls back to linear.
        return t

    # ------------------------------------------------------------------
    # Light management
    # ------------------------------------------------------------------

    def create_light(
        self,
        name: str,
        light_type: LightType,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        direction: Tuple[float, float, float] = (0.0, -1.0, 0.0),
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
        range: float = 0.0,
        spot_angle: float = 0.0,
        shadow_mode: ShadowMode = ShadowMode.NONE,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LightSource:
        """Create and register a new light source.

        Args:
            name: Human-readable name of the light.
            light_type: The ``LightType`` of this source.
            position: World position ``(x, y, z)``.
            direction: World direction ``(x, y, z)``.
            color: Emitted color ``(r, g, b)`` in the range 0.0 to 1.0.
            intensity: Emitted brightness (engine-defined scale).
            range: Attenuation range for point/spot/area lights.
            spot_angle: Cone half-angle in degrees for spot lights.
            shadow_mode: The ``ShadowMode`` for shadow casting.
            priority: Rendering priority (lower renders first).
            metadata: Free-form extension data.

        Returns:
            The newly created LightSource.

        Raises:
            ValueError: If the light capacity (``_MAX_LIGHTS``) has been
                reached or the intensity is negative.
        """
        with self._lock:
            if len(self._lights) >= _MAX_LIGHTS:
                raise ValueError(
                    f"Light capacity reached ({_MAX_LIGHTS})"
                )
            if intensity < 0:
                raise ValueError(
                    f"Light intensity must be non-negative: {intensity}"
                )
            light = LightSource(
                name=name,
                light_type=light_type,
                state=LightState.ON,
                position=tuple(position),
                direction=tuple(direction),
                color=tuple(color),
                intensity=intensity,
                range=range,
                spot_angle=spot_angle,
                shadow_mode=shadow_mode,
                enabled=True,
                priority=priority,
                metadata=dict(metadata) if metadata else {},
            )
            self._lights[light.id] = light
            self._total_lights += 1
            self._emit_event(
                LightEventKind.LIGHT_CREATED,
                payload={
                    "light_id": light.id,
                    "name": light.name,
                    "light_type": light.light_type.value,
                    "state": light.state.value,
                },
            )
            return light

    def get_light(self, light_id: str) -> Optional[LightSource]:
        """Retrieve a light source by its identifier."""
        with self._lock:
            return self._lights.get(light_id)

    def list_lights(
        self,
        light_type: Optional[LightType] = None,
        state: Optional[LightState] = None,
    ) -> List[LightSource]:
        """List light sources, optionally filtered by type and/or state.

        The returned list is sorted by name then id.

        Args:
            light_type: When provided, restrict the result to lights of
                this type.
            state: When provided, restrict the result to lights in this
                state.
        """
        with self._lock:
            lights = list(self._lights.values())
            if light_type is not None:
                lights = [l for l in lights if l.light_type == light_type]
            if state is not None:
                lights = [l for l in lights if l.state == state]
            lights.sort(key=lambda l: (l.name, l.id))
            return lights

    def remove_light(self, light_id: str) -> bool:
        """Remove a light source from the director.

        The light is also detached from any group's member list and any
        mood's per-light state/override/multiplier maps.

        Returns:
            True if the light was removed, False if it was not found.
        """
        with self._lock:
            if light_id not in self._lights:
                return False
            del self._lights[light_id]
            for group in self._groups.values():
                if light_id in group.light_ids:
                    group.light_ids[:] = [
                        lid for lid in group.light_ids if lid != light_id
                    ]
            for mood in self._moods.values():
                mood.light_states.pop(light_id, None)
                mood.color_overrides.pop(light_id, None)
                mood.intensity_multipliers.pop(light_id, None)
            self._emit_event(
                LightEventKind.LIGHT_REMOVED,
                payload={"light_id": light_id},
            )
            return True

    def set_light_state(
        self,
        light_id: str,
        state: LightState,
    ) -> Optional[LightSource]:
        """Set the lifecycle state of a light source.

        Args:
            light_id: Identifier of the light to update.
            state: The target ``LightState``.

        Returns:
            The updated LightSource, or None if the light was not found.
        """
        with self._lock:
            light = self._lights.get(light_id)
            if light is None:
                return None
            light.state = state
            self._emit_event(
                LightEventKind.LIGHT_STATE_CHANGED,
                payload={
                    "light_id": light.id,
                    "name": light.name,
                    "state": light.state.value,
                },
            )
            return light

    def set_light_intensity(
        self,
        light_id: str,
        intensity: float,
    ) -> Optional[LightSource]:
        """Set the intensity of a light source.

        Args:
            light_id: Identifier of the light to update.
            intensity: The target intensity (clamped to be non-negative).

        Returns:
            The updated LightSource, or None if the light was not found.
        """
        with self._lock:
            light = self._lights.get(light_id)
            if light is None:
                return None
            light.intensity = max(0.0, intensity)
            self._emit_event(
                LightEventKind.LIGHT_STATE_CHANGED,
                payload={
                    "light_id": light.id,
                    "name": light.name,
                    "intensity": light.intensity,
                },
            )
            return light

    def set_light_color(
        self,
        light_id: str,
        color: Tuple[float, float, float],
    ) -> Optional[LightSource]:
        """Set the emitted color of a light source.

        Args:
            light_id: Identifier of the light to update.
            color: The target color ``(r, g, b)`` in the range 0.0 to 1.0.

        Returns:
            The updated LightSource, or None if the light was not found.
        """
        with self._lock:
            light = self._lights.get(light_id)
            if light is None:
                return None
            light.color = tuple(color)
            self._emit_event(
                LightEventKind.LIGHT_STATE_CHANGED,
                payload={
                    "light_id": light.id,
                    "name": light.name,
                    "color": list(light.color),
                },
            )
            return light

    # ------------------------------------------------------------------
    # Group management
    # ------------------------------------------------------------------

    def create_group(
        self,
        name: str,
        light_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LightGroup:
        """Create and register a new light group.

        Args:
            name: Human-readable name of the group.
            light_ids: Ordered list of member light source ids.
            metadata: Free-form extension data.

        Returns:
            The newly created LightGroup.

        Raises:
            ValueError: If the group capacity (``_MAX_GROUPS``) has been
                reached.
        """
        with self._lock:
            if len(self._groups) >= _MAX_GROUPS:
                raise ValueError(
                    f"Group capacity reached ({_MAX_GROUPS})"
                )
            group = LightGroup(
                name=name,
                light_ids=list(light_ids) if light_ids else [],
                enabled=True,
                metadata=dict(metadata) if metadata else {},
            )
            self._groups[group.id] = group
            self._total_groups += 1
            self._emit_event(
                LightEventKind.GROUP_CREATED,
                payload={
                    "group_id": group.id,
                    "name": group.name,
                    "light_ids": list(group.light_ids),
                },
            )
            return group

    def get_group(self, group_id: str) -> Optional[LightGroup]:
        """Retrieve a light group by its identifier."""
        with self._lock:
            return self._groups.get(group_id)

    def list_groups(self) -> List[LightGroup]:
        """Return all registered light groups sorted by name then id."""
        with self._lock:
            groups = list(self._groups.values())
            groups.sort(key=lambda g: (g.name, g.id))
            return groups

    def remove_group(self, group_id: str) -> bool:
        """Remove a light group from the director.

        Member lights are left in place; only the group binding is removed.

        Returns:
            True if the group was removed, False if it was not found.
        """
        with self._lock:
            if group_id not in self._groups:
                return False
            del self._groups[group_id]
            return True

    def set_group_enabled(
        self,
        group_id: str,
        enabled: bool,
    ) -> Optional[LightGroup]:
        """Toggle the enabled flag of a light group.

        Args:
            group_id: Identifier of the group to update.
            enabled: The target enabled state.

        Returns:
            The updated LightGroup, or None if the group was not found.
        """
        with self._lock:
            group = self._groups.get(group_id)
            if group is None:
                return None
            group.enabled = enabled
            return group

    # ------------------------------------------------------------------
    # Mood management
    # ------------------------------------------------------------------

    def create_mood(
        self,
        name: str,
        mood_type: MoodType,
        light_states: Optional[Dict[str, LightState]] = None,
        color_overrides: Optional[
            Dict[str, Tuple[float, float, float]]
        ] = None,
        intensity_multipliers: Optional[Dict[str, float]] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LightingMood:
        """Create and register a new lighting mood preset.

        Args:
            name: Human-readable name of the mood.
            mood_type: The ``MoodType`` category of this mood.
            light_states: Mapping of light id -> target ``LightState``.
            color_overrides: Mapping of light id -> ``(r, g, b)`` override.
            intensity_multipliers: Mapping of light id -> multiplier float.
            description: Human-readable description of the mood.
            metadata: Free-form extension data.

        Returns:
            The newly created LightingMood.

        Raises:
            ValueError: If the mood capacity (``_MAX_MOODS``) has been
                reached.
        """
        with self._lock:
            if len(self._moods) >= _MAX_MOODS:
                raise ValueError(
                    f"Mood capacity reached ({_MAX_MOODS})"
                )
            mood = LightingMood(
                name=name,
                mood_type=mood_type,
                light_states=dict(light_states) if light_states else {},
                color_overrides=dict(color_overrides) if color_overrides else {},
                intensity_multipliers=dict(intensity_multipliers)
                if intensity_multipliers
                else {},
                description=description,
                metadata=dict(metadata) if metadata else {},
            )
            self._moods[mood.id] = mood
            self._total_moods += 1
            return mood

    def get_mood(self, mood_id: str) -> Optional[LightingMood]:
        """Retrieve a lighting mood by its identifier."""
        with self._lock:
            return self._moods.get(mood_id)

    def list_moods(
        self,
        mood_type: Optional[MoodType] = None,
    ) -> List[LightingMood]:
        """List lighting moods, optionally filtered by mood type.

        The returned list is sorted by name then id.

        Args:
            mood_type: When provided, restrict the result to moods of
                this type.
        """
        with self._lock:
            moods = list(self._moods.values())
            if mood_type is not None:
                moods = [m for m in moods if m.mood_type == mood_type]
            moods.sort(key=lambda m: (m.name, m.id))
            return moods

    def remove_mood(self, mood_id: str) -> bool:
        """Remove a lighting mood from the director.

        If the removed mood is currently active, the active mood reference
        is cleared. Mood transitions referencing the removed mood are left
        in place; callers should clean them up explicitly.

        Returns:
            True if the mood was removed, False if it was not found.
        """
        with self._lock:
            if mood_id not in self._moods:
                return False
            del self._moods[mood_id]
            if self._active_mood_id == mood_id:
                self._active_mood_id = None
            return True

    def activate_mood(self, mood_id: str) -> Optional[LightingMood]:
        """Apply a mood preset to all of its referenced lights.

        For each light referenced in the mood's ``light_states`` map the
        light's state is set to the mood-pinned state. Color overrides
        replace the light's color and intensity multipliers scale the
        light's intensity. Lights referenced in the mood but not present
        in the registry are silently skipped.

        Args:
            mood_id: Identifier of the mood to activate.

        Returns:
            The activated LightingMood, or None if it was not found.
        """
        with self._lock:
            mood = self._moods.get(mood_id)
            if mood is None:
                return None
            for light_id, target_state in mood.light_states.items():
                light = self._lights.get(light_id)
                if light is None:
                    continue
                light.state = target_state
                self._emit_event(
                    LightEventKind.LIGHT_STATE_CHANGED,
                    payload={
                        "light_id": light.id,
                        "name": light.name,
                        "state": light.state.value,
                        "mood_id": mood.id,
                    },
                )
            for light_id, override in mood.color_overrides.items():
                light = self._lights.get(light_id)
                if light is None:
                    continue
                light.color = tuple(override)
            for light_id, multiplier in mood.intensity_multipliers.items():
                light = self._lights.get(light_id)
                if light is None:
                    continue
                light.intensity = max(0.0, light.intensity * multiplier)
            self._active_mood_id = mood.id
            self._emit_event(
                LightEventKind.MOOD_ACTIVATED,
                payload={
                    "mood_id": mood.id,
                    "name": mood.name,
                    "mood_type": mood.mood_type.value,
                },
            )
            return mood

    # ------------------------------------------------------------------
    # Mood transition management
    # ------------------------------------------------------------------

    def create_mood_transition(
        self,
        from_mood_id: str,
        to_mood_id: str,
        duration: float = 0.0,
        easing: str = "linear",
    ) -> MoodTransition:
        """Create a timed transition between two existing moods.

        Args:
            from_mood_id: Identifier of the source mood.
            to_mood_id: Identifier of the destination mood.
            duration: Blend length in seconds.
            easing: Name of the easing curve to apply.

        Returns:
            The newly created MoodTransition.

        Raises:
            ValueError: If the transition capacity (``_MAX_TRANSITIONS``)
                has been reached, either mood does not exist, the two
                moods are the same, or the duration is negative.
        """
        with self._lock:
            if len(self._transitions) >= _MAX_TRANSITIONS:
                raise ValueError(
                    f"Mood transition capacity reached ({_MAX_TRANSITIONS})"
                )
            if from_mood_id not in self._moods:
                raise ValueError(f"Source mood not found: {from_mood_id}")
            if to_mood_id not in self._moods:
                raise ValueError(f"Destination mood not found: {to_mood_id}")
            if from_mood_id == to_mood_id:
                raise ValueError(
                    "Cannot transition a mood to itself: "
                    f"{from_mood_id}"
                )
            if duration < 0:
                raise ValueError(
                    f"Transition duration must be non-negative: {duration}"
                )
            transition = MoodTransition(
                from_mood_id=from_mood_id,
                to_mood_id=to_mood_id,
                duration=duration,
                easing=easing or "linear",
            )
            self._transitions[transition.id] = transition
            self._total_transitions += 1
            return transition

    def execute_mood_transition(
        self,
        transition_id: str,
    ) -> Optional[MoodTransition]:
        """Execute a previously created mood transition.

        Activates the source mood (so the starting state is well-defined),
        emits a transition-started event, then activates the destination
        mood, applies the easing curve to compute the final progress, and
        records the start and completion timestamps. The transition's
        progress is set to 1.0 on completion.

        Args:
            transition_id: Identifier of the transition to execute.

        Returns:
            The executed MoodTransition, or None if it was not found or
            references a missing mood.
        """
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return None
            from_mood = self._moods.get(transition.from_mood_id)
            to_mood = self._moods.get(transition.to_mood_id)
            if from_mood is None or to_mood is None:
                return None

            transition.started_at = (
                datetime.datetime.utcnow().isoformat() + "Z"
            )
            transition.progress = 0.0
            self._emit_event(
                LightEventKind.MOOD_TRANSITION_STARTED,
                payload={
                    "transition_id": transition.id,
                    "from_mood_id": transition.from_mood_id,
                    "to_mood_id": transition.to_mood_id,
                    "duration": transition.duration,
                    "easing": transition.easing,
                },
            )

            # Establish the source lighting state, then blend to the target.
            self.activate_mood(transition.from_mood_id)

            # Evaluate the easing curve to a final progress value. For an
            # instantaneous transition (duration == 0) progress jumps to 1.0;
            # otherwise we sample the eased endpoint to represent the
            # completed blend. A real engine would tick progress over time.
            if transition.duration <= 0:
                transition.progress = 1.0
            else:
                transition.progress = self._ease(transition.easing, 1.0)

            self.activate_mood(transition.to_mood_id)

            transition.completed_at = (
                datetime.datetime.utcnow().isoformat() + "Z"
            )
            self._emit_event(
                LightEventKind.MOOD_TRANSITION_COMPLETED,
                payload={
                    "transition_id": transition.id,
                    "from_mood_id": transition.from_mood_id,
                    "to_mood_id": transition.to_mood_id,
                    "progress": transition.progress,
                },
            )
            return transition

    def get_mood_transition(
        self,
        transition_id: str,
    ) -> Optional[MoodTransition]:
        """Retrieve a mood transition by its identifier."""
        with self._lock:
            return self._transitions.get(transition_id)

    def list_mood_transitions(self) -> List[MoodTransition]:
        """Return all registered mood transitions sorted by id."""
        with self._lock:
            transitions = list(self._transitions.values())
            transitions.sort(key=lambda t: t.id)
            return transitions

    # ------------------------------------------------------------------
    # Lighting computation
    # ------------------------------------------------------------------

    def compute_lighting(
        self,
        position: Tuple[float, float, float],
        radius: float = 0.0,
    ) -> Dict[str, Any]:
        """Aggregate the lighting contributions at a point in space.

        Iterates every enabled, active (non-OFF) light and computes its
        contribution to the query point. Directional and ambient lights
        contribute regardless of distance. Point, spot, and area lights
        contribute an inverse-square-falloff amount when within their
        range (and, for spot lights, within their cone). Spot lights
        additionally factor the cone angle attenuation.

        Args:
            position: World position ``(x, y, z)`` to sample.
            radius: Optional query radius; lights beyond ``position`` +
                ``radius`` are skipped. A value of 0.0 disables the
                spatial pre-filter for non-directional lights.

        Returns:
            A dict describing the aggregate lighting, including the
            accumulated ``color`` ``(r, g, b)``, the ``total_intensity``,
            the number of ``contributing_lights``, and a per-light
            ``contributions`` list.
        """
        with self._lock:
            px, py, pz = position
            color_r = 0.0
            color_g = 0.0
            color_b = 0.0
            total_intensity = 0.0
            contributions: List[Dict[str, Any]] = []
            for light in self._lights.values():
                if not light.enabled or light.state == LightState.OFF:
                    continue
                ltype = light.light_type
                cr, cg, cb = light.color
                intensity = light.intensity

                if ltype in (LightType.AMBIENT, LightType.HEMISPHERE):
                    # Ambient and hemisphere lights contribute evenly.
                    contribution = intensity
                elif ltype == LightType.DIRECTIONAL:
                    # Directional lights contribute fully regardless of
                    # distance; direction is not attenuated by position.
                    contribution = intensity
                else:
                    # Point / spot / area lights fall off with distance.
                    lx, ly, lz = light.position
                    dx = px - lx
                    dy = py - ly
                    dz = pz - lz
                    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                    # Spatial pre-filter when a query radius is given.
                    if radius > 0.0 and dist > radius and dist > 0.0:
                        continue
                    # Range attenuation.
                    if light.range > 0.0 and dist > light.range:
                        continue
                    if dist < 1e-6:
                        falloff = 1.0
                    else:
                        falloff = 1.0 / (1.0 + dist * dist)
                    # Clamp falloff to the light's range so far lights
                    # do not contribute past their declared range.
                    if light.range > 0.0:
                        falloff = min(
                            falloff,
                            max(0.0, 1.0 - dist / light.range),
                        )
                    contribution = intensity * falloff

                    # Spot cone attenuation.
                    if ltype == LightType.SPOT and light.spot_angle > 0.0:
                        # Direction the spot is pointing (assumed normalized
                        # by the caller; we normalize defensively).
                        dirx, diry, dirz = light.direction
                        dlen = math.sqrt(
                            dirx * dirx + diry * diry + dirz * dirz
                        )
                        if dlen < 1e-6:
                            spot_cos = 0.0
                        else:
                            # Cosine of the angle between the spot
                            # direction and the vector to the point.
                            if dist < 1e-6:
                                spot_cos = 1.0
                            else:
                                spot_cos = max(
                                    0.0,
                                    (
                                        dirx * dx + diry * dy + dirz * dz
                                    )
                                    / (dlen * dist),
                                )
                        # Half-angle in radians; treat spot_angle as the
                        # cone half-angle in degrees.
                        half_angle = math.radians(light.spot_angle)
                        cone_cos = math.cos(half_angle)
                        if spot_cos < cone_cos:
                            contribution = 0.0
                        else:
                            # Smooth cone attenuation toward the edge.
                            if cone_cos < 1.0:
                                contribution *= (spot_cos - cone_cos) / (
                                    1.0 - cone_cos
                                )
                if contribution <= 0.0:
                    continue
                color_r += cr * contribution
                color_g += cg * contribution
                color_b += cb * contribution
                total_intensity += contribution
                contributions.append(
                    {
                        "light_id": light.id,
                        "name": light.name,
                        "light_type": ltype.value,
                        "contribution": contribution,
                        "color": [cr, cg, cb],
                    }
                )
            return {
                "position": list(position),
                "radius": radius,
                "color": [color_r, color_g, color_b],
                "total_intensity": total_intensity,
                "contributing_lights": len(contributions),
                "contributions": contributions,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            }

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_active_lights(self) -> List[LightSource]:
        """Return all enabled lights currently in an active state.

        A light is considered active when it is enabled and not in the
        ``OFF`` state. The returned list is sorted by name then id.
        """
        with self._lock:
            lights = [
                light
                for light in self._lights.values()
                if light.enabled and light.state != LightState.OFF
            ]
            lights.sort(key=lambda l: (l.name, l.id))
            return lights

    def get_active_mood(self) -> Optional[LightingMood]:
        """Return the currently active lighting mood, if any."""
        with self._lock:
            if self._active_mood_id is None:
                return None
            return self._moods.get(self._active_mood_id)

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: Any,
        handler: Callable[[LightEvent], None],
    ) -> str:
        """Subscribe a handler to lighting director events.

        Args:
            kind: The ``LightEventKind`` (or its string value) to
                subscribe to. Pass ``None`` to subscribe to all events.
            handler: Callable invoked with each matching LightEvent.

        Returns:
            A handler identifier that can be passed to
            :meth:`unregister_event_handler` to remove the subscription.

        Raises:
            ValueError: If the handler capacity (``_MAX_EVENT_HANDLERS``)
                has been reached.
        """
        with self._lock:
            if len(self._handler_registry) >= _MAX_EVENT_HANDLERS:
                raise ValueError(
                    f"Event handler limit reached ({_MAX_EVENT_HANDLERS})"
                )
            key = self._normalize_kind(kind)
            self._event_handlers.setdefault(key, []).append(handler)
            handler_id = uuid.uuid4().hex
            self._handler_registry[handler_id] = (key, handler)
            return handler_id

    def unregister_event_handler(self, handler_id: str) -> bool:
        """Remove a previously registered event handler.

        Args:
            handler_id: The identifier returned by
                :meth:`register_event_handler`.

        Returns:
            True if the handler was removed, False if no handler is
            registered under that id.
        """
        with self._lock:
            entry = self._handler_registry.pop(handler_id, None)
            if entry is None:
                return False
            key, handler = entry
            handlers = self._event_handlers.get(key)
            if handlers is not None:
                try:
                    handlers.remove(handler)
                except ValueError:
                    pass
                if not handlers:
                    self._event_handlers.pop(key, None)
            return True

    def list_events(
        self,
        event_kind: Optional[Any] = None,
        limit: int = 100,
    ) -> List[LightEvent]:
        """Return the most recent events, newest last.

        Args:
            event_kind: When provided (as a ``LightEventKind`` or its
                string value), restrict the result to events of that kind.
            limit: Maximum number of events to return.

        Returns:
            A list of LightEvent records (up to ``limit``).
        """
        with self._lock:
            if limit <= 0:
                return []
            events = list(self._events)
            if event_kind is not None:
                target = self._normalize_kind(event_kind)
                events = [e for e in events if e.kind.value == target]
            return events[-limit:]

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_stats(self) -> LightingStats:
        """Return aggregate statistic counters as a LightingStats object."""
        with self._lock:
            return LightingStats(
                total_lights=self._total_lights,
                total_groups=self._total_groups,
                total_moods=self._total_moods,
                active_lights=self._count_active_lights(),
                active_mood=self._active_mood_id,
                last_updated=datetime.datetime.utcnow().isoformat() + "Z",
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current director state."""
        with self._lock:
            stats = self._compute_stats()
            return {
                "initialized": self._initialized,
                "total_lights": len(self._lights),
                "total_groups": len(self._groups),
                "total_moods": len(self._moods),
                "total_transitions": len(self._transitions),
                "active_lights": self._count_active_lights(),
                "active_mood": self._active_mood_id,
                "total_events": len(self._events),
                "total_handlers": len(self._handler_registry),
                "stats": stats,
            }

    def get_snapshot(self) -> LightingSnapshot:
        """Capture an immutable snapshot of the director state."""
        with self._lock:
            stats = self._compute_stats()
            return LightingSnapshot(
                total_lights=len(self._lights),
                active_lights=self._count_active_lights(),
                group_count=len(self._groups),
                mood_count=len(self._moods),
                stats=stats,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all lights, groups, moods, transitions, events, and handlers.

        Restores the director to its initial state, including the default
        seed lighting data.
        """
        with self._lock:
            self._lights.clear()
            self._groups.clear()
            self._moods.clear()
            self._transitions.clear()
            self._active_mood_id = None
            self._events.clear()
            self._event_handlers.clear()
            self._handler_registry.clear()
            self._total_events_emitted = 0
            self._total_lights = 0
            self._total_groups = 0
            self._total_moods = 0
            self._total_transitions = 0
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate the default lights, groups, moods, and mood transition.

        Creates a small cinematic setup: five lights (a directional sun,
        two point torches, an ambient fill, and a stage spotlight), two
        light groups (the torches and the ambient set), three lighting
        moods (daytime, nighttime, and a dramatic scene), and a single
        mood transition blending from daytime to nighttime over three
        seconds with an ease-in-out curve.
        """
        # 1. Lights - the foundational cinematic light rig.
        sun = LightSource(
            name="Sun",
            light_type=LightType.DIRECTIONAL,
            state=LightState.ON,
            position=(0.0, 100.0, 0.0),
            direction=(-0.5, -1.0, -0.5),
            color=(1.0, 0.95, 0.85),
            intensity=3.0,
            range=0.0,
            spot_angle=0.0,
            shadow_mode=ShadowMode.SOFT,
            enabled=True,
            priority=0,
            metadata={"role": "key_light", "category": "sun"},
        )
        self._lights[sun.id] = sun
        self._total_lights += 1
        self._emit_event(
            LightEventKind.LIGHT_CREATED,
            payload={
                "light_id": sun.id,
                "name": sun.name,
                "light_type": sun.light_type.value,
                "state": sun.state.value,
            },
        )

        torch_01 = LightSource(
            name="Torch_01",
            light_type=LightType.POINT,
            state=LightState.ON,
            position=(10.0, 3.0, 10.0),
            direction=(0.0, 1.0, 0.0),
            color=(1.0, 0.6, 0.2),
            intensity=2.0,
            range=15.0,
            spot_angle=0.0,
            shadow_mode=ShadowMode.SOFT,
            enabled=True,
            priority=1,
            metadata={"role": "practical", "category": "torch"},
        )
        self._lights[torch_01.id] = torch_01
        self._total_lights += 1
        self._emit_event(
            LightEventKind.LIGHT_CREATED,
            payload={
                "light_id": torch_01.id,
                "name": torch_01.name,
                "light_type": torch_01.light_type.value,
                "state": torch_01.state.value,
            },
        )

        torch_02 = LightSource(
            name="Torch_02",
            light_type=LightType.POINT,
            state=LightState.ON,
            position=(20.0, 3.0, 20.0),
            direction=(0.0, 1.0, 0.0),
            color=(1.0, 0.6, 0.2),
            intensity=2.0,
            range=15.0,
            spot_angle=0.0,
            shadow_mode=ShadowMode.SOFT,
            enabled=True,
            priority=1,
            metadata={"role": "practical", "category": "torch"},
        )
        self._lights[torch_02.id] = torch_02
        self._total_lights += 1
        self._emit_event(
            LightEventKind.LIGHT_CREATED,
            payload={
                "light_id": torch_02.id,
                "name": torch_02.name,
                "light_type": torch_02.light_type.value,
                "state": torch_02.state.value,
            },
        )

        ambient_fill = LightSource(
            name="Ambient_Fill",
            light_type=LightType.AMBIENT,
            state=LightState.ON,
            position=(0.0, 0.0, 0.0),
            direction=(0.0, 1.0, 0.0),
            color=(0.3, 0.3, 0.4),
            intensity=0.5,
            range=0.0,
            spot_angle=0.0,
            shadow_mode=ShadowMode.NONE,
            enabled=True,
            priority=2,
            metadata={"role": "fill_light", "category": "ambient"},
        )
        self._lights[ambient_fill.id] = ambient_fill
        self._total_lights += 1
        self._emit_event(
            LightEventKind.LIGHT_CREATED,
            payload={
                "light_id": ambient_fill.id,
                "name": ambient_fill.name,
                "light_type": ambient_fill.light_type.value,
                "state": ambient_fill.state.value,
            },
        )

        spotlight_stage = LightSource(
            name="Spotlight_Stage",
            light_type=LightType.SPOT,
            state=LightState.OFF,
            position=(15.0, 10.0, 15.0),
            direction=(0.0, -1.0, 0.0),
            color=(1.0, 1.0, 1.0),
            intensity=5.0,
            range=25.0,
            spot_angle=45.0,
            shadow_mode=ShadowMode.HARD,
            enabled=True,
            priority=0,
            metadata={"role": "stage_light", "category": "spotlight"},
        )
        self._lights[spotlight_stage.id] = spotlight_stage
        self._total_lights += 1
        self._emit_event(
            LightEventKind.LIGHT_CREATED,
            payload={
                "light_id": spotlight_stage.id,
                "name": spotlight_stage.name,
                "light_type": spotlight_stage.light_type.value,
                "state": spotlight_stage.state.value,
            },
        )

        # 2. Groups - the torches and the ambient set.
        torches_group = LightGroup(
            name="Torches",
            light_ids=[torch_01.id, torch_02.id],
            enabled=True,
            metadata={"description": "All practical torch lights"},
        )
        self._groups[torches_group.id] = torches_group
        self._total_groups += 1
        self._emit_event(
            LightEventKind.GROUP_CREATED,
            payload={
                "group_id": torches_group.id,
                "name": torches_group.name,
                "light_ids": list(torches_group.light_ids),
            },
        )

        ambient_group = LightGroup(
            name="Ambient",
            light_ids=[ambient_fill.id, sun.id],
            enabled=True,
            metadata={"description": "Sun and ambient fill lights"},
        )
        self._groups[ambient_group.id] = ambient_group
        self._total_groups += 1
        self._emit_event(
            LightEventKind.GROUP_CREATED,
            payload={
                "group_id": ambient_group.id,
                "name": ambient_group.name,
                "light_ids": list(ambient_group.light_ids),
            },
        )

        # 3. Moods - daytime, nighttime, and a dramatic scene.
        daytime_mood = LightingMood(
            name="Daytime",
            mood_type=MoodType.NOON,
            light_states={
                sun.id: LightState.ON,
                torch_01.id: LightState.OFF,
                torch_02.id: LightState.OFF,
                ambient_fill.id: LightState.ON,
            },
            color_overrides={},
            intensity_multipliers={},
            description="Bright midday sun with torches off and ambient fill.",
            metadata={"time_of_day": "noon"},
        )
        self._moods[daytime_mood.id] = daytime_mood
        self._total_moods += 1

        nighttime_mood = LightingMood(
            name="Nighttime",
            mood_type=MoodType.NIGHT,
            light_states={
                sun.id: LightState.OFF,
                torch_01.id: LightState.ON,
                torch_02.id: LightState.ON,
                ambient_fill.id: LightState.ON,
            },
            color_overrides={},
            intensity_multipliers={
                ambient_fill.id: 0.3,
            },
            description="Sun off, torches lit, ambient fill dimmed.",
            metadata={"time_of_day": "night"},
        )
        self._moods[nighttime_mood.id] = nighttime_mood
        self._total_moods += 1

        dramatic_mood = LightingMood(
            name="Dramatic Scene",
            mood_type=MoodType.DRAMATIC,
            light_states={
                sun.id: LightState.ON,
                torch_01.id: LightState.FLICKERING,
                spotlight_stage.id: LightState.ON,
            },
            color_overrides={},
            intensity_multipliers={
                sun.id: 0.4,
            },
            description="Dim sun, flickering torch, stage spotlight on.",
            metadata={"tone": "dramatic"},
        )
        self._moods[dramatic_mood.id] = dramatic_mood
        self._total_moods += 1

        # 4. Mood transition - daytime blends into nighttime over 3s.
        day_to_night = MoodTransition(
            from_mood_id=daytime_mood.id,
            to_mood_id=nighttime_mood.id,
            duration=3.0,
            easing="ease_in_out",
        )
        self._transitions[day_to_night.id] = day_to_night
        self._total_transitions += 1


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_lighting_director() -> LightingDirectorEngine:
    """Return the singleton LightingDirectorEngine instance."""
    return LightingDirectorEngine.get_instance()
