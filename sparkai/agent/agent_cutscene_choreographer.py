"""
SparkLabs Agent - AI Cutscene Choreographer

An AI cinematic direction and camera choreography agent for the SparkLabs
AI-native game engine. The choreographer designs in-engine cutscenes by
arranging camera shots, marking emotional beats, blocking actor movement,
timing subtitle lines, and managing transitions and pacing across a full
sequence. Directors can draft, approve, reject, and archive cutscenes, and
the agent emits a complete audit trail of every editorial action.

Architecture:
  CutsceneChoreographer (singleton)
    |-- CameraShot, EmotionalBeatMark, ActorBlocking, SubtitleLine,
       CutsceneSequence, CutsceneTemplate, CutsceneStats,
       CutsceneSnapshot, CutsceneEvent
    |-- ShotType, CameraMovement, TransitionType, EmotionalBeat,
       PacingMode, CutsceneStatus, CutsceneEventKind

Core Capabilities:
  - create_cutscene / get_cutscene / list_cutscenes / update_cutscene /
    delete_cutscene: cutscene sequence lifecycle management.
  - add_shot / get_shot / list_shots / update_shot / remove_shot /
    set_transition: camera shot composition with framing, movement,
    field of view, focal length, depth of field, and transitions.
  - mark_beat / get_beat / list_beats: emotional beat markers tied to
    shots for pacing and dramatic emphasis.
  - block_actor / get_blocking / list_blocking: actor staging with
    position, facing, animation, and entry/exit timing.
  - add_subtitle / get_subtitle / list_subtitles: timed subtitle lines
    with speaker, typography, and screen position.
  - adjust_pacing: shift the pacing mode of a cutscene.
  - create_template / get_template / list_templates: reusable cutscene
    templates with default shots, pacing, and transitions.
  - approve_cutscene / reject_cutscene / archive_cutscene: editorial
    review workflow with status transitions.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CutsceneChoreographer.get_instance` or the module-level
:func:`get_cutscene_choreographer` factory.
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

_MAX_CUTSCENES: int = 500
_MAX_SHOTS: int = 5000
_MAX_BEATS: int = 5000
_MAX_BLOCKING: int = 2000
_MAX_SUBTITLES: int = 5000
_MAX_TEMPLATES: int = 200
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default."""
    if value is None or value == "":
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, falling back to default."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, falling back to default."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
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


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ShotType(Enum):
    """Camera framing and shot composition type."""
    ESTABLISHING = "establishing"
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_SHOULDER = "over_shoulder"
    AERIAL = "aerial"
    DOLLY = "dolly"
    TRACKING = "tracking"
    POV = "pov"
    DUTCH_ANGLE = "dutch_angle"
    TWO_SHOT = "two_shot"


class CameraMovement(Enum):
    """Camera motion style during a shot."""
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRACKING = "tracking"
    CRANE = "crane"
    HANDHELD = "handheld"
    STEADICAM = "steadicam"
    ORBIT = "orbit"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


class TransitionType(Enum):
    """Transition style between consecutive shots."""
    CUT = "cut"
    FADE_TO_BLACK = "fade_to_black"
    FADE_TO_WHITE = "fade_to_white"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    IRIS = "iris"
    WHIP_PAN = "whip_pan"
    CROSSFADE = "crossfade"
    MORPH = "morph"


class EmotionalBeat(Enum):
    """Emotional tone marking a dramatic moment in a cutscene."""
    CALM = "calm"
    TENSION_BUILDING = "tension_building"
    REVELATION = "revelation"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    MELANCHOLY = "melancholy"
    TRIUMPH = "triumph"
    FEAR = "fear"
    JOY = "joy"
    ANGER = "anger"
    SADNESS = "sadness"
    SURPRISE = "surprise"


class PacingMode(Enum):
    """Rhythm and speed at which a cutscene unfolds."""
    SLOW = "slow"
    DELIBERATE = "deliberate"
    NORMAL = "normal"
    BRISK = "brisk"
    FRENETIC = "frenetic"


class CutsceneStatus(Enum):
    """Lifecycle status of a cutscene sequence."""
    DRAFT = "draft"
    BLOCKED = "blocked"
    RECORDED = "recorded"
    RENDERED = "rendered"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class CutsceneEventKind(Enum):
    """Audit event kinds emitted by the choreographer."""
    CUTSCENE_CREATED = "cutscene_created"
    CUTSCENE_UPDATED = "cutscene_updated"
    SHOT_ADDED = "shot_added"
    SHOT_REMOVED = "shot_removed"
    TRANSITION_SET = "transition_set"
    BEAT_MARKED = "beat_marked"
    PACING_ADJUSTED = "pacing_adjusted"
    CUTSCENE_APPROVED = "cutscene_approved"
    CUTSCENE_REJECTED = "cutscene_rejected"
    CUTSCENE_ARCHIVED = "cutscene_archived"
    SUBTITLE_ADDED = "subtitle_added"
    ACTOR_BLOCKED = "actor_blocked"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CameraShot:
    """A single camera shot within a cutscene."""
    shot_id: str
    cutscene_id: str
    shot_number: int = 0
    shot_type: ShotType = ShotType.MEDIUM
    camera_movement: CameraMovement = CameraMovement.STATIC
    duration_seconds: float = 3.0
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    look_at_x: float = 0.0
    look_at_y: float = 0.0
    look_at_z: float = 0.0
    fov: float = 60.0
    focal_length: float = 50.0
    depth_of_field: float = 0.0
    transition_in: TransitionType = TransitionType.CUT
    transition_out: TransitionType = TransitionType.CUT
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EmotionalBeatMark:
    """A dramatic beat pinned to a shot at a specific time."""
    beat_id: str
    cutscene_id: str
    shot_id: str
    beat: EmotionalBeat = EmotionalBeat.CALM
    intensity: float = 0.5
    timestamp: float = 0.0
    description: str = ""
    actor_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ActorBlocking:
    """Staging instructions for an actor within a shot."""
    blocking_id: str
    cutscene_id: str
    shot_id: str
    actor_id: str
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    facing_angle: float = 0.0
    animation_name: str = ""
    entry_time: float = 0.0
    exit_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SubtitleLine:
    """A timed subtitle line spoken during a shot."""
    line_id: str
    cutscene_id: str
    shot_id: str
    speaker_id: str
    text: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    font_size: int = 24
    color: str = "#FFFFFF"
    position: str = "bottom"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CutsceneSequence:
    """A complete cutscene sequence composed of shots and beats."""
    cutscene_id: str
    title: str = ""
    description: str = ""
    total_duration: float = 0.0
    status: CutsceneStatus = CutsceneStatus.DRAFT
    pacing: PacingMode = PacingMode.NORMAL
    shot_count: int = 0
    beat_count: int = 0
    actor_count: int = 0
    subtitle_count: int = 0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CutsceneTemplate:
    """A reusable template for spawning new cutscenes."""
    template_id: str
    name: str = ""
    genre: str = ""
    description: str = ""
    default_shots: List[Dict[str, Any]] = field(default_factory=list)
    default_pacing: PacingMode = PacingMode.NORMAL
    default_transitions: List[TransitionType] = field(default_factory=list)
    recommended_duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CutsceneStats:
    """Aggregate statistics across all cutscenes."""
    total_cutscenes: int = 0
    drafts: int = 0
    recorded: int = 0
    rendered: int = 0
    approved: int = 0
    rejected: int = 0
    total_shots: int = 0
    total_beats: int = 0
    total_subtitles: int = 0
    avg_duration: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CutsceneSnapshot:
    """A point-in-time snapshot of choreographer state."""
    cutscenes: List[Dict[str, Any]] = field(default_factory=list)
    shots: List[Dict[str, Any]] = field(default_factory=list)
    beats: List[Dict[str, Any]] = field(default_factory=list)
    blocking: List[Dict[str, Any]] = field(default_factory=list)
    subtitles: List[Dict[str, Any]] = field(default_factory=list)
    templates: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CutsceneEvent:
    """An audit event emitted by the choreographer."""
    event_id: str
    kind: CutsceneEventKind
    cutscene_id: str = ""
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Cutscene Choreographer Singleton
# ---------------------------------------------------------------------------


class CutsceneChoreographer:
    """AI cinematic direction and camera choreography agent."""

    _instance: Optional["CutsceneChoreographer"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "CutsceneChoreographer":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CutsceneChoreographer":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._cutscenes: Dict[str, CutsceneSequence] = {}
            self._shots: Dict[str, CameraShot] = {}
            self._beats: Dict[str, EmotionalBeatMark] = {}
            self._blocking: Dict[str, ActorBlocking] = {}
            self._subtitles: Dict[str, SubtitleLine] = {}
            self._templates: Dict[str, CutsceneTemplate] = {}
            self._events: List[CutsceneEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(self, kind: CutsceneEventKind, cutscene_id: str,
              payload: Dict[str, Any]) -> None:
        event = CutsceneEvent(
            event_id=_new_id("evt"),
            kind=kind,
            cutscene_id=cutscene_id,
            timestamp=_now(),
            payload=payload,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _recount_cutscene(self, cutscene_id: str) -> None:
        """Recompute derived counts and duration for a cutscene."""
        cutscene = self._cutscenes.get(cutscene_id)
        if cutscene is None:
            return
        shots = [s for s in self._shots.values() if s.cutscene_id == cutscene_id]
        beats = [b for b in self._beats.values() if b.cutscene_id == cutscene_id]
        blocking = [b for b in self._blocking.values() if b.cutscene_id == cutscene_id]
        subtitles = [s for s in self._subtitles.values() if s.cutscene_id == cutscene_id]
        cutscene.shot_count = len(shots)
        cutscene.beat_count = len(beats)
        cutscene.actor_count = len(set(b.actor_id for b in blocking if b.actor_id))
        cutscene.subtitle_count = len(subtitles)
        cutscene.total_duration = sum(s.duration_seconds for s in shots)
        cutscene.updated_at = _now()

    # ------------------------------------------------------------------
    # Cutscene Lifecycle
    # ------------------------------------------------------------------

    def create_cutscene(self, title: str, description: str = "",
                        pacing: PacingMode = PacingMode.NORMAL,
                        metadata: Optional[Dict[str, Any]] = None) -> CutsceneSequence:
        with self._lock:
            cutscene = CutsceneSequence(
                cutscene_id=_new_id("cs"),
                title=title,
                description=description,
                pacing=pacing,
                metadata=metadata or {},
            )
            self._cutscenes[cutscene.cutscene_id] = cutscene
            _evict_fifo_dict(self._cutscenes, _MAX_CUTSCENES)
            self._emit(CutsceneEventKind.CUTSCENE_CREATED, cutscene.cutscene_id,
                       {"title": title})
            return cutscene

    def get_cutscene(self, cutscene_id: str) -> Optional[CutsceneSequence]:
        with self._lock:
            return self._cutscenes.get(cutscene_id)

    def list_cutscenes(self, status: Optional[CutsceneStatus] = None,
                       pacing: Optional[PacingMode] = None,
                       limit: int = 100) -> List[CutsceneSequence]:
        with self._lock:
            items = list(self._cutscenes.values())
            if status is not None:
                items = [c for c in items if c.status == status]
            if pacing is not None:
                items = [c for c in items if c.pacing == pacing]
            return items[:limit]

    def update_cutscene(self, cutscene_id: str, **kwargs: Any) -> Optional[CutsceneSequence]:
        with self._lock:
            cutscene = self._cutscenes.get(cutscene_id)
            if cutscene is None:
                return None
            for k, v in kwargs.items():
                if k == "status" and isinstance(v, str):
                    try:
                        v = CutsceneStatus(v)
                    except ValueError:
                        continue
                elif k == "pacing" and isinstance(v, str):
                    try:
                        v = PacingMode(v)
                    except ValueError:
                        continue
                if hasattr(cutscene, k) and k not in ("cutscene_id", "created_at"):
                    setattr(cutscene, k, v)
            cutscene.updated_at = _now()
            self._emit(CutsceneEventKind.CUTSCENE_UPDATED, cutscene_id, {})
            return cutscene

    def delete_cutscene(self, cutscene_id: str) -> bool:
        with self._lock:
            if cutscene_id not in self._cutscenes:
                return False
            # Cascade-remove dependent shots, beats, blocking, and subtitles.
            for shot in [s for s in self._shots.values() if s.cutscene_id == cutscene_id]:
                self._shots.pop(shot.shot_id, None)
            for beat in [b for b in self._beats.values() if b.cutscene_id == cutscene_id]:
                self._beats.pop(beat.beat_id, None)
            for blk in [b for b in self._blocking.values() if b.cutscene_id == cutscene_id]:
                self._blocking.pop(blk.blocking_id, None)
            for sub in [s for s in self._subtitles.values() if s.cutscene_id == cutscene_id]:
                self._subtitles.pop(sub.line_id, None)
            del self._cutscenes[cutscene_id]
            return True

    # ------------------------------------------------------------------
    # Shot Management
    # ------------------------------------------------------------------

    def add_shot(self, cutscene_id: str, shot_type: Any = ShotType.MEDIUM,
                 camera_movement: Any = CameraMovement.STATIC,
                 duration_seconds: Any = 3.0,
                 position: Any = (0.0, 0.0, 0.0),
                 look_at: Any = (0.0, 0.0, 0.0),
                 fov: Any = 60.0,
                 transition_in: Any = TransitionType.CUT,
                 transition_out: Any = TransitionType.CUT,
                 duration_frames: Any = None) -> CameraShot:
        with self._lock:
            st = _safe_enum(ShotType, shot_type, ShotType.MEDIUM)
            cm = _safe_enum(CameraMovement, camera_movement, CameraMovement.STATIC)
            ti = _safe_enum(TransitionType, transition_in, TransitionType.CUT)
            to = _safe_enum(TransitionType, transition_out, TransitionType.CUT)
            if duration_frames is not None:
                dur = _safe_float(duration_frames, 3.0) / 30.0
            else:
                dur = _safe_float(duration_seconds, 3.0)
            pos = position if isinstance(position, (tuple, list)) and len(position) >= 3 else (0.0, 0.0, 0.0)
            la = look_at if isinstance(look_at, (tuple, list)) and len(look_at) >= 3 else (0.0, 0.0, 0.0)
            existing = [s for s in self._shots.values() if s.cutscene_id == cutscene_id]
            shot_number = len(existing) + 1
            shot = CameraShot(
                shot_id=_new_id("sht"),
                cutscene_id=cutscene_id,
                shot_number=shot_number,
                shot_type=st,
                camera_movement=cm,
                duration_seconds=dur,
                position_x=pos[0],
                position_y=pos[1],
                position_z=pos[2],
                look_at_x=la[0],
                look_at_y=la[1],
                look_at_z=la[2],
                fov=_safe_float(fov, 60.0),
                transition_in=ti,
                transition_out=to,
            )
            self._shots[shot.shot_id] = shot
            _evict_fifo_dict(self._shots, _MAX_SHOTS)
            self._recount_cutscene(cutscene_id)
            self._emit(CutsceneEventKind.SHOT_ADDED, cutscene_id,
                       {"shot_id": shot.shot_id, "shot_number": shot_number})
            return shot

    def get_shot(self, shot_id: str) -> Optional[CameraShot]:
        with self._lock:
            return self._shots.get(shot_id)

    def list_shots(self, cutscene_id: str, limit: int = 100) -> List[CameraShot]:
        with self._lock:
            items = [s for s in self._shots.values() if s.cutscene_id == cutscene_id]
            items.sort(key=lambda x: x.shot_number)
            return items[:limit]

    def update_shot(self, shot_id: str, **kwargs: Any) -> Optional[CameraShot]:
        with self._lock:
            shot = self._shots.get(shot_id)
            if shot is None:
                return None
            for k, v in kwargs.items():
                if k == "shot_type" and isinstance(v, str):
                    try:
                        v = ShotType(v)
                    except ValueError:
                        continue
                elif k == "camera_movement" and isinstance(v, str):
                    try:
                        v = CameraMovement(v)
                    except ValueError:
                        continue
                elif k in ("transition_in", "transition_out") and isinstance(v, str):
                    try:
                        v = TransitionType(v)
                    except ValueError:
                        continue
                if hasattr(shot, k) and k not in ("shot_id", "cutscene_id"):
                    setattr(shot, k, v)
            self._recount_cutscene(shot.cutscene_id)
            self._emit(CutsceneEventKind.CUTSCENE_UPDATED, shot.cutscene_id,
                       {"shot_id": shot_id, "action": "updated"})
            return shot

    def remove_shot(self, shot_id: str) -> bool:
        with self._lock:
            shot = self._shots.get(shot_id)
            if shot is None:
                return False
            cutscene_id = shot.cutscene_id
            del self._shots[shot_id]
            self._recount_cutscene(cutscene_id)
            self._emit(CutsceneEventKind.SHOT_REMOVED, cutscene_id, {"shot_id": shot_id})
            return True

    def set_transition(self, shot_id: str, transition_in: Any = "",
                       transition_out: Any = "") -> CameraShot:
        with self._lock:
            shot = self._shots.get(shot_id)
            if shot is None:
                raise KeyError(f"Shot not found: {shot_id}")
            tin = _safe_enum(TransitionType, transition_in, TransitionType.CUT)
            tout = _safe_enum(TransitionType, transition_out, TransitionType.CUT)
            shot.transition_in = tin
            shot.transition_out = tout
            self._emit(CutsceneEventKind.TRANSITION_SET, shot.cutscene_id,
                       {"shot_id": shot_id,
                        "transition_in": tin.value,
                        "transition_out": tout.value})
            return shot

    # ------------------------------------------------------------------
    # Emotional Beats
    # ------------------------------------------------------------------

    def mark_beat(self, cutscene_id: str, shot_id: str = "", beat: Any = None,
                  intensity: Any = 0.5, description: str = "",
                  actor_id: str = "",
                  beat_type: Any = None,
                  frame: Any = None) -> EmotionalBeatMark:
        with self._lock:
            beat_val = beat_type if beat_type is not None else beat
            beat_enum = _safe_enum(EmotionalBeat, beat_val, EmotionalBeat.CALM)
            # Derive the beat timestamp from the shot's start time within the cutscene.
            timestamp = 0.0
            if shot_id:
                target = self._shots.get(shot_id)
                if target is not None and target.cutscene_id == cutscene_id:
                    prior = [s for s in self._shots.values()
                             if s.cutscene_id == cutscene_id and s.shot_number < target.shot_number]
                    timestamp = sum(s.duration_seconds for s in prior)
            elif frame is not None:
                timestamp = _safe_float(frame, 0.0) / 30.0
            mark = EmotionalBeatMark(
                beat_id=_new_id("bt"),
                cutscene_id=cutscene_id,
                shot_id=shot_id,
                beat=beat_enum,
                intensity=_safe_float(intensity, 0.5),
                timestamp=round(timestamp, 3),
                description=description,
                actor_id=actor_id,
            )
            self._beats[mark.beat_id] = mark
            _evict_fifo_dict(self._beats, _MAX_BEATS)
            self._recount_cutscene(cutscene_id)
            self._emit(CutsceneEventKind.BEAT_MARKED, cutscene_id,
                       {"beat_id": mark.beat_id, "shot_id": shot_id, "beat": beat_enum.value})
            return mark

    def get_beat(self, beat_id: str) -> Optional[EmotionalBeatMark]:
        with self._lock:
            return self._beats.get(beat_id)

    def list_beats(self, cutscene_id: str, limit: int = 100) -> List[EmotionalBeatMark]:
        with self._lock:
            items = [b for b in self._beats.values() if b.cutscene_id == cutscene_id]
            items.sort(key=lambda x: x.timestamp)
            return items[:limit]

    # ------------------------------------------------------------------
    # Actor Blocking
    # ------------------------------------------------------------------

    def block_actor(self, cutscene_id: str, shot_id: str = "", actor_id: str = "",
                    position: Any = (0.0, 0.0, 0.0),
                    facing_angle: Any = 0.0, animation_name: str = "",
                    entry_time: Any = 0.0, exit_time: Any = 0.0,
                    frame: Any = None) -> ActorBlocking:
        with self._lock:
            pos = position if isinstance(position, (tuple, list, dict)) and len(position) >= 3 else (0.0, 0.0, 0.0)
            if isinstance(pos, dict):
                pos = (pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0))
            blocking = ActorBlocking(
                blocking_id=_new_id("blk"),
                cutscene_id=cutscene_id,
                shot_id=shot_id,
                actor_id=actor_id,
                position_x=_safe_float(pos[0], 0.0),
                position_y=_safe_float(pos[1], 0.0),
                position_z=_safe_float(pos[2], 0.0),
                facing_angle=_safe_float(facing_angle, 0.0),
                animation_name=animation_name,
                entry_time=_safe_float(entry_time, 0.0),
                exit_time=_safe_float(exit_time, 0.0),
            )
            self._blocking[blocking.blocking_id] = blocking
            _evict_fifo_dict(self._blocking, _MAX_BLOCKING)
            self._recount_cutscene(cutscene_id)
            self._emit(CutsceneEventKind.ACTOR_BLOCKED, cutscene_id,
                       {"blocking_id": blocking.blocking_id, "actor_id": actor_id})
            return blocking

    def get_blocking(self, blocking_id: str) -> Optional[ActorBlocking]:
        with self._lock:
            return self._blocking.get(blocking_id)

    def list_blocking(self, cutscene_id: str, shot_id: Optional[str] = None,
                      limit: int = 100) -> List[ActorBlocking]:
        with self._lock:
            items = [b for b in self._blocking.values() if b.cutscene_id == cutscene_id]
            if shot_id is not None:
                items = [b for b in items if b.shot_id == shot_id]
            return items[:limit]

    # ------------------------------------------------------------------
    # Subtitles
    # ------------------------------------------------------------------

    def add_subtitle(self, cutscene_id: str, shot_id: str, speaker_id: str,
                     text: str, start_time: float = 0.0, end_time: float = 0.0,
                     font_size: int = 24, color: str = "#FFFFFF",
                     position: str = "bottom") -> SubtitleLine:
        with self._lock:
            line = SubtitleLine(
                line_id=_new_id("sub"),
                cutscene_id=cutscene_id,
                shot_id=shot_id,
                speaker_id=speaker_id,
                text=text,
                start_time=start_time,
                end_time=end_time,
                font_size=font_size,
                color=color,
                position=position,
            )
            self._subtitles[line.line_id] = line
            _evict_fifo_dict(self._subtitles, _MAX_SUBTITLES)
            self._recount_cutscene(cutscene_id)
            self._emit(CutsceneEventKind.SUBTITLE_ADDED, cutscene_id,
                       {"line_id": line.line_id, "speaker_id": speaker_id})
            return line

    def get_subtitle(self, line_id: str) -> Optional[SubtitleLine]:
        with self._lock:
            return self._subtitles.get(line_id)

    def list_subtitles(self, cutscene_id: str, limit: int = 100) -> List[SubtitleLine]:
        with self._lock:
            items = [s for s in self._subtitles.values() if s.cutscene_id == cutscene_id]
            items.sort(key=lambda x: x.start_time)
            return items[:limit]

    # ------------------------------------------------------------------
    # Pacing
    # ------------------------------------------------------------------

    def adjust_pacing(self, cutscene_id: str, pacing: Any = None,
                      mode: Any = None) -> CutsceneSequence:
        with self._lock:
            cutscene = self._cutscenes.get(cutscene_id)
            if cutscene is None:
                raise KeyError(f"Cutscene not found: {cutscene_id}")
            pacing_val = mode if mode is not None else pacing
            if isinstance(pacing_val, PacingMode):
                pacing_enum = pacing_val
            elif isinstance(pacing_val, str) and pacing_val:
                pacing_lower = pacing_val.lower()
                alias_map = {"fast": "brisk", "slow": "slow", "normal": "normal",
                             "deliberate": "deliberate", "brisk": "brisk",
                             "frenetic": "frenetic"}
                mapped = alias_map.get(pacing_lower, pacing_lower)
                pacing_enum = _safe_enum(PacingMode, mapped, cutscene.pacing)
            else:
                pacing_enum = cutscene.pacing
            cutscene.pacing = pacing_enum
            cutscene.updated_at = _now()
            self._emit(CutsceneEventKind.PACING_ADJUSTED, cutscene_id,
                       {"pacing": pacing_enum.value})
            return cutscene

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def create_template(self, name: str, genre: str = "", description: str = "",
                        default_shots: Optional[List[Dict[str, Any]]] = None,
                        default_pacing: PacingMode = PacingMode.NORMAL,
                        default_transitions: Optional[List[TransitionType]] = None,
                        recommended_duration: float = 0.0) -> CutsceneTemplate:
        with self._lock:
            template = CutsceneTemplate(
                template_id=_new_id("tpl"),
                name=name,
                genre=genre,
                description=description,
                default_shots=default_shots or [],
                default_pacing=default_pacing,
                default_transitions=default_transitions or [],
                recommended_duration=recommended_duration,
            )
            self._templates[template.template_id] = template
            _evict_fifo_dict(self._templates, _MAX_TEMPLATES)
            return template

    def get_template(self, template_id: str) -> Optional[CutsceneTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(self, genre: Optional[str] = None,
                       limit: int = 100) -> List[CutsceneTemplate]:
        with self._lock:
            items = list(self._templates.values())
            if genre is not None:
                items = [t for t in items if t.genre == genre]
            return items[:limit]

    # ------------------------------------------------------------------
    # Editorial Workflow
    # ------------------------------------------------------------------

    def approve_cutscene(self, cutscene_id: str) -> CutsceneSequence:
        with self._lock:
            cutscene = self._cutscenes.get(cutscene_id)
            if cutscene is None:
                raise KeyError(f"Cutscene not found: {cutscene_id}")
            cutscene.status = CutsceneStatus.APPROVED
            cutscene.updated_at = _now()
            self._emit(CutsceneEventKind.CUTSCENE_APPROVED, cutscene_id, {})
            return cutscene

    def reject_cutscene(self, cutscene_id: str, reason: str = "") -> CutsceneSequence:
        with self._lock:
            cutscene = self._cutscenes.get(cutscene_id)
            if cutscene is None:
                raise KeyError(f"Cutscene not found: {cutscene_id}")
            cutscene.status = CutsceneStatus.REJECTED
            cutscene.updated_at = _now()
            self._emit(CutsceneEventKind.CUTSCENE_REJECTED, cutscene_id,
                       {"reason": reason})
            return cutscene

    def archive_cutscene(self, cutscene_id: str) -> CutsceneSequence:
        with self._lock:
            cutscene = self._cutscenes.get(cutscene_id)
            if cutscene is None:
                raise KeyError(f"Cutscene not found: {cutscene_id}")
            cutscene.status = CutsceneStatus.ARCHIVED
            cutscene.updated_at = _now()
            self._emit(CutsceneEventKind.CUTSCENE_ARCHIVED, cutscene_id, {})
            return cutscene

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100,
                    kind: Optional[CutsceneEventKind] = None) -> List[CutsceneEvent]:
        with self._lock:
            items = list(self._events)
            if kind is not None:
                items = [e for e in items if e.kind == kind]
            return items[:limit]

    def get_stats(self) -> CutsceneStats:
        with self._lock:
            cutscenes = list(self._cutscenes.values())
            total = len(cutscenes)
            drafts = sum(1 for c in cutscenes if c.status == CutsceneStatus.DRAFT)
            recorded = sum(1 for c in cutscenes if c.status == CutsceneStatus.RECORDED)
            rendered = sum(1 for c in cutscenes if c.status == CutsceneStatus.RENDERED)
            approved = sum(1 for c in cutscenes if c.status == CutsceneStatus.APPROVED)
            rejected = sum(1 for c in cutscenes if c.status == CutsceneStatus.REJECTED)
            avg_duration = (sum(c.total_duration for c in cutscenes) / total) if total else 0.0
            return CutsceneStats(
                total_cutscenes=total,
                drafts=drafts,
                recorded=recorded,
                rendered=rendered,
                approved=approved,
                rejected=rejected,
                total_shots=len(self._shots),
                total_beats=len(self._beats),
                total_subtitles=len(self._subtitles),
                avg_duration=round(avg_duration, 3),
                last_updated=_now(),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_cutscenes": len(self._cutscenes),
                "total_shots": len(self._shots),
                "total_beats": len(self._beats),
                "total_blocking": len(self._blocking),
                "total_subtitles": len(self._subtitles),
                "total_templates": len(self._templates),
                "total_events": len(self._events),
                "capacities": {
                    "max_cutscenes": _MAX_CUTSCENES,
                    "max_shots": _MAX_SHOTS,
                    "max_beats": _MAX_BEATS,
                    "max_blocking": _MAX_BLOCKING,
                    "max_subtitles": _MAX_SUBTITLES,
                    "max_templates": _MAX_TEMPLATES,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> CutsceneSnapshot:
        with self._lock:
            return CutsceneSnapshot(
                cutscenes=[c.to_dict() for c in list(self._cutscenes.values())[:50]],
                shots=[s.to_dict() for s in list(self._shots.values())[:100]],
                beats=[b.to_dict() for b in list(self._beats.values())[:100]],
                blocking=[b.to_dict() for b in list(self._blocking.values())[:100]],
                subtitles=[s.to_dict() for s in list(self._subtitles.values())[:100]],
                templates=[t.to_dict() for t in list(self._templates.values())[:50]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._cutscenes.clear()
            self._shots.clear()
            self._beats.clear()
            self._blocking.clear()
            self._subtitles.clear()
            self._templates.clear()
            self._events.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        # --- Cutscene 1 (draft): a slow, atmospheric opening ---
        cs1 = self.create_cutscene(
            title="The Awakening",
            description="Opening sequence where the protagonist discovers dormant powers at dawn.",
            pacing=PacingMode.SLOW,
            metadata={"act": 1, "location": "cliffside_ruins", "composer_track": "dawn_theme"},
        )

        # Shot 1: establishing the landscape
        s1 = self.add_shot(
            cs1.cutscene_id, shot_type=ShotType.ESTABLISHING,
            camera_movement=CameraMovement.STATIC, duration_seconds=6.0,
            position=(0.0, 5.0, -20.0), look_at=(0.0, 2.0, 0.0), fov=70.0,
            transition_in=TransitionType.CUT, transition_out=TransitionType.DISSOLVE,
        )
        # Shot 2: intimate close-up as power stirs
        s2 = self.add_shot(
            cs1.cutscene_id, shot_type=ShotType.CLOSE_UP,
            camera_movement=CameraMovement.DOLLY_IN, duration_seconds=4.5,
            position=(2.0, 1.5, -3.0), look_at=(0.0, 1.6, 0.0), fov=35.0,
            transition_in=TransitionType.DISSOLVE, transition_out=TransitionType.CUT,
        )
        # Shot 3: medium pull as the protagonist steadies
        s3 = self.add_shot(
            cs1.cutscene_id, shot_type=ShotType.MEDIUM,
            camera_movement=CameraMovement.PAN, duration_seconds=5.0,
            position=(-3.0, 1.2, -4.0), look_at=(0.0, 1.5, 0.0), fov=50.0,
            transition_in=TransitionType.CUT, transition_out=TransitionType.FADE_TO_BLACK,
        )

        # Emotional beats for cutscene 1
        self.mark_beat(
            cs1.cutscene_id, s1.shot_id, beat=EmotionalBeat.CALM,
            intensity=0.3, description="The protagonist gazes at the horizon, unaware of what stirs within.",
            actor_id="aria",
        )
        self.mark_beat(
            cs1.cutscene_id, s2.shot_id, beat=EmotionalBeat.REVELATION,
            intensity=0.8, description="The first surge of power surfaces, cracking the stillness.",
            actor_id="aria",
        )

        # Actor blocking for cutscene 1
        self.block_actor(
            cs1.cutscene_id, s1.shot_id, actor_id="aria",
            position=(0.0, 0.0, 0.0), facing_angle=90.0,
            animation_name="idle_to_awaken", entry_time=0.0, exit_time=10.5,
        )

        # Subtitles for cutscene 1
        self.add_subtitle(
            cs1.cutscene_id, s1.shot_id, speaker_id="narrator",
            text="The world held its breath, waiting for a sign.",
            start_time=0.5, end_time=4.0, font_size=22, color="#D8D8D8", position="bottom",
        )
        self.add_subtitle(
            cs1.cutscene_id, s2.shot_id, speaker_id="aria",
            text="What... is happening to me?",
            start_time=7.0, end_time=10.0, font_size=26, color="#FFFFFF", position="bottom",
        )

        # --- Cutscene 2 (approved): a brisk confrontation ---
        cs2 = self.create_cutscene(
            title="Confrontation at Dawn",
            description="The hero and antagonist face off as the sun crests the ramparts.",
            pacing=PacingMode.BRISK,
            metadata={"act": 2, "location": "castle_ramparts", "composer_track": "duel_theme"},
        )

        # Shot 4: wide duel framing
        s4 = self.add_shot(
            cs2.cutscene_id, shot_type=ShotType.WIDE,
            camera_movement=CameraMovement.STATIC, duration_seconds=5.0,
            position=(0.0, 8.0, -25.0), look_at=(0.0, 1.0, 0.0), fov=75.0,
            transition_in=TransitionType.FADE_TO_BLACK, transition_out=TransitionType.CUT,
        )
        # Shot 5: over-shoulder intensity
        s5 = self.add_shot(
            cs2.cutscene_id, shot_type=ShotType.OVER_SHOULDER,
            camera_movement=CameraMovement.HANDHELD, duration_seconds=4.0,
            position=(1.5, 1.7, -2.5), look_at=(-1.0, 1.6, 0.0), fov=45.0,
            transition_in=TransitionType.CUT, transition_out=TransitionType.DISSOLVE,
        )

        # Emotional beat for cutscene 2
        self.mark_beat(
            cs2.cutscene_id, s4.shot_id, beat=EmotionalBeat.CLIMAX,
            intensity=1.0, description="Blades cross at first light, sealing both fates.",
            actor_id="aria",
        )

        # Actor blocking for cutscene 2
        self.block_actor(
            cs2.cutscene_id, s4.shot_id, actor_id="malachar",
            position=(-2.0, 0.0, 0.0), facing_angle=270.0,
            animation_name="combat_stance", entry_time=0.0, exit_time=9.0,
        )

        # Subtitles for cutscene 2
        self.add_subtitle(
            cs2.cutscene_id, s4.shot_id, speaker_id="aria",
            text="This ends here, Malachar.",
            start_time=0.5, end_time=2.5, font_size=26, color="#FFFFFF", position="bottom",
        )
        self.add_subtitle(
            cs2.cutscene_id, s5.shot_id, speaker_id="malachar",
            text="You underestimate the dark.",
            start_time=3.0, end_time=5.5, font_size=26, color="#FF4444", position="bottom",
        )

        # Mark the second cutscene as approved
        cs2.status = CutsceneStatus.APPROVED
        cs2.updated_at = _now()

        # --- Template: a balanced dramatic framework ---
        self.create_template(
            name="Cinematic Drama Template",
            genre="drama",
            description="A balanced dramatic framework pairing establishing shots with emotional beats.",
            default_shots=[
                {"shot_type": "establishing", "duration": 5.0},
                {"shot_type": "medium", "duration": 4.0},
                {"shot_type": "close_up", "duration": 3.5},
            ],
            default_pacing=PacingMode.DELIBERATE,
            default_transitions=[TransitionType.CUT, TransitionType.DISSOLVE],
            recommended_duration=30.0,
        )


def get_cutscene_choreographer() -> CutsceneChoreographer:
    """Factory function to get the singleton CutsceneChoreographer instance."""
    return CutsceneChoreographer.get_instance()
