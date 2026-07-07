"""
SparkLabs Engine - Cutscene Player

Cinematic cutscene playback system for the SparkLabs game engine. The
player orchestrates timeline tracks, camera sequences, subtitle sync,
actor blocking, audio cues and effect triggers across one or more
cutscenes. Each cutscene is modeled as a collection of timeline tracks
that hold ordered clips; clips in turn hold camera keyframes, subtitle
entries, actor cues and audio cues that fire at specific offsets within
the clip.

Architecture:
  CutscenePlayer (singleton)
    |-- CutsceneAsset         (top-level cutscene definition)
    |-- TimelineTrack         (ordered layer inside a cutscene)
    |-- TimelineClip          (time-bounded segment on a track)
    |-- CameraKeyframe        (camera position / rotation / fov sample)
    |-- SubtitleEntry         (timed caption with speaker and styling)
    |-- ActorCue              (actor action with target transform)
    |-- AudioCue              (sound playback with mixing parameters)
    |-- PlaybackCheckpoint    (named seek target inside a cutscene)
    |-- CutscenePlayerStats   (aggregate counters)
    |-- CutscenePlayerSnapshot (immutable point-in-time capture)
    |-- CutscenePlayerEvent   (audit log entry)

Core Capabilities:
  - load_cutscene / unload_cutscene / update_cutscene: lifecycle for
    cutscene assets, with priority and loop-mode metadata.
  - add_track / update_track / remove_track: timeline layer management
    with sort ordering, lock and enable flags.
  - add_clip / update_clip / remove_clip: segment management with
    blend in/out, offsets and arbitrary properties.
  - add_camera_keyframe / list_camera_keyframes: cinematic camera path
    sampling with per-axis position, rotation, fov and interpolation.
  - add_subtitle / get_subtitle / list_subtitles: timed caption sync
    with speaker, language, font size, color and screen position.
  - add_actor_cue / list_actor_cues: actor blocking with action name,
    parameters and target transform plus blend time.
  - add_audio_cue / list_audio_cues: sound cues with volume, pitch,
    loop flag, fade ramps and spatial position.
  - play / pause / resume / stop / seek / get_playback_state: playback
    transport control with per-cutscene state tracking.
  - add_checkpoint / get_checkpoint / list_checkpoints: named seek
    targets that can be flagged as skippable.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability, serialization and lifecycle reset.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``. A class-level ``_inner_lock`` guards both
singleton creation and one-time initialization; an instance-level
``_lock`` guards every public method body. Consumers should obtain the
instance through :func:`get_cutscene_player`.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest
# entry is evicted in FIFO order to keep memory growth predictable
# across long-running sessions and large cutscene libraries.
_MAX_CUTSCENES: int = 500
_MAX_TRACKS: int = 2000
_MAX_CLIPS: int = 10000
_MAX_CAMERA_KEYFRAMES: int = 10000
_MAX_SUBTITLES: int = 10000
_MAX_ACTOR_CUES: int = 10000
_MAX_AUDIO_CUES: int = 10000
_MAX_CHECKPOINTS: int = 5000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Used as the default factory for timestamp fields on data classes
    and on every audit event the player emits.
    """
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier
            with an underscore. When omitted, the bare hex id is
            returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``.

    Eviction order is the natural list order (front is oldest). The
    store is mutated in place.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload.

    Enums are unwrapped to their ``.value`` strings. Dataclasses are
    serialized through :func:`_dataclass_to_dict`. Lists, tuples and
    dicts are walked recursively. Anything else is returned as-is.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance to a plain dictionary.

    Each value is passed through :func:`_to_jsonable` so that nested
    enums or dataclasses are also serialized. The returned dictionary
    is a shallow copy of the dataclass's fields.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _enum_value(value: Any, enum_cls: Optional[type] = None) -> str:
    """Normalize an enum or string into its underlying string value.

    Accepts either an ``Enum`` member (its ``.value`` is returned) or a
    plain string (returned unchanged). When ``enum_cls`` is supplied
    and ``value`` is a string matching a member value, the member is
    resolved first so that invalid values raise ``ValueError``.
    """
    if isinstance(value, Enum):
        return value.value
    if enum_cls is not None and isinstance(value, str):
        return enum_cls(value).value
    return str(value)


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class TrackType(Enum):
    """Kind of content carried by a timeline track.

    - ``CAMERA``: cinematic camera movement and framing.
    - ``ACTOR``: in-world character blocking and actions.
    - ``SUBTITLE``: timed caption and dialogue text.
    - ``AUDIO``: sound effects, music and ambience.
    - ``EFFECT``: visual effects such as particles and shaders.
    - ``ANIMATION``: scripted animation playback.
    - ``LIGHTING``: scene lighting changes and color grading.
    - ``WEATHER``: dynamic weather and atmosphere state.
    """

    CAMERA = "camera"
    ACTOR = "actor"
    SUBTITLE = "subtitle"
    AUDIO = "audio"
    EFFECT = "effect"
    ANIMATION = "animation"
    LIGHTING = "lighting"
    WEATHER = "weather"


class PlaybackState(Enum):
    """Transport state of a single cutscene playback session.

    - ``STOPPED``: not playing; position reset to the start.
    - ``PLAYING``: actively advancing along the timeline.
    - ``PAUSED``: held at the current position.
    - ``SEEKING``: jumping to a new position.
    - ``FINISHED``: reached the end of the cutscene.
    """

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    SEEKING = "seeking"
    FINISHED = "finished"


class CutscenePriority(Enum):
    """Scheduling priority for a cutscene asset.

    - ``BACKGROUND``: ambient playback that yields to everything.
    - ``NORMAL``: default storytelling priority.
    - ``IMPORTANT``: key narrative beat that blocks lower priority.
    - ``CRITICAL``: must-play moment such as a boss intro.
    - ``SYSTEM``: engine-driven cutscene that cannot be skipped.
    """

    BACKGROUND = "background"
    NORMAL = "normal"
    IMPORTANT = "important"
    CRITICAL = "critical"
    SYSTEM = "system"


class LoopMode(Enum):
    """How playback behaves when it reaches the end of the cutscene.

    - ``NONE``: stop at the end.
    - ``LOOP``: restart from the beginning.
    - ``PING_PONG``: reverse direction at each end.
    - ``LOOP_SEGMENT``: loop a bounded sub-range of the timeline.
    """

    NONE = "none"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    LOOP_SEGMENT = "loop_segment"


class CutscenePlayerEventKind(Enum):
    """Kinds of audit events emitted by the cutscene player."""

    CUTSCENE_LOADED = "cutscene_loaded"
    CUTSCENE_UNLOADED = "cutscene_unloaded"
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_RESUMED = "playback_resumed"
    PLAYBACK_STOPPED = "playback_stopped"
    PLAYBACK_SEEKED = "playback_seeked"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"
    TRACK_UPDATED = "track_updated"
    SUBTITLE_SHOWN = "subtitle_shown"
    SUBTITLE_HIDDEN = "subtitle_hidden"
    CHECKPOINT_REACHED = "checkpoint_reached"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class TimelineTrack:
    """A single ordered layer inside a cutscene timeline.

    Tracks group related clips (for example all camera moves or all
    subtitle lines). A track can be disabled to mute its clips during
    playback, and locked to prevent editing in authoring tools.
    """

    track_id: str = field(default_factory=lambda: _new_id("track"))
    cutscene_id: str = ""
    track_type: str = TrackType.CAMERA.value
    name: str = ""
    enabled: bool = True
    locked: bool = False
    sort_order: int = 0
    clip_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "cutscene_id": self.cutscene_id,
            "track_type": self.track_type,
            "name": self.name,
            "enabled": self.enabled,
            "locked": self.locked,
            "sort_order": self.sort_order,
            "clip_count": self.clip_count,
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class TimelineClip:
    """A time-bounded segment that lives on a timeline track.

    Clips carry a start time and duration on the cutscene timeline,
    optional trim offsets for the source material, blend ramps for
    smooth transitions, and an arbitrary properties bag for
    type-specific data.
    """

    clip_id: str = field(default_factory=lambda: _new_id("clip"))
    track_id: str = ""
    cutscene_id: str = ""
    name: str = ""
    start_time: float = 0.0
    duration: float = 0.0
    start_offset: float = 0.0
    end_offset: float = 0.0
    blend_in: float = 0.0
    blend_out: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "track_id": self.track_id,
            "cutscene_id": self.cutscene_id,
            "name": self.name,
            "start_time": self.start_time,
            "duration": self.duration,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "blend_in": self.blend_in,
            "blend_out": self.blend_out,
            "properties": _to_jsonable(self.properties),
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class CameraKeyframe:
    """A single camera sample inside a camera clip.

    Stores per-axis position and rotation (Euler angles in degrees),
    a field-of-view value, the time offset relative to the parent
    clip start, and the interpolation mode to use when blending toward
    the next keyframe.
    """

    keyframe_id: str = field(default_factory=lambda: _new_id("kf"))
    clip_id: str = ""
    time_offset: float = 0.0
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    fov: float = 60.0
    interpolation: str = "linear"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyframe_id": self.keyframe_id,
            "clip_id": self.clip_id,
            "time_offset": self.time_offset,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "position_z": self.position_z,
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "rotation_z": self.rotation_z,
            "fov": self.fov,
            "interpolation": self.interpolation,
        }


@dataclass
class SubtitleEntry:
    """A timed caption shown during a cutscene.

    Each entry has a start and end time on the cutscene timeline, the
    speaker identifier, the localized text, the language code, font
    size, an HTML-style color string, and a normalized screen position
    in the 0..1 range.
    """

    entry_id: str = field(default_factory=lambda: _new_id("sub"))
    clip_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    speaker_id: str = ""
    text: str = ""
    language: str = "en"
    font_size: int = 24
    color: str = "#FFFFFF"
    position_x: float = 0.5
    position_y: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "clip_id": self.clip_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker_id": self.speaker_id,
            "text": self.text,
            "language": self.language,
            "font_size": self.font_size,
            "color": self.color,
            "position_x": self.position_x,
            "position_y": self.position_y,
        }


@dataclass
class ActorCue:
    """A blocking direction for a single actor within a clip.

    Specifies the actor, the start time on the cutscene timeline, the
    action name, action parameters, the target world position and
    rotation to move toward, and the blend time for the transition.
    """

    cue_id: str = field(default_factory=lambda: _new_id("act"))
    clip_id: str = ""
    actor_id: str = ""
    start_time: float = 0.0
    action_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    target_position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    target_rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    blend_time: float = 0.2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "clip_id": self.clip_id,
            "actor_id": self.actor_id,
            "start_time": self.start_time,
            "action_name": self.action_name,
            "parameters": _to_jsonable(self.parameters),
            "target_position": list(self.target_position),
            "target_rotation": list(self.target_rotation),
            "blend_time": self.blend_time,
        }


@dataclass
class AudioCue:
    """A sound playback instruction within a clip.

    Carries the audio asset id, the start time on the cutscene
    timeline, volume and pitch multipliers, a loop flag, fade-in and
    fade-out durations, and a spatial position for 3D mixing.
    """

    cue_id: str = field(default_factory=lambda: _new_id("aud"))
    clip_id: str = ""
    audio_id: str = ""
    start_time: float = 0.0
    volume: float = 1.0
    pitch: float = 1.0
    loop: bool = False
    fade_in: float = 0.0
    fade_out: float = 0.0
    spatial_position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "clip_id": self.clip_id,
            "audio_id": self.audio_id,
            "start_time": self.start_time,
            "volume": self.volume,
            "pitch": self.pitch,
            "loop": self.loop,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "spatial_position": list(self.spatial_position),
        }


@dataclass
class CutsceneAsset:
    """Top-level definition of a single cutscene.

    Holds the title, description, total duration, scheduling priority,
    loop behavior, cached track and clip counts, creation and update
    timestamps, and an arbitrary metadata bag.
    """

    cutscene_id: str = field(default_factory=lambda: _new_id("cs"))
    title: str = ""
    description: str = ""
    duration: float = 0.0
    priority: str = CutscenePriority.NORMAL.value
    loop_mode: str = LoopMode.NONE.value
    track_count: int = 0
    clip_count: int = 0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cutscene_id": self.cutscene_id,
            "title": self.title,
            "description": self.description,
            "duration": self.duration,
            "priority": self.priority,
            "loop_mode": self.loop_mode,
            "track_count": self.track_count,
            "clip_count": self.clip_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class PlaybackCheckpoint:
    """A named seek target inside a cutscene.

    Checkpoints mark story beats the player can skip to (when
    ``can_skip_to`` is True) and are recorded with the timeline
    position they point at.
    """

    checkpoint_id: str = field(default_factory=lambda: _new_id("ckpt"))
    cutscene_id: str = ""
    time_position: float = 0.0
    label: str = ""
    can_skip_to: bool = True
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "cutscene_id": self.cutscene_id,
            "time_position": self.time_position,
            "label": self.label,
            "can_skip_to": self.can_skip_to,
            "created_at": self.created_at,
        }


@dataclass
class CutscenePlayerStats:
    """Aggregate counters summarizing the player's current state."""

    total_cutscenes: int = 0
    loaded_cutscenes: int = 0
    total_tracks: int = 0
    total_clips: int = 0
    total_subtitles: int = 0
    total_playbacks: int = 0
    total_checkpoints: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cutscenes": self.total_cutscenes,
            "loaded_cutscenes": self.loaded_cutscenes,
            "total_tracks": self.total_tracks,
            "total_clips": self.total_clips,
            "total_subtitles": self.total_subtitles,
            "total_playbacks": self.total_playbacks,
            "total_checkpoints": self.total_checkpoints,
            "last_updated": self.last_updated,
        }


@dataclass
class CutscenePlayerSnapshot:
    """Immutable point-in-time capture of the entire player state."""

    cutscenes: List[CutsceneAsset] = field(default_factory=list)
    tracks: List[TimelineTrack] = field(default_factory=list)
    clips: List[TimelineClip] = field(default_factory=list)
    camera_keyframes: List[CameraKeyframe] = field(default_factory=list)
    subtitles: List[SubtitleEntry] = field(default_factory=list)
    actor_cues: List[ActorCue] = field(default_factory=list)
    audio_cues: List[AudioCue] = field(default_factory=list)
    checkpoints: List[PlaybackCheckpoint] = field(default_factory=list)
    current_playback: Dict[str, Any] = field(default_factory=dict)
    stats: CutscenePlayerStats = field(default_factory=CutscenePlayerStats)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cutscenes": [c.to_dict() for c in self.cutscenes],
            "tracks": [t.to_dict() for t in self.tracks],
            "clips": [c.to_dict() for c in self.clips],
            "camera_keyframes": [k.to_dict() for k in self.camera_keyframes],
            "subtitles": [s.to_dict() for s in self.subtitles],
            "actor_cues": [a.to_dict() for a in self.actor_cues],
            "audio_cues": [a.to_dict() for a in self.audio_cues],
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "current_playback": _to_jsonable(self.current_playback),
            "stats": self.stats.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class CutscenePlayerEvent:
    """A single audit log entry emitted by the cutscene player."""

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: str = CutscenePlayerEventKind.CUTSCENE_LOADED.value
    cutscene_id: str = ""
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "cutscene_id": self.cutscene_id,
            "timestamp": self.timestamp,
            "payload": _to_jsonable(self.payload),
        }


# ---------------------------------------------------------------------------
# Cutscene Player
# ---------------------------------------------------------------------------


class CutscenePlayer:
    """Cinematic cutscene playback system for the SparkLabs engine.

    The player owns a library of cutscene assets, each containing
    timeline tracks, clips and the per-clip camera keyframes,
    subtitles, actor cues and audio cues that drive playback. It also
    tracks per-cutscene transport state (stopped / playing / paused /
    seeking / finished), named checkpoints, an audit log of events,
    aggregate stats and a full-state snapshot helper.

    Implements the singleton pattern with double-checked locking
    using ``threading.RLock``. A class-level ``_inner_lock`` guards
    singleton creation and one-time initialization; an instance-level
    ``_lock`` guards every public method body. Consumers should obtain
    the instance through :func:`get_cutscene_player`.

    Usage:
        player = get_cutscene_player()
        cutscene = player.load_cutscene(
            title="Opening",
            description="The hero arrives at the city.",
            duration=42.0,
            priority=CutscenePriority.IMPORTANT,
            loop_mode=LoopMode.NONE,
            metadata={"chapter": 1},
        )
        track = player.add_track(
            cutscene_id=cutscene.cutscene_id,
            track_type=TrackType.CAMERA,
            name="Main Camera",
            sort_order=0,
        )
        player.play(cutscene.cutscene_id)
        print(player.get_status())
    """

    _instance: Optional["CutscenePlayer"] = None
    _inner_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "CutscenePlayer":
        # Double-checked locking on the class-level _inner_lock. The
        # outer check avoids taking the lock on the hot path once the
        # singleton exists; the inner check prevents a race between
        # two threads that both observed _instance as None. The
        # freshly allocated instance is marked not-yet-initialized so
        # that __init__ performs the real one-time setup.
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CutscenePlayer":
        """Return the singleton player instance (constructs on first use)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # One-time initialization guard. The outer check avoids taking
        # the lock on the hot path once initialization is complete; the
        # inner check prevents a race between two threads that both
        # observed _initialized as False. The class-level _inner_lock
        # is reused here so singleton creation and initialization are
        # mutually exclusive.
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return

            # Instance-level re-entrant lock guarding every public
            # method body. Set before any store is populated so that
            # helper methods can safely acquire it during seeding.
            self._lock = threading.RLock()

            # Primary stores keyed by their entity id.
            self._cutscenes: Dict[str, CutsceneAsset] = {}
            self._tracks: Dict[str, TimelineTrack] = {}
            self._clips: Dict[str, TimelineClip] = {}
            self._camera_keyframes: Dict[str, CameraKeyframe] = {}
            self._subtitles: Dict[str, SubtitleEntry] = {}
            self._actor_cues: Dict[str, ActorCue] = {}
            self._audio_cues: Dict[str, AudioCue] = {}
            self._checkpoints: Dict[str, PlaybackCheckpoint] = {}
            self._events: List[CutscenePlayerEvent] = []

            # Per-parent index maps so accessor methods do not have to
            # scan the global stores. Each maps a parent id to the
            # ordered list of child ids.
            self._tracks_by_cutscene: Dict[str, List[str]] = {}
            self._clips_by_cutscene: Dict[str, List[str]] = {}
            self._clips_by_track: Dict[str, List[str]] = {}
            self._keyframes_by_clip: Dict[str, List[str]] = {}
            self._subtitles_by_clip: Dict[str, List[str]] = {}
            self._subtitles_by_cutscene: Dict[str, List[str]] = {}
            self._actor_cues_by_clip: Dict[str, List[str]] = {}
            self._audio_cues_by_clip: Dict[str, List[str]] = {}
            self._checkpoints_by_cutscene: Dict[str, List[str]] = {}

            # Per-cutscene playback transport state. Each value is a
            # dict with state, position, started_at and updated_at.
            self._playback: Dict[str, Dict[str, Any]] = {}

            # Aggregate counters maintained for fast stats retrieval.
            self._cutscene_counter: int = 0
            self._track_counter: int = 0
            self._clip_counter: int = 0
            self._keyframe_counter: int = 0
            self._subtitle_counter: int = 0
            self._actor_cue_counter: int = 0
            self._audio_cue_counter: int = 0
            self._checkpoint_counter: int = 0
            self._event_counter: int = 0
            self._playback_counter: int = 0

            self._initialized: bool = True

            # Populate the default seed cutscene data.
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the player with seed cutscenes and timeline content.

        The seed demonstrates a small but representative data set:

          - 2 cutscenes (an opening cinematic and a finale).
          - 5 tracks spanning camera, subtitle, actor and audio types.
          - 8 clips distributed across the tracks.
          - 5 camera keyframes forming two camera paths.
          - 6 subtitle entries in English covering two speakers.
          - 4 actor cues driving hero and companion blocking.
          - 4 audio cues for music, ambience and effects.
          - 3 named checkpoints marking skip targets.
        """
        # ------------------------------------------------------------------
        # Cutscene 1: the opening cinematic.
        # ------------------------------------------------------------------
        cs1 = self.load_cutscene(
            title="Arrival at Dawnhold",
            description="The hero arrives at the city of Dawnhold as dawn breaks.",
            duration=48.0,
            priority=CutscenePriority.IMPORTANT,
            loop_mode=LoopMode.NONE,
            metadata={"chapter": 1, "director": "narrative_team", "seed": True},
        )

        # Camera track for the opening cinematic.
        cam_track_1 = self.add_track(
            cutscene_id=cs1.cutscene_id,
            track_type=TrackType.CAMERA,
            name="Opening Camera",
            sort_order=0,
            metadata={"seed": True},
        )
        # Subtitle track for the opening cinematic.
        sub_track_1 = self.add_track(
            cutscene_id=cs1.cutscene_id,
            track_type=TrackType.SUBTITLE,
            name="Opening Dialogue",
            sort_order=1,
            metadata={"seed": True},
        )
        # Actor track for the opening cinematic.
        act_track_1 = self.add_track(
            cutscene_id=cs1.cutscene_id,
            track_type=TrackType.ACTOR,
            name="Opening Blocking",
            sort_order=2,
            metadata={"seed": True},
        )

        # Two camera clips with five keyframes between them.
        cam_clip_1a = self.add_clip(
            track_id=cam_track_1.track_id,
            cutscene_id=cs1.cutscene_id,
            name="Establishing Sweep",
            start_time=0.0,
            duration=18.0,
            properties={"lens": "35mm", "seed": True},
            metadata={"seed": True},
        )
        cam_clip_1b = self.add_clip(
            track_id=cam_track_1.track_id,
            cutscene_id=cs1.cutscene_id,
            name="Hero Close-Up",
            start_time=18.0,
            duration=30.0,
            properties={"lens": "85mm", "seed": True},
            metadata={"seed": True},
        )
        self.add_camera_keyframe(
            clip_id=cam_clip_1a.clip_id,
            time_offset=0.0,
            position=(-120.0, 40.0, 220.0),
            rotation=(12.0, 28.0, 0.0),
            fov=55.0,
            interpolation="ease_in_out",
        )
        self.add_camera_keyframe(
            clip_id=cam_clip_1a.clip_id,
            time_offset=8.0,
            position=(-60.0, 30.0, 160.0),
            rotation=(8.0, 18.0, 0.0),
            fov=50.0,
            interpolation="ease_in_out",
        )
        self.add_camera_keyframe(
            clip_id=cam_clip_1a.clip_id,
            time_offset=16.0,
            position=(-20.0, 22.0, 110.0),
            rotation=(5.0, 10.0, 0.0),
            fov=45.0,
            interpolation="linear",
        )
        self.add_camera_keyframe(
            clip_id=cam_clip_1b.clip_id,
            time_offset=0.0,
            position=(20.0, 18.0, 80.0),
            rotation=(2.0, -8.0, 0.0),
            fov=40.0,
            interpolation="ease_out",
        )
        self.add_camera_keyframe(
            clip_id=cam_clip_1b.clip_id,
            time_offset=12.0,
            position=(30.0, 16.0, 60.0),
            rotation=(1.0, -6.0, 0.0),
            fov=35.0,
            interpolation="linear",
        )

        # Two subtitle clips with six subtitle entries.
        sub_clip_1a = self.add_clip(
            track_id=sub_track_1.track_id,
            cutscene_id=cs1.cutscene_id,
            name="Narrator Lines",
            start_time=2.0,
            duration=16.0,
            properties={"box": "lower_third", "seed": True},
            metadata={"seed": True},
        )
        sub_clip_1b = self.add_clip(
            track_id=sub_track_1.track_id,
            cutscene_id=cs1.cutscene_id,
            name="Hero Lines",
            start_time=20.0,
            duration=26.0,
            properties={"box": "lower_third", "seed": True},
            metadata={"seed": True},
        )
        self.add_subtitle(
            clip_id=sub_clip_1a.clip_id,
            start_time=2.0,
            end_time=7.0,
            speaker_id="narrator",
            text="The road to Dawnhold had been long.",
            language="en",
            font_size=26,
            color="#E8E8E8",
            position=(0.5, 0.82),
        )
        self.add_subtitle(
            clip_id=sub_clip_1a.clip_id,
            start_time=8.0,
            end_time=13.0,
            speaker_id="narrator",
            text="But the city rose to meet the morning light.",
            language="en",
            font_size=26,
            color="#E8E8E8",
            position=(0.5, 0.82),
        )
        self.add_subtitle(
            clip_id=sub_clip_1a.clip_id,
            start_time=14.0,
            end_time=17.0,
            speaker_id="narrator",
            text="And so it began.",
            language="en",
            font_size=26,
            color="#E8E8E8",
            position=(0.5, 0.82),
        )
        self.add_subtitle(
            clip_id=sub_clip_1b.clip_id,
            start_time=21.0,
            end_time=26.0,
            speaker_id="hero",
            text="So this is Dawnhold.",
            language="en",
            font_size=24,
            color="#FFFFFF",
            position=(0.5, 0.8),
        )
        self.add_subtitle(
            clip_id=sub_clip_1b.clip_id,
            start_time=27.0,
            end_time=33.0,
            speaker_id="hero",
            text="Bigger than the stories said.",
            language="en",
            font_size=24,
            color="#FFFFFF",
            position=(0.5, 0.8),
        )
        self.add_subtitle(
            clip_id=sub_clip_1b.clip_id,
            start_time=35.0,
            end_time=42.0,
            speaker_id="hero",
            text="Let's see what waits inside.",
            language="en",
            font_size=24,
            color="#FFFFFF",
            position=(0.5, 0.8),
        )

        # One actor clip with four actor cues.
        act_clip_1 = self.add_clip(
            track_id=act_track_1.track_id,
            cutscene_id=cs1.cutscene_id,
            name="Hero Approach",
            start_time=4.0,
            duration=40.0,
            properties={"root_motion": True, "seed": True},
            metadata={"seed": True},
        )
        self.add_actor_cue(
            clip_id=act_clip_1.clip_id,
            actor_id="hero",
            start_time=4.0,
            action_name="walk_to",
            parameters={"speed": 1.0},
            target_position=(10.0, 0.0, 70.0),
            target_rotation=(0.0, 0.0, 0.0),
            blend_time=0.3,
        )
        self.add_actor_cue(
            clip_id=act_clip_1.clip_id,
            actor_id="hero",
            start_time=20.0,
            action_name="look_up",
            parameters={"duration": 3.0},
            target_position=(10.0, 0.0, 70.0),
            target_rotation=(-25.0, 0.0, 0.0),
            blend_time=0.2,
        )
        self.add_actor_cue(
            clip_id=act_clip_1.clip_id,
            actor_id="companion",
            start_time=8.0,
            action_name="walk_to",
            parameters={"speed": 0.9},
            target_position=(6.0, 0.0, 74.0),
            target_rotation=(0.0, 10.0, 0.0),
            blend_time=0.3,
        )
        self.add_actor_cue(
            clip_id=act_clip_1.clip_id,
            actor_id="companion",
            start_time=34.0,
            action_name="gesture",
            parameters={"gesture": "wave", "duration": 2.0},
            target_position=(6.0, 0.0, 74.0),
            target_rotation=(0.0, -15.0, 0.0),
            blend_time=0.15,
        )

        # Checkpoints for the opening cinematic.
        self.add_checkpoint(
            cutscene_id=cs1.cutscene_id,
            time_position=0.0,
            label="Start",
            can_skip_to=True,
        )
        self.add_checkpoint(
            cutscene_id=cs1.cutscene_id,
            time_position=18.0,
            label="Hero Close-Up",
            can_skip_to=True,
        )

        # ------------------------------------------------------------------
        # Cutscene 2: the finale.
        # ------------------------------------------------------------------
        cs2 = self.load_cutscene(
            title="The Final Stand",
            description="The hero confronts the antagonist atop the spire.",
            duration=72.0,
            priority=CutscenePriority.CRITICAL,
            loop_mode=LoopMode.NONE,
            metadata={"chapter": 12, "director": "narrative_team", "seed": True},
        )

        # Camera track for the finale.
        cam_track_2 = self.add_track(
            cutscene_id=cs2.cutscene_id,
            track_type=TrackType.CAMERA,
            name="Finale Camera",
            sort_order=0,
            metadata={"seed": True},
        )
        # Audio track for the finale.
        aud_track_2 = self.add_track(
            cutscene_id=cs2.cutscene_id,
            track_type=TrackType.AUDIO,
            name="Finale Audio",
            sort_order=1,
            metadata={"seed": True},
        )

        # Two camera clips (no extra keyframes beyond the opening set
        # so the total keyframe count stays at five).
        self.add_clip(
            track_id=cam_track_2.track_id,
            cutscene_id=cs2.cutscene_id,
            name="Spire Reveal",
            start_time=0.0,
            duration=24.0,
            properties={"lens": "24mm", "seed": True},
            metadata={"seed": True},
        )
        self.add_clip(
            track_id=cam_track_2.track_id,
            cutscene_id=cs2.cutscene_id,
            name="Confrontation",
            start_time=24.0,
            duration=48.0,
            properties={"lens": "50mm", "seed": True},
            metadata={"seed": True},
        )

        # One audio clip with four audio cues.
        aud_clip_2 = self.add_clip(
            track_id=aud_track_2.track_id,
            cutscene_id=cs2.cutscene_id,
            name="Finale Soundtrack",
            start_time=0.0,
            duration=72.0,
            properties={"mix": "cinematic", "seed": True},
            metadata={"seed": True},
        )
        self.add_audio_cue(
            clip_id=aud_clip_2.clip_id,
            audio_id="mus_finale_theme",
            start_time=0.0,
            volume=0.85,
            pitch=1.0,
            loop=False,
            fade_in=2.0,
            fade_out=3.0,
            spatial_position=(0.0, 0.0, 0.0),
        )
        self.add_audio_cue(
            clip_id=aud_clip_2.clip_id,
            audio_id="amb_wind_spire",
            start_time=0.0,
            volume=0.4,
            pitch=1.0,
            loop=True,
            fade_in=4.0,
            fade_out=4.0,
            spatial_position=(0.0, 0.0, 0.0),
        )
        self.add_audio_cue(
            clip_id=aud_clip_2.clip_id,
            audio_id="sfx_sword_clash",
            start_time=30.0,
            volume=1.0,
            pitch=1.0,
            loop=False,
            fade_in=0.0,
            fade_out=0.5,
            spatial_position=(12.0, 5.0, 20.0),
        )
        self.add_audio_cue(
            clip_id=aud_clip_2.clip_id,
            audio_id="vox_antagonist_taunt",
            start_time=40.0,
            volume=0.95,
            pitch=1.0,
            loop=False,
            fade_in=0.1,
            fade_out=0.4,
            spatial_position=(8.0, 6.0, 18.0),
        )

        # Checkpoint for the finale.
        self.add_checkpoint(
            cutscene_id=cs2.cutscene_id,
            time_position=30.0,
            label="The Clash",
            can_skip_to=False,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: CutscenePlayerEventKind,
        cutscene_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> CutscenePlayerEvent:
        """Record an audit event (caller must hold ``self._lock``).

        Returns the created CutscenePlayerEvent. Evicts the oldest
        event when the event store is at capacity.
        """
        event = CutscenePlayerEvent(
            kind=kind.value,
            cutscene_id=cutscene_id,
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    def _index_append(self, index: Dict[str, List[str]], key: str, value: str) -> None:
        """Append a child id to a parent-keyed index list (caller holds lock)."""
        bucket = index.get(key)
        if bucket is None:
            bucket = []
            index[key] = bucket
        bucket.append(value)

    def _index_remove(self, index: Dict[str, List[str]], key: str, value: str) -> None:
        """Remove a child id from a parent-keyed index list (caller holds lock)."""
        bucket = index.get(key)
        if not bucket:
            return
        try:
            bucket.remove(value)
        except ValueError:
            return
        if not bucket:
            index.pop(key, None)

    def _touch(self, cutscene_id: str) -> None:
        """Refresh the updated_at timestamp on a cutscene (caller holds lock)."""
        asset = self._cutscenes.get(cutscene_id)
        if asset is not None:
            asset.updated_at = _now()

    def _recount_cutscene(self, cutscene_id: str) -> None:
        """Recompute track and clip counts for a cutscene (caller holds lock)."""
        asset = self._cutscenes.get(cutscene_id)
        if asset is None:
            return
        track_ids = self._tracks_by_cutscene.get(cutscene_id, [])
        asset.track_count = len(track_ids)
        clip_ids = self._clips_by_cutscene.get(cutscene_id, [])
        asset.clip_count = len(clip_ids)
        asset.updated_at = _now()

    # ------------------------------------------------------------------
    # FIFO eviction helpers
    # ------------------------------------------------------------------
    #
    # Each helper evicts the oldest entries from a store until the
    # store is at or below its capacity. Eviction runs AFTER an
    # insertion so the store never exceeds its cap. Parent stores
    # cascade-remove their children so no orphaned data or dangling
    # index entries remain. Eviction is performed quietly: no audit
    # events are recorded, which keeps the event log focused on
    # caller-driven actions and avoids feedback during eviction.

    def _evict_oldest_cutscene(self) -> None:
        """Evict oldest cutscenes (with full cascade) until at or below cap."""
        while len(self._cutscenes) > _MAX_CUTSCENES:
            oldest_id = next(iter(self._cutscenes), None)
            if oldest_id is None:
                break
            self._unload_internal(oldest_id, quiet=True)

    def _evict_oldest_track(self) -> None:
        """Evict oldest tracks (with clip cascade) until at or below cap."""
        while len(self._tracks) > _MAX_TRACKS:
            oldest_id = next(iter(self._tracks), None)
            if oldest_id is None:
                break
            self._remove_track_internal(oldest_id, quiet=True)

    def _evict_oldest_clip(self) -> None:
        """Evict oldest clips (with child cascade) until at or below cap."""
        while len(self._clips) > _MAX_CLIPS:
            oldest_id = next(iter(self._clips), None)
            if oldest_id is None:
                break
            self._remove_clip_internal(oldest_id, quiet=True)

    def _evict_oldest_keyframe(self) -> None:
        """Evict oldest camera keyframes until at or below cap."""
        while len(self._camera_keyframes) > _MAX_CAMERA_KEYFRAMES:
            oldest_id = next(iter(self._camera_keyframes), None)
            if oldest_id is None:
                break
            keyframe = self._camera_keyframes.pop(oldest_id)
            self._index_remove(self._keyframes_by_clip, keyframe.clip_id, oldest_id)
            self._keyframe_counter = max(0, self._keyframe_counter - 1)

    def _evict_oldest_subtitle(self) -> None:
        """Evict oldest subtitle entries until at or below cap."""
        while len(self._subtitles) > _MAX_SUBTITLES:
            oldest_id = next(iter(self._subtitles), None)
            if oldest_id is None:
                break
            entry = self._subtitles.pop(oldest_id)
            self._index_remove(self._subtitles_by_clip, entry.clip_id, oldest_id)
            clip = self._clips.get(entry.clip_id)
            if clip is not None:
                self._index_remove(self._subtitles_by_cutscene, clip.cutscene_id, oldest_id)
            self._subtitle_counter = max(0, self._subtitle_counter - 1)

    def _evict_oldest_actor_cue(self) -> None:
        """Evict oldest actor cues until at or below cap."""
        while len(self._actor_cues) > _MAX_ACTOR_CUES:
            oldest_id = next(iter(self._actor_cues), None)
            if oldest_id is None:
                break
            cue = self._actor_cues.pop(oldest_id)
            self._index_remove(self._actor_cues_by_clip, cue.clip_id, oldest_id)
            self._actor_cue_counter = max(0, self._actor_cue_counter - 1)

    def _evict_oldest_audio_cue(self) -> None:
        """Evict oldest audio cues until at or below cap."""
        while len(self._audio_cues) > _MAX_AUDIO_CUES:
            oldest_id = next(iter(self._audio_cues), None)
            if oldest_id is None:
                break
            cue = self._audio_cues.pop(oldest_id)
            self._index_remove(self._audio_cues_by_clip, cue.clip_id, oldest_id)
            self._audio_cue_counter = max(0, self._audio_cue_counter - 1)

    def _evict_oldest_checkpoint(self) -> None:
        """Evict oldest checkpoints until at or below cap."""
        while len(self._checkpoints) > _MAX_CHECKPOINTS:
            oldest_id = next(iter(self._checkpoints), None)
            if oldest_id is None:
                break
            checkpoint = self._checkpoints.pop(oldest_id)
            self._index_remove(self._checkpoints_by_cutscene, checkpoint.cutscene_id, oldest_id)
            self._checkpoint_counter = max(0, self._checkpoint_counter - 1)

    # ------------------------------------------------------------------
    # Cutscene lifecycle
    # ------------------------------------------------------------------

    def load_cutscene(
        self,
        title: str,
        description: str = "",
        duration: float = 0.0,
        priority: Union[CutscenePriority, str] = CutscenePriority.NORMAL,
        loop_mode: Union[LoopMode, str] = LoopMode.NONE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CutsceneAsset:
        """Register a new cutscene asset and return it.

        A ``cutscene_loaded`` audit event is recorded. When the
        cutscene store is at capacity the oldest cutscene (and its
        tracks, clips and child entities) is evicted in FIFO order.
        """
        with self._lock:
            asset = CutsceneAsset(
                title=title,
                description=description,
                duration=max(0.0, float(duration)),
                priority=_enum_value(priority, CutscenePriority),
                loop_mode=_enum_value(loop_mode, LoopMode),
                metadata=dict(metadata) if metadata else {},
            )
            self._cutscenes[asset.cutscene_id] = asset
            self._cutscene_counter += 1
            self._evict_oldest_cutscene()
            self._record_event(
                CutscenePlayerEventKind.CUTSCENE_LOADED,
                cutscene_id=asset.cutscene_id,
                payload={"title": title, "duration": asset.duration},
            )
            return asset

    def unload_cutscene(self, cutscene_id: str) -> bool:
        """Remove a cutscene and all of its child entities.

        Returns True when a cutscene was removed, False when the id
        was unknown. A ``cutscene_unloaded`` event is recorded on
        success.
        """
        with self._lock:
            return self._unload_internal(cutscene_id, quiet=False)

    def _unload_internal(self, cutscene_id: str, quiet: bool = False) -> bool:
        """Internal cutscene removal without re-acquiring the lock.

        When ``quiet`` is True no audit event is recorded; this is
        used by FIFO eviction so the event log is not polluted with
        capacity-driven removals.
        """
        asset = self._cutscenes.get(cutscene_id)
        if asset is None:
            return False
        # Cascade remove every track and its clips plus the
        # per-clip children so no orphaned data remains.
        for track_id in list(self._tracks_by_cutscene.get(cutscene_id, [])):
            self._remove_track_internal(track_id, quiet=True)
        # Drop any remaining clips and child entities that may
        # have been indexed directly under the cutscene.
        for clip_id in list(self._clips_by_cutscene.get(cutscene_id, [])):
            self._remove_clip_internal(clip_id, quiet=True)
        self._subtitles_by_cutscene.pop(cutscene_id, None)
        for ckpt_id in list(self._checkpoints_by_cutscene.get(cutscene_id, [])):
            self._checkpoints.pop(ckpt_id, None)
            self._checkpoint_counter = max(0, self._checkpoint_counter - 1)
        self._checkpoints_by_cutscene.pop(cutscene_id, None)
        self._playback.pop(cutscene_id, None)
        self._cutscenes.pop(cutscene_id, None)
        self._cutscene_counter = max(0, self._cutscene_counter - 1)
        if not quiet:
            self._record_event(
                CutscenePlayerEventKind.CUTSCENE_UNLOADED,
                cutscene_id=cutscene_id,
                payload={"title": asset.title},
            )
        return True

    def get_cutscene(self, cutscene_id: str) -> Optional[CutsceneAsset]:
        """Return the cutscene asset for ``cutscene_id`` or None."""
        with self._lock:
            return self._cutscenes.get(cutscene_id)

    def list_cutscenes(
        self,
        priority: Optional[Union[CutscenePriority, str]] = None,
        limit: int = 100,
    ) -> List[CutsceneAsset]:
        """List cutscenes, optionally filtered by priority.

        Results are ordered by creation order (insertion order) and
        capped at ``limit``. A negative or zero limit returns an empty
        list.
        """
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            wanted = _enum_value(priority, CutscenePriority) if priority is not None else None
            out: List[CutsceneAsset] = []
            for asset in self._cutscenes.values():
                if wanted is not None and asset.priority != wanted:
                    continue
                out.append(asset)
                if len(out) >= cap:
                    break
            return out

    def update_cutscene(self, cutscene_id: str, **kwargs: Any) -> Optional[CutsceneAsset]:
        """Update editable fields on a cutscene asset.

        Accepts ``title``, ``description``, ``duration``, ``priority``,
        ``loop_mode`` and ``metadata`` as keyword arguments. The
        ``updated_at`` timestamp is refreshed and the updated asset is
        returned. Returns None when the cutscene id is unknown.
        """
        with self._lock:
            asset = self._cutscenes.get(cutscene_id)
            if asset is None:
                return None
            if "title" in kwargs:
                asset.title = str(kwargs["title"])
            if "description" in kwargs:
                asset.description = str(kwargs["description"])
            if "duration" in kwargs:
                asset.duration = max(0.0, float(kwargs["duration"]))
            if "priority" in kwargs:
                asset.priority = _enum_value(kwargs["priority"], CutscenePriority)
            if "loop_mode" in kwargs:
                asset.loop_mode = _enum_value(kwargs["loop_mode"], LoopMode)
            if "metadata" in kwargs:
                asset.metadata = dict(kwargs["metadata"]) if kwargs["metadata"] else {}
            asset.updated_at = _now()
            return asset

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def add_track(
        self,
        cutscene_id: str,
        track_type: Union[TrackType, str] = TrackType.CAMERA,
        name: str = "",
        sort_order: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TimelineTrack:
        """Add a timeline track to a cutscene and return it.

        Raises ``ValueError`` when the cutscene does not exist. A
        ``track_added`` event is recorded.
        """
        with self._lock:
            if cutscene_id not in self._cutscenes:
                raise ValueError(f"Unknown cutscene_id: {cutscene_id}")
            track = TimelineTrack(
                cutscene_id=cutscene_id,
                track_type=_enum_value(track_type, TrackType),
                name=name,
                sort_order=int(sort_order),
                metadata=dict(metadata) if metadata else {},
            )
            self._tracks[track.track_id] = track
            self._track_counter += 1
            self._index_append(self._tracks_by_cutscene, cutscene_id, track.track_id)
            self._evict_oldest_track()
            self._recount_cutscene(cutscene_id)
            self._record_event(
                CutscenePlayerEventKind.TRACK_ADDED,
                cutscene_id=cutscene_id,
                payload={"track_id": track.track_id, "track_type": track.track_type},
            )
            return track

    def get_track(self, track_id: str) -> Optional[TimelineTrack]:
        """Return the timeline track for ``track_id`` or None."""
        with self._lock:
            return self._tracks.get(track_id)

    def list_tracks(
        self,
        cutscene_id: Optional[str] = None,
        track_type: Optional[Union[TrackType, str]] = None,
        limit: int = 100,
    ) -> List[TimelineTrack]:
        """List tracks, optionally filtered by cutscene and track type.

        Results are ordered by sort_order then insertion order and
        capped at ``limit``.
        """
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            wanted_type = _enum_value(track_type, TrackType) if track_type is not None else None
            if cutscene_id is not None:
                ids = self._tracks_by_cutscene.get(cutscene_id, [])
                candidates = [self._tracks[tid] for tid in ids if tid in self._tracks]
            else:
                candidates = list(self._tracks.values())
            candidates.sort(key=lambda t: (t.sort_order, t.track_id))
            out: List[TimelineTrack] = []
            for track in candidates:
                if wanted_type is not None and track.track_type != wanted_type:
                    continue
                out.append(track)
                if len(out) >= cap:
                    break
            return out

    def update_track(self, track_id: str, **kwargs: Any) -> Optional[TimelineTrack]:
        """Update editable fields on a timeline track.

        Accepts ``track_type``, ``name``, ``enabled``, ``locked``,
        ``sort_order`` and ``metadata``. Returns None when the track
        id is unknown.
        """
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return None
            if "track_type" in kwargs:
                track.track_type = _enum_value(kwargs["track_type"], TrackType)
            if "name" in kwargs:
                track.name = str(kwargs["name"])
            if "enabled" in kwargs:
                track.enabled = bool(kwargs["enabled"])
            if "locked" in kwargs:
                track.locked = bool(kwargs["locked"])
            if "sort_order" in kwargs:
                track.sort_order = int(kwargs["sort_order"])
            if "metadata" in kwargs:
                track.metadata = dict(kwargs["metadata"]) if kwargs["metadata"] else {}
            self._touch(track.cutscene_id)
            self._record_event(
                CutscenePlayerEventKind.TRACK_UPDATED,
                cutscene_id=track.cutscene_id,
                payload={"track_id": track_id, "updated_fields": list(kwargs.keys())},
            )
            return track

    def remove_track(self, track_id: str) -> bool:
        """Remove a track and all of its clips (and their children).

        Returns True when a track was removed, False when the id was
        unknown. A ``track_removed`` event is recorded on success.
        """
        with self._lock:
            return self._remove_track_internal(track_id, quiet=False)

    def _remove_track_internal(self, track_id: str, quiet: bool = False) -> bool:
        """Internal track removal without re-acquiring the lock.

        When ``quiet`` is True no audit event is recorded; this is
        used during FIFO eviction and cascade removal.
        """
        track = self._tracks.get(track_id)
        if track is None:
            return False
        cutscene_id = track.cutscene_id
        for clip_id in list(self._clips_by_track.get(track_id, [])):
            self._remove_clip_internal(clip_id, quiet=True)
        self._tracks.pop(track_id, None)
        self._index_remove(self._tracks_by_cutscene, cutscene_id, track_id)
        self._track_counter = max(0, self._track_counter - 1)
        self._recount_cutscene(cutscene_id)
        if not quiet:
            self._record_event(
                CutscenePlayerEventKind.TRACK_REMOVED,
                cutscene_id=cutscene_id,
                payload={"track_id": track_id},
            )
        return True

    # ------------------------------------------------------------------
    # Clip management
    # ------------------------------------------------------------------

    def add_clip(
        self,
        track_id: str,
        cutscene_id: str,
        name: str = "",
        start_time: float = 0.0,
        duration: float = 0.0,
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TimelineClip:
        """Add a clip to a track and return it.

        Raises ``ValueError`` when the track or cutscene does not
        exist. The parent track's ``clip_count`` and the cutscene's
        ``clip_count`` are updated.
        """
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                raise ValueError(f"Unknown track_id: {track_id}")
            if cutscene_id not in self._cutscenes:
                raise ValueError(f"Unknown cutscene_id: {cutscene_id}")
            clip = TimelineClip(
                track_id=track_id,
                cutscene_id=cutscene_id,
                name=name,
                start_time=max(0.0, float(start_time)),
                duration=max(0.0, float(duration)),
                properties=dict(properties) if properties else {},
                metadata=dict(metadata) if metadata else {},
            )
            self._clips[clip.clip_id] = clip
            self._clip_counter += 1
            self._index_append(self._clips_by_track, track_id, clip.clip_id)
            self._index_append(self._clips_by_cutscene, cutscene_id, clip.clip_id)
            self._evict_oldest_clip()
            track.clip_count = len(self._clips_by_track.get(track_id, []))
            self._recount_cutscene(cutscene_id)
            self._touch(cutscene_id)
            return clip

    def get_clip(self, clip_id: str) -> Optional[TimelineClip]:
        """Return the timeline clip for ``clip_id`` or None."""
        with self._lock:
            return self._clips.get(clip_id)

    def list_clips(
        self,
        track_id: Optional[str] = None,
        cutscene_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[TimelineClip]:
        """List clips, optionally filtered by track and/or cutscene.

        Results are ordered by start_time then insertion order and
        capped at ``limit``.
        """
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            if track_id is not None:
                ids = self._clips_by_track.get(track_id, [])
                candidates = [self._clips[cid] for cid in ids if cid in self._clips]
            elif cutscene_id is not None:
                ids = self._clips_by_cutscene.get(cutscene_id, [])
                candidates = [self._clips[cid] for cid in ids if cid in self._clips]
            else:
                candidates = list(self._clips.values())
            candidates.sort(key=lambda c: (c.start_time, c.clip_id))
            return candidates[:cap]

    def update_clip(self, clip_id: str, **kwargs: Any) -> Optional[TimelineClip]:
        """Update editable fields on a timeline clip.

        Accepts ``name``, ``start_time``, ``duration``,
        ``start_offset``, ``end_offset``, ``blend_in``, ``blend_out``,
        ``properties`` and ``metadata``.
        """
        with self._lock:
            clip = self._clips.get(clip_id)
            if clip is None:
                return None
            if "name" in kwargs:
                clip.name = str(kwargs["name"])
            if "start_time" in kwargs:
                clip.start_time = max(0.0, float(kwargs["start_time"]))
            if "duration" in kwargs:
                clip.duration = max(0.0, float(kwargs["duration"]))
            if "start_offset" in kwargs:
                clip.start_offset = float(kwargs["start_offset"])
            if "end_offset" in kwargs:
                clip.end_offset = float(kwargs["end_offset"])
            if "blend_in" in kwargs:
                clip.blend_in = max(0.0, float(kwargs["blend_in"]))
            if "blend_out" in kwargs:
                clip.blend_out = max(0.0, float(kwargs["blend_out"]))
            if "properties" in kwargs:
                clip.properties = dict(kwargs["properties"]) if kwargs["properties"] else {}
            if "metadata" in kwargs:
                clip.metadata = dict(kwargs["metadata"]) if kwargs["metadata"] else {}
            self._touch(clip.cutscene_id)
            return clip

    def remove_clip(self, clip_id: str) -> bool:
        """Remove a clip and all of its child entities.

        Returns True when a clip was removed, False when the id was
        unknown.
        """
        with self._lock:
            return self._remove_clip_internal(clip_id, quiet=False)

    def _remove_clip_internal(self, clip_id: str, quiet: bool = False) -> bool:
        """Internal clip removal without re-acquiring the lock.

        When ``quiet`` is True no audit event is recorded; this is
        used during FIFO eviction and cascade removal.
        """
        clip = self._clips.get(clip_id)
        if clip is None:
            return False
        track_id = clip.track_id
        cutscene_id = clip.cutscene_id
        # Cascade remove per-clip children.
        for kf_id in list(self._keyframes_by_clip.get(clip_id, [])):
            self._camera_keyframes.pop(kf_id, None)
            self._keyframe_counter = max(0, self._keyframe_counter - 1)
        self._keyframes_by_clip.pop(clip_id, None)
        for sub_id in list(self._subtitles_by_clip.get(clip_id, [])):
            entry = self._subtitles.pop(sub_id, None)
            if entry is not None:
                self._index_remove(self._subtitles_by_cutscene, cutscene_id, sub_id)
                self._subtitle_counter = max(0, self._subtitle_counter - 1)
        self._subtitles_by_clip.pop(clip_id, None)
        for cue_id in list(self._actor_cues_by_clip.get(clip_id, [])):
            self._actor_cues.pop(cue_id, None)
            self._actor_cue_counter = max(0, self._actor_cue_counter - 1)
        self._actor_cues_by_clip.pop(clip_id, None)
        for cue_id in list(self._audio_cues_by_clip.get(clip_id, [])):
            self._audio_cues.pop(cue_id, None)
            self._audio_cue_counter = max(0, self._audio_cue_counter - 1)
        self._audio_cues_by_clip.pop(clip_id, None)
        # Remove the clip itself and update parent counts.
        self._clips.pop(clip_id, None)
        self._clip_counter = max(0, self._clip_counter - 1)
        self._index_remove(self._clips_by_track, track_id, clip_id)
        self._index_remove(self._clips_by_cutscene, cutscene_id, clip_id)
        track = self._tracks.get(track_id)
        if track is not None:
            track.clip_count = len(self._clips_by_track.get(track_id, []))
        self._recount_cutscene(cutscene_id)
        return True

    # ------------------------------------------------------------------
    # Camera keyframes
    # ------------------------------------------------------------------

    def _resolve_clip(self, clip_id: str, cutscene_id: str = "") -> str:
        """Resolve a clip_id, falling back to the first clip of a cutscene.

        When ``cutscene_id`` is supplied but no clip exists for that
        cutscene, a default track and clip are auto-created so that
        callers can add keyframes, subtitles, actor cues and audio cues
        without first manually creating timeline structure.
        """
        if clip_id and clip_id in self._clips:
            return clip_id
        if cutscene_id:
            for cid, clip in self._clips.items():
                if clip.cutscene_id == cutscene_id:
                    return cid
            if cutscene_id in self._cutscenes:
                track_id = ""
                for tid, track in self._tracks.items():
                    if track.cutscene_id == cutscene_id:
                        track_id = tid
                        break
                if not track_id:
                    new_track = TimelineTrack(
                        cutscene_id=cutscene_id,
                        track_type=TrackType.CAMERA.value,
                        name="auto",
                    )
                    self._tracks[new_track.track_id] = new_track
                    self._track_counter += 1
                    self._index_append(self._tracks_by_cutscene, cutscene_id, new_track.track_id)
                    track_id = new_track.track_id
                new_clip = TimelineClip(
                    track_id=track_id,
                    cutscene_id=cutscene_id,
                    name="auto",
                )
                self._clips[new_clip.clip_id] = new_clip
                self._clip_counter += 1
                self._index_append(self._clips_by_cutscene, cutscene_id, new_clip.clip_id)
                self._index_append(self._clips_by_track, track_id, new_clip.clip_id)
                parent_track = self._tracks.get(track_id)
                if parent_track is not None:
                    parent_track.clip_count += 1
                return new_clip.clip_id
        return clip_id

    @staticmethod
    def _vec3(value: Any, default: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> Tuple[float, float, float]:
        """Convert a list/tuple/dict to a 3-float tuple."""
        if isinstance(value, dict):
            return (float(value.get("x", 0.0)), float(value.get("y", 0.0)), float(value.get("z", 0.0)))
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            return (float(value[0]), float(value[1]), float(value[2]))
        return default

    @staticmethod
    def _frame_to_time(frame: Any, time_val: float = 0.0) -> float:
        """Convert a frame number to time in seconds (30fps), falling back to time_val."""
        if frame is not None and frame != "":
            try:
                return float(frame) / 30.0
            except (TypeError, ValueError):
                pass
        try:
            return float(time_val) if time_val else 0.0
        except (TypeError, ValueError):
            return 0.0

    def add_camera_keyframe(
        self,
        clip_id: str = "",
        time_offset: float = 0.0,
        position: Any = (0.0, 0.0, 0.0),
        rotation: Any = (0.0, 0.0, 0.0),
        fov: float = 60.0,
        interpolation: str = "linear",
        cutscene_id: str = "",
        frame: Any = None,
    ) -> CameraKeyframe:
        """Add a camera keyframe to a clip and return it.

        Raises ``ValueError`` when the clip does not exist.
        """
        with self._lock:
            cid = self._resolve_clip(clip_id, cutscene_id)
            if cid not in self._clips:
                raise ValueError(f"Unknown clip_id: {cid}")
            pos = self._vec3(position)
            rot = self._vec3(rotation)
            t_off = self._frame_to_time(frame, time_offset)
            keyframe = CameraKeyframe(
                clip_id=cid,
                time_offset=max(0.0, t_off),
                position_x=pos[0],
                position_y=pos[1],
                position_z=pos[2],
                rotation_x=rot[0],
                rotation_y=rot[1],
                rotation_z=rot[2],
                fov=float(fov),
                interpolation=str(interpolation),
            )
            self._camera_keyframes[keyframe.keyframe_id] = keyframe
            self._keyframe_counter += 1
            self._index_append(self._keyframes_by_clip, cid, keyframe.keyframe_id)
            self._evict_oldest_keyframe()
            clip = self._clips.get(cid)
            if clip is not None:
                self._touch(clip.cutscene_id)
            return keyframe

    def list_camera_keyframes(self, clip_id: str, limit: int = 100) -> List[CameraKeyframe]:
        """List camera keyframes for a clip ordered by time offset."""
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            ids = self._keyframes_by_clip.get(clip_id, [])
            candidates = [self._camera_keyframes[kid] for kid in ids if kid in self._camera_keyframes]
            candidates.sort(key=lambda k: (k.time_offset, k.keyframe_id))
            return candidates[:cap]

    # ------------------------------------------------------------------
    # Subtitles
    # ------------------------------------------------------------------

    def add_subtitle(
        self,
        clip_id: str = "",
        start_time: float = 0.0,
        end_time: float = 0.0,
        speaker_id: str = "",
        text: str = "",
        language: str = "en",
        font_size: int = 24,
        color: str = "#FFFFFF",
        position: Any = (0.5, 0.8),
        cutscene_id: str = "",
        start_frame: Any = None,
        end_frame: Any = None,
    ) -> SubtitleEntry:
        """Add a subtitle entry to a clip and return it.

        Raises ``ValueError`` when the clip does not exist. A
        ``subtitle_shown`` event is recorded.
        """
        with self._lock:
            cid = self._resolve_clip(clip_id, cutscene_id)
            clip = self._clips.get(cid)
            if clip is None:
                raise ValueError(f"Unknown clip_id: {cid}")
            s_time = self._frame_to_time(start_frame, start_time)
            e_time = self._frame_to_time(end_frame, end_time) if end_frame is not None else (float(end_time) if end_time else s_time)
            pos = position if isinstance(position, (list, tuple)) and len(position) >= 2 else (0.5, 0.8)
            entry = SubtitleEntry(
                clip_id=cid,
                start_time=max(0.0, s_time),
                end_time=max(s_time, e_time),
                speaker_id=str(speaker_id),
                text=str(text),
                language=str(language),
                font_size=int(font_size) if font_size else 24,
                color=str(color),
                position_x=float(pos[0]),
                position_y=float(pos[1]),
            )
            self._subtitles[entry.entry_id] = entry
            self._subtitle_counter += 1
            self._index_append(self._subtitles_by_clip, cid, entry.entry_id)
            self._index_append(self._subtitles_by_cutscene, clip.cutscene_id, entry.entry_id)
            self._evict_oldest_subtitle()
            self._touch(clip.cutscene_id)
            self._record_event(
                CutscenePlayerEventKind.SUBTITLE_SHOWN,
                cutscene_id=clip.cutscene_id,
                payload={"entry_id": entry.entry_id, "speaker_id": speaker_id},
            )
            return entry

    def get_subtitle(self, entry_id: str) -> Optional[SubtitleEntry]:
        """Return the subtitle entry for ``entry_id`` or None."""
        with self._lock:
            return self._subtitles.get(entry_id)

    def list_subtitles(
        self,
        cutscene_id: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 100,
    ) -> List[SubtitleEntry]:
        """List subtitles, optionally filtered by cutscene and language.

        Results are ordered by start_time then insertion order and
        capped at ``limit``.
        """
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            if cutscene_id is not None:
                ids = self._subtitles_by_cutscene.get(cutscene_id, [])
                candidates = [self._subtitles[eid] for eid in ids if eid in self._subtitles]
            else:
                candidates = list(self._subtitles.values())
            candidates.sort(key=lambda s: (s.start_time, s.entry_id))
            out: List[SubtitleEntry] = []
            for entry in candidates:
                if language is not None and entry.language != language:
                    continue
                out.append(entry)
                if len(out) >= cap:
                    break
            return out

    # ------------------------------------------------------------------
    # Actor cues
    # ------------------------------------------------------------------

    def add_actor_cue(
        self,
        clip_id: str = "",
        actor_id: str = "",
        start_time: float = 0.0,
        action_name: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        target_position: Any = (0.0, 0.0, 0.0),
        target_rotation: Any = (0.0, 0.0, 0.0),
        blend_time: float = 0.2,
        cutscene_id: str = "",
        frame: Any = None,
        action: str = "",
    ) -> ActorCue:
        """Add an actor cue to a clip and return it.

        Raises ``ValueError`` when the clip does not exist.
        """
        with self._lock:
            cid = self._resolve_clip(clip_id, cutscene_id)
            clip = self._clips.get(cid)
            if clip is None:
                raise ValueError(f"Unknown clip_id: {cid}")
            pos = self._vec3(target_position)
            rot = self._vec3(target_rotation)
            s_time = self._frame_to_time(frame, start_time)
            act = action_name if action_name else action
            cue = ActorCue(
                clip_id=cid,
                actor_id=str(actor_id),
                start_time=max(0.0, s_time),
                action_name=str(act),
                parameters=dict(parameters) if parameters else {},
                target_position=[pos[0], pos[1], pos[2]],
                target_rotation=[rot[0], rot[1], rot[2]],
                blend_time=max(0.0, float(blend_time) if blend_time else 0.2),
            )
            self._actor_cues[cue.cue_id] = cue
            self._actor_cue_counter += 1
            self._index_append(self._actor_cues_by_clip, cid, cue.cue_id)
            self._evict_oldest_actor_cue()
            self._touch(clip.cutscene_id)
            return cue

    def list_actor_cues(self, clip_id: str, limit: int = 100) -> List[ActorCue]:
        """List actor cues for a clip ordered by start time."""
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            ids = self._actor_cues_by_clip.get(clip_id, [])
            candidates = [self._actor_cues[cid] for cid in ids if cid in self._actor_cues]
            candidates.sort(key=lambda c: (c.start_time, c.cue_id))
            return candidates[:cap]

    # ------------------------------------------------------------------
    # Audio cues
    # ------------------------------------------------------------------

    def add_audio_cue(
        self,
        clip_id: str = "",
        audio_id: str = "",
        start_time: float = 0.0,
        volume: float = 1.0,
        pitch: float = 1.0,
        loop: bool = False,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
        spatial_position: Any = (0.0, 0.0, 0.0),
        cutscene_id: str = "",
        frame: Any = None,
        action: str = "",
    ) -> AudioCue:
        """Add an audio cue to a clip and return it.

        Raises ``ValueError`` when the clip does not exist.
        """
        with self._lock:
            cid = self._resolve_clip(clip_id, cutscene_id)
            clip = self._clips.get(cid)
            if clip is None:
                raise ValueError(f"Unknown clip_id: {cid}")
            pos = self._vec3(spatial_position)
            s_time = self._frame_to_time(frame, start_time)
            cue = AudioCue(
                clip_id=cid,
                audio_id=str(audio_id),
                start_time=max(0.0, s_time),
                volume=max(0.0, float(volume) if volume else 1.0),
                pitch=float(pitch) if pitch else 1.0,
                loop=bool(loop),
                fade_in=max(0.0, float(fade_in) if fade_in else 0.0),
                fade_out=max(0.0, float(fade_out) if fade_out else 0.0),
                spatial_position=[pos[0], pos[1], pos[2]],
            )
            self._audio_cues[cue.cue_id] = cue
            self._audio_cue_counter += 1
            self._index_append(self._audio_cues_by_clip, cid, cue.cue_id)
            self._evict_oldest_audio_cue()
            self._touch(clip.cutscene_id)
            return cue

    def list_audio_cues(self, clip_id: str, limit: int = 100) -> List[AudioCue]:
        """List audio cues for a clip ordered by start time."""
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            ids = self._audio_cues_by_clip.get(clip_id, [])
            candidates = [self._audio_cues[cid] for cid in ids if cid in self._audio_cues]
            candidates.sort(key=lambda c: (c.start_time, c.cue_id))
            return candidates[:cap]

    # ------------------------------------------------------------------
    # Playback transport
    # ------------------------------------------------------------------

    def play(self, cutscene_id: str, from_time: float = 0.0) -> dict:
        """Start or restart playback of a cutscene from ``from_time``.

        Returns ``{"playing": True, "cutscene_id": ..., "position": ...}``.
        Raises ``ValueError`` when the cutscene does not exist.
        """
        with self._lock:
            asset = self._cutscenes.get(cutscene_id)
            if asset is None:
                raise ValueError(f"Unknown cutscene_id: {cutscene_id}")
            position = max(0.0, min(float(from_time), asset.duration))
            now = _now()
            self._playback[cutscene_id] = {
                "state": PlaybackState.PLAYING.value,
                "position": position,
                "started_at": now,
                "updated_at": now,
            }
            self._playback_counter += 1
            self._record_event(
                CutscenePlayerEventKind.PLAYBACK_STARTED,
                cutscene_id=cutscene_id,
                payload={"from_time": position},
            )
            return {
                "playing": True,
                "cutscene_id": cutscene_id,
                "position": position,
            }

    def pause(self, cutscene_id: str) -> dict:
        """Pause a playing cutscene.

        Returns ``{"paused": True, "cutscene_id": ..., "position": ...}``.
        Raises ``ValueError`` when the cutscene does not exist.
        """
        with self._lock:
            asset = self._cutscenes.get(cutscene_id)
            if asset is None:
                raise ValueError(f"Unknown cutscene_id: {cutscene_id}")
            state = self._playback.get(cutscene_id)
            position = state["position"] if state else 0.0
            now = _now()
            self._playback[cutscene_id] = {
                "state": PlaybackState.PAUSED.value,
                "position": position,
                "started_at": state["started_at"] if state else now,
                "updated_at": now,
            }
            self._record_event(
                CutscenePlayerEventKind.PLAYBACK_PAUSED,
                cutscene_id=cutscene_id,
                payload={"position": position},
            )
            return {
                "paused": True,
                "cutscene_id": cutscene_id,
                "position": position,
            }

    def resume(self, cutscene_id: str) -> dict:
        """Resume a paused cutscene.

        Returns ``{"playing": True, "cutscene_id": ..., "position": ...}``.
        Raises ``ValueError`` when the cutscene does not exist.
        """
        with self._lock:
            asset = self._cutscenes.get(cutscene_id)
            if asset is None:
                raise ValueError(f"Unknown cutscene_id: {cutscene_id}")
            state = self._playback.get(cutscene_id)
            position = state["position"] if state else 0.0
            now = _now()
            self._playback[cutscene_id] = {
                "state": PlaybackState.PLAYING.value,
                "position": position,
                "started_at": state["started_at"] if state else now,
                "updated_at": now,
            }
            self._record_event(
                CutscenePlayerEventKind.PLAYBACK_RESUMED,
                cutscene_id=cutscene_id,
                payload={"position": position},
            )
            return {
                "playing": True,
                "cutscene_id": cutscene_id,
                "position": position,
            }

    def stop(self, cutscene_id: str) -> dict:
        """Stop playback of a cutscene and reset its position to zero.

        Returns ``{"stopped": True, "cutscene_id": ..., "position": 0.0}``.
        Raises ``ValueError`` when the cutscene does not exist.
        """
        with self._lock:
            asset = self._cutscenes.get(cutscene_id)
            if asset is None:
                raise ValueError(f"Unknown cutscene_id: {cutscene_id}")
            now = _now()
            self._playback[cutscene_id] = {
                "state": PlaybackState.STOPPED.value,
                "position": 0.0,
                "started_at": now,
                "updated_at": now,
            }
            self._record_event(
                CutscenePlayerEventKind.PLAYBACK_STOPPED,
                cutscene_id=cutscene_id,
                payload={},
            )
            return {
                "stopped": True,
                "cutscene_id": cutscene_id,
                "position": 0.0,
            }

    def seek(self, cutscene_id: str, time_position: float) -> dict:
        """Seek a cutscene to ``time_position`` on the timeline.

        The playback state is set to ``seeking`` then restored to its
        previous transport state (playing or paused). Returns
        ``{"seeked": True, "cutscene_id": ..., "position": ...}``.
        Raises ``ValueError`` when the cutscene does not exist.
        """
        with self._lock:
            asset = self._cutscenes.get(cutscene_id)
            if asset is None:
                raise ValueError(f"Unknown cutscene_id: {cutscene_id}")
            position = max(0.0, min(float(time_position), asset.duration))
            state = self._playback.get(cutscene_id)
            previous_state = state["state"] if state else PlaybackState.STOPPED.value
            # Briefly mark the transport as seeking, then restore the
            # prior playing / paused state so playback continues from
            # the new position.
            now = _now()
            self._playback[cutscene_id] = {
                "state": PlaybackState.SEEKING.value,
                "position": position,
                "started_at": state["started_at"] if state else now,
                "updated_at": now,
            }
            restored = previous_state
            if restored == PlaybackState.STOPPED.value:
                restored = PlaybackState.PAUSED.value
            self._playback[cutscene_id]["state"] = restored
            self._record_event(
                CutscenePlayerEventKind.PLAYBACK_SEEKED,
                cutscene_id=cutscene_id,
                payload={"time_position": position, "restored_state": restored},
            )
            return {
                "seeked": True,
                "cutscene_id": cutscene_id,
                "position": position,
            }

    def get_playback_state(self, cutscene_id: str) -> Optional[dict]:
        """Return the playback state dict for a cutscene, or None.

        The returned dict is a shallow copy of the internal transport
        record so callers cannot mutate the player's state.
        """
        with self._lock:
            state = self._playback.get(cutscene_id)
            if state is None:
                return None
            return dict(state)

    # ------------------------------------------------------------------
    # Checkpoints
    # ------------------------------------------------------------------

    def add_checkpoint(
        self,
        cutscene_id: str,
        time_position: float,
        label: str = "",
        can_skip_to: bool = True,
    ) -> PlaybackCheckpoint:
        """Add a named seek target to a cutscene and return it.

        Raises ``ValueError`` when the cutscene does not exist. A
        ``checkpoint_reached`` event is recorded to mark the new
        skip target.
        """
        with self._lock:
            asset = self._cutscenes.get(cutscene_id)
            if asset is None:
                raise ValueError(f"Unknown cutscene_id: {cutscene_id}")
            position = max(0.0, min(float(time_position), asset.duration))
            checkpoint = PlaybackCheckpoint(
                cutscene_id=cutscene_id,
                time_position=position,
                label=str(label),
                can_skip_to=bool(can_skip_to),
            )
            self._checkpoints[checkpoint.checkpoint_id] = checkpoint
            self._checkpoint_counter += 1
            self._index_append(self._checkpoints_by_cutscene, cutscene_id, checkpoint.checkpoint_id)
            self._evict_oldest_checkpoint()
            self._touch(cutscene_id)
            self._record_event(
                CutscenePlayerEventKind.CHECKPOINT_REACHED,
                cutscene_id=cutscene_id,
                payload={"checkpoint_id": checkpoint.checkpoint_id, "label": label},
            )
            return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Optional[PlaybackCheckpoint]:
        """Return the checkpoint for ``checkpoint_id`` or None."""
        with self._lock:
            return self._checkpoints.get(checkpoint_id)

    def list_checkpoints(self, cutscene_id: str, limit: int = 100) -> List[PlaybackCheckpoint]:
        """List checkpoints for a cutscene ordered by time position."""
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            ids = self._checkpoints_by_cutscene.get(cutscene_id, [])
            candidates = [self._checkpoints[cid] for cid in ids if cid in self._checkpoints]
            candidates.sort(key=lambda c: (c.time_position, c.checkpoint_id))
            return candidates[:cap]

    # ------------------------------------------------------------------
    # Events, stats, status, snapshot
    # ------------------------------------------------------------------

    def list_events(
        self,
        limit: int = 100,
        kind: Optional[Union[CutscenePlayerEventKind, str]] = None,
    ) -> List[CutscenePlayerEvent]:
        """List audit events, optionally filtered by event kind.

        Results are returned newest-first (most recent events first)
        and capped at ``limit``.
        """
        with self._lock:
            cap = max(0, int(limit))
            if cap == 0:
                return []
            wanted = _enum_value(kind, CutscenePlayerEventKind) if kind is not None else None
            # Walk the event log in reverse so the most recent events
            # come first.
            out: List[CutscenePlayerEvent] = []
            for event in reversed(self._events):
                if wanted is not None and event.kind != wanted:
                    continue
                out.append(event)
                if len(out) >= cap:
                    break
            return out

    def get_stats(self) -> CutscenePlayerStats:
        """Compute aggregate statistics from the current player state."""
        with self._lock:
            return CutscenePlayerStats(
                total_cutscenes=self._cutscene_counter,
                loaded_cutscenes=len(self._cutscenes),
                total_tracks=self._track_counter,
                total_clips=self._clip_counter,
                total_subtitles=self._subtitle_counter,
                total_playbacks=self._playback_counter,
                total_checkpoints=self._checkpoint_counter,
                last_updated=_now(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current cutscene player state.

        The ``initialized`` flag is always the first key in the
        returned dictionary, followed by store counts, aggregate
        counters and the computed stats block.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "cutscene_count": len(self._cutscenes),
                "track_count": len(self._tracks),
                "clip_count": len(self._clips),
                "camera_keyframe_count": len(self._camera_keyframes),
                "subtitle_count": len(self._subtitles),
                "actor_cue_count": len(self._actor_cues),
                "audio_cue_count": len(self._audio_cues),
                "checkpoint_count": len(self._checkpoints),
                "event_count": len(self._events),
                "active_playback_count": len(self._playback),
                "cutscene_counter": self._cutscene_counter,
                "track_counter": self._track_counter,
                "clip_counter": self._clip_counter,
                "keyframe_counter": self._keyframe_counter,
                "subtitle_counter": self._subtitle_counter,
                "actor_cue_counter": self._actor_cue_counter,
                "audio_cue_counter": self._audio_cue_counter,
                "checkpoint_counter": self._checkpoint_counter,
                "event_counter": self._event_counter,
                "playback_counter": self._playback_counter,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> CutscenePlayerSnapshot:
        """Capture an immutable snapshot of the entire player state."""
        with self._lock:
            stats = self.get_stats()
            return CutscenePlayerSnapshot(
                cutscenes=list(self._cutscenes.values()),
                tracks=list(self._tracks.values()),
                clips=list(self._clips.values()),
                camera_keyframes=list(self._camera_keyframes.values()),
                subtitles=list(self._subtitles.values()),
                actor_cues=list(self._actor_cues.values()),
                audio_cues=list(self._audio_cues.values()),
                checkpoints=list(self._checkpoints.values()),
                current_playback={k: dict(v) for k, v in self._playback.items()},
                stats=stats,
                timestamp=_now(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the player with default data.

        Restores the player to its initial state, including the seed
        cutscenes, tracks, clips, camera keyframes, subtitles, actor
        cues, audio cues, checkpoints and audit events.
        """
        with self._lock:
            self._cutscenes.clear()
            self._tracks.clear()
            self._clips.clear()
            self._camera_keyframes.clear()
            self._subtitles.clear()
            self._actor_cues.clear()
            self._audio_cues.clear()
            self._checkpoints.clear()
            self._events.clear()
            self._tracks_by_cutscene.clear()
            self._clips_by_cutscene.clear()
            self._clips_by_track.clear()
            self._keyframes_by_clip.clear()
            self._subtitles_by_clip.clear()
            self._subtitles_by_cutscene.clear()
            self._actor_cues_by_clip.clear()
            self._audio_cues_by_clip.clear()
            self._checkpoints_by_cutscene.clear()
            self._playback.clear()
            self._cutscene_counter = 0
            self._track_counter = 0
            self._clip_counter = 0
            self._keyframe_counter = 0
            self._subtitle_counter = 0
            self._actor_cue_counter = 0
            self._audio_cue_counter = 0
            self._checkpoint_counter = 0
            self._event_counter = 0
            self._playback_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_cutscene_player() -> CutscenePlayer:
    """Return the singleton CutscenePlayer instance."""
    return CutscenePlayer.get_instance()
