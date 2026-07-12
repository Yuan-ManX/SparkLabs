"""
SparkLabs Agent - AI Trailer Director

AI-native game trailer direction engine for the SparkLabs game platform. The
director ingests gameplay footage clips, selects highlight moments, synchronizes
them with music, applies cinematic transitions and effects, paces the narrative
arc of the trailer, and manages render jobs from draft to publication. It models
the full creative pipeline that a human trailer director would follow, driven by
quality scoring, genre-aware clip affinity, beat-aligned music synchronization,
and narrative beat placement.

Architecture:
  AITrailerDirector (singleton)
    |-- GameplayClip, TrailerProject, TransitionEffect, MusicSelection,
        NarrativeArc, RenderJob, TrailerDirectorConfig, TrailerDirectorStats,
        TrailerDirectorSnapshot, TrailerDirectorEvent
    |-- TrailerGenre, ClipCategory, TransitionType, PacingMode, MusicSyncMode,
        TrailerStatus, NarrativeBeat

Core Capabilities:
  - register_clip / get_clip / list_clips / remove_clip: ingest and manage
    discrete gameplay footage clips from any recorded session.
  - create_project / get_project / list_projects / update_project /
    remove_project: maintain trailer projects that aggregate clips,
    transitions, music, pacing, and narrative beats into a single creative
    work product.
  - add_clip_to_project / remove_clip_from_project / reorder_clips: assemble
    the ordered clip sequence that forms the trailer timeline.
  - select_highlights: AI-driven clip selection from a pool that maximizes
    quality, respects target duration, and preserves category diversity.
  - add_transition / get_transition / list_transitions / remove_transition:
    manage cinematic transitions between adjacent clips.
  - set_music / get_music / list_music / remove_music: maintain the music
    library and bind a track to a project.
  - create_narrative_arc / get_narrative_arc / list_narrative_arcs /
    remove_narrative_arc: define the emotional and pacing shape of a trailer.
  - set_pacing / auto_pace: assign or auto-derive pacing modes across the
    trailer timeline.
  - sync_music: align clip boundaries to music beats for a polished cut.
  - start_render / get_render_job / list_render_jobs / cancel_render: manage
    asynchronous render jobs that turn a project into a distributable video.
  - publish_trailer: promote a completed render to a published trailer.
  - list_events / get_status / get_stats / get_snapshot / get_config /
    set_config / tick / reset: observability, tuning, and lifecycle control.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TRAILERS: int = 2000
_MAX_CLIPS: int = 20000
_MAX_TRANSITIONS: int = 10000
_MAX_MUSIC: int = 2000
_MAX_NARRATIVE_ARCS: int = 2000
_MAX_RENDER_JOBS: int = 1000
_MAX_EVENTS: int = 10000

# Quality and progress bounds
_QUALITY_MIN: float = 0.0
_QUALITY_MAX: float = 1.0
_PROGRESS_MIN: float = 0.0
_PROGRESS_MAX: float = 1.0

# Highlight-selection tuning
_HIGHLIGHT_DURATION_TOLERANCE: float = 1.15
_HIGHLIGHT_DIVERSITY_PENALTY: float = 0.12
_HIGHLIGHT_MIN_QUALITY: float = 0.3

# Render simulation tuning (progress per second of simulated time)
_RENDER_PROGRESS_PER_SECOND: float = 0.04
_RENDER_PROGRESS_MAX_STEP: float = 0.25

# Genre-to-category affinity used by the AI highlight selector. Higher values
# mean a clip of that category is a stronger fit for a trailer of that genre.
_GENRE_CATEGORY_AFFINITY: Dict[str, Dict[str, float]] = {
    "cinematic": {
        "cutscene": 0.9, "emotional_moment": 0.85, "intro": 0.7,
        "outro": 0.65, "boss_fight": 0.55, "gameplay_highlight": 0.5,
        "achievement": 0.35, "explosion": 0.45, "funny_moment": 0.2,
        "custom": 0.3,
    },
    "gameplay": {
        "gameplay_highlight": 0.95, "boss_fight": 0.9, "explosion": 0.85,
        "achievement": 0.7, "funny_moment": 0.6, "emotional_moment": 0.4,
        "cutscene": 0.3, "intro": 0.35, "outro": 0.35, "custom": 0.4,
    },
    "story": {
        "cutscene": 0.95, "emotional_moment": 0.9, "intro": 0.75,
        "outro": 0.7, "boss_fight": 0.45, "gameplay_highlight": 0.4,
        "achievement": 0.3, "explosion": 0.35, "funny_moment": 0.25,
        "custom": 0.35,
    },
    "hype": {
        "boss_fight": 0.95, "explosion": 0.95, "gameplay_highlight": 0.85,
        "achievement": 0.8, "funny_moment": 0.55, "emotional_moment": 0.5,
        "cutscene": 0.4, "intro": 0.6, "outro": 0.6, "custom": 0.5,
    },
    "documentary": {
        "gameplay_highlight": 0.8, "cutscene": 0.7, "emotional_moment": 0.65,
        "achievement": 0.6, "boss_fight": 0.55, "intro": 0.6,
        "outro": 0.6, "explosion": 0.4, "funny_moment": 0.45,
        "custom": 0.5,
    },
    "teaser": {
        "cutscene": 0.8, "intro": 0.85, "boss_fight": 0.7,
        "explosion": 0.65, "gameplay_highlight": 0.6, "emotional_moment": 0.55,
        "achievement": 0.35, "outro": 0.4, "funny_moment": 0.3,
        "custom": 0.4,
    },
    "announcement": {
        "intro": 0.9, "cutscene": 0.8, "gameplay_highlight": 0.75,
        "boss_fight": 0.65, "achievement": 0.6, "emotional_moment": 0.5,
        "explosion": 0.55, "outro": 0.7, "funny_moment": 0.4,
        "custom": 0.45,
    },
    "update": {
        "gameplay_highlight": 0.85, "achievement": 0.8, "cutscene": 0.6,
        "boss_fight": 0.55, "emotional_moment": 0.45, "intro": 0.5,
        "outro": 0.5, "explosion": 0.4, "funny_moment": 0.5,
        "custom": 0.45,
    },
}

# Narrative-beat-to-pacing mapping used by the AI auto-pacer.
_BEAT_PACING_MAP: Dict[str, str] = {
    "hook": "fast_cut",
    "setup": "slow_build",
    "escalation": "steady",
    "twist": "fast_cut",
    "climax": "crescendo",
    "resolution": "steady",
    "call_to_action": "finale",
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


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


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        cleaned = ts.rstrip("Z")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class TrailerGenre(str, Enum):
    """Creative genre of a trailer, driving clip selection and pacing."""
    CINEMATIC = "cinematic"
    GAMEPLAY = "gameplay"
    STORY = "story"
    HYPE = "hype"
    DOCUMENTARY = "documentary"
    TEASER = "teaser"
    ANNOUNCEMENT = "announcement"
    UPDATE = "update"


class ClipCategory(str, Enum):
    """Classification of a gameplay clip for selection and pacing logic."""
    GAMEPLAY_HIGHLIGHT = "gameplay_highlight"
    BOSS_FIGHT = "boss_fight"
    EXPLOSION = "explosion"
    EMOTIONAL_MOMENT = "emotional_moment"
    FUNNY_MOMENT = "funny_moment"
    ACHIEVEMENT = "achievement"
    CUTSCENE = "cutscene"
    INTRO = "intro"
    OUTRO = "outro"
    CUSTOM = "custom"


class TransitionType(str, Enum):
    """Visual transition applied between two adjacent clips."""
    CUT = "cut"
    CROSSFADE = "crossfade"
    WIPE = "wipe"
    SLIDE = "slide"
    ZOOM = "zoom"
    GLITCH = "glitch"
    WHIP_PAN = "whip_pan"
    DISSOLVE = "dissolve"
    IRIS = "iris"


class PacingMode(str, Enum):
    """Pacing strategy applied to a segment of the trailer timeline."""
    SLOW_BUILD = "slow_build"
    STEADY = "steady"
    FAST_CUT = "fast_cut"
    MONTAGE = "montage"
    CRESCENDO = "crescendo"
    FINALE = "finale"


class MusicSyncMode(str, Enum):
    """Strategy for aligning clip boundaries to music structure."""
    NONE = "none"
    BEAT_MATCH = "beat_match"
    PHRASE_ALIGN = "phrase_align"
    EMOTIONAL_CUE = "emotional_cue"
    DYNAMIC = "dynamic"


class TrailerStatus(str, Enum):
    """Lifecycle state of a trailer project."""
    DRAFT = "draft"
    ANALYZING = "analyzing"
    SELECTING = "selecting"
    EDITING = "editing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    PUBLISHED = "published"


class NarrativeBeat(str, Enum):
    """Structural beat in the narrative arc of a trailer."""
    HOOK = "hook"
    SETUP = "setup"
    ESCALATION = "escalation"
    TWIST = "twist"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    CALL_TO_ACTION = "call_to_action"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class GameplayClip:
    """A single recorded gameplay clip available for trailer assembly.

    Captures the source session, timestamp, duration, category, a 0..1
    quality score, a human-readable description, tags, and free-form
    metadata. Clips are the atomic unit fed into highlight selection and
    project assembly.
    """
    clip_id: str
    source_session: str
    timestamp: str
    duration: float = 0.0
    category: ClipCategory = ClipCategory.GAMEPLAY_HIGHLIGHT
    quality_score: float = 0.0
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TrailerProject:
    """A trailer project that aggregates clips, transitions, music, pacing,
    and narrative beats into a single creative work product.

    The clips list is ordered to represent the timeline sequence. Each
    project tracks its lifecycle status, target duration, and timestamps
    for creation and last update.
    """
    project_id: str
    title: str
    genre: TrailerGenre
    target_duration: float = 60.0
    status: TrailerStatus = TrailerStatus.DRAFT
    clips: List[str] = field(default_factory=list)
    transitions: List[str] = field(default_factory=list)
    music_track: str = ""
    pacing: PacingMode = PacingMode.STEADY
    narrative_beats: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TransitionEffect:
    """A cinematic transition between two adjacent clips.

    Stores the transition type, duration in seconds, the source and target
    clip IDs, and a parameters dict for type-specific tuning such as fade
    curve, wipe direction, or zoom factor.
    """
    transition_id: str
    type: TransitionType = TransitionType.CUT
    duration: float = 0.5
    source_clip: str = ""
    target_clip: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicSelection:
    """A music track from the library available for trailer scoring.

    Captures the track name, mood, BPM, duration, the sync mode that
    determines how clips align to the track, and a list of cue points
    (timestamps in seconds) marking beats, phrases, or emotional shifts.
    """
    music_id: str
    track_name: str
    mood: str = ""
    bpm: float = 120.0
    duration: float = 0.0
    sync_mode: MusicSyncMode = MusicSyncMode.BEAT_MATCH
    cue_points: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NarrativeArc:
    """The narrative shape of a trailer defined by beats and curves.

    The beats list holds ordered NarrativeBeat values. The pacing_curve and
    emotional_curve are parallel lists of 0..1 floats describing intensity
    over normalized timeline position. climax_position is the 0..1 position
    of the narrative climax.
    """
    arc_id: str
    beats: List[str] = field(default_factory=list)
    pacing_curve: List[float] = field(default_factory=list)
    emotional_curve: List[float] = field(default_factory=list)
    climax_position: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RenderJob:
    """An asynchronous render job that turns a project into a video file.

    Tracks the resolution, frame rate, container format, quality preset,
    lifecycle status, 0..1 progress, and the output path of the rendered
    video once complete.
    """
    job_id: str
    project_id: str
    resolution: str = "1920x1080"
    fps: int = 30
    format: str = "mp4"
    quality_preset: str = "high"
    status: TrailerStatus = TrailerStatus.RENDERING
    progress: float = 0.0
    output_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TrailerDirectorConfig:
    """Tunable configuration for the AI trailer director."""
    max_projects: int = 2000
    max_clips_per_project: int = 50
    default_target_duration: float = 60.0
    default_resolution: str = "1920x1080"
    default_fps: int = 30
    auto_select_clips: bool = True
    auto_sync_music: bool = True
    auto_pace_narrative: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TrailerDirectorStats:
    """Roll-up statistics maintained across the director's lifetime."""
    total_projects: int = 0
    total_clips: int = 0
    total_renders: int = 0
    total_published: int = 0
    active_projects: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TrailerDirectorSnapshot:
    """A point-in-time snapshot of the director's full state."""
    timestamp: str
    projects: List[Dict[str, Any]] = field(default_factory=list)
    clips: List[Dict[str, Any]] = field(default_factory=list)
    render_jobs: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TrailerDirectorEvent:
    """An internal audit event emitted by the director."""
    event_id: str
    timestamp: str
    event_type: str
    project_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main System - AI Trailer Director (Singleton)
# ---------------------------------------------------------------------------

class AITrailerDirector:
    """AI-native game trailer direction engine.

    The director maintains a pool of gameplay clips, trailer projects,
    transitions, music selections, narrative arcs, and render jobs. It is
    thread-safe and implemented as a singleton with double-checked locking.
    The _init_lock guards singleton instance creation; _lock guards seed
    initialization and all mutating operations to keep internal dictionaries
    consistent.

    The AI capabilities center on three original algorithms:
      - select_highlights: greedy quality-maximizing clip selection with
        genre-aware category affinity and diversity penalties.
      - auto_pace: narrative-beat-driven pacing assignment that maps each
        beat to a pacing mode and derives a composite project pacing.
      - sync_music: beat-aligned clip boundary snapping computed from the
        music BPM and cue points.
    """

    _instance: Optional["AITrailerDirector"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        # Initialize empty containers so the instance is usable before seeding.
        self._clips: Dict[str, GameplayClip] = {}
        self._projects: Dict[str, TrailerProject] = {}
        self._transitions: Dict[str, TransitionEffect] = {}
        self._music: Dict[str, MusicSelection] = {}
        self._narrative_arcs: Dict[str, NarrativeArc] = {}
        self._render_jobs: Dict[str, RenderJob] = {}
        self._events: List[TrailerDirectorEvent] = []
        self._config = TrailerDirectorConfig()
        self._stats = TrailerDirectorStats()
        self._tick_count: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "AITrailerDirector":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        # Populate the director with a canonical set of trailer data.
        # self._initialized = True is set at the very end.
        self._seed_data()
        self._initialized = True

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._seed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        project_id: str = "",
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = TrailerDirectorEvent(
            event_id=_new_id("evt"),
            timestamp=_now(),
            event_type=event_type,
            project_id=project_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_projects = len(self._projects)
        self._stats.total_clips = len(self._clips)
        self._stats.total_renders = len(self._render_jobs)
        self._stats.total_published = sum(
            1 for p in self._projects.values()
            if p.status == TrailerStatus.PUBLISHED
        )
        self._stats.active_projects = sum(
            1 for p in self._projects.values()
            if p.status not in (TrailerStatus.COMPLETED, TrailerStatus.PUBLISHED,
                                TrailerStatus.FAILED)
        )
        self._stats.tick_count = self._tick_count

    def _project_clips(self, project_id: str) -> List[GameplayClip]:
        project = self._projects.get(project_id)
        if project is None:
            return []
        out: List[GameplayClip] = []
        for cid in project.clips:
            clip = self._clips.get(cid)
            if clip is not None:
                out.append(clip)
        return out

    def _project_total_duration(self, project_id: str) -> float:
        return sum(c.duration for c in self._project_clips(project_id))

    @staticmethod
    def _genre_affinity(genre: TrailerGenre, category: ClipCategory) -> float:
        table = _GENRE_CATEGORY_AFFINITY.get(genre.value, {})
        return table.get(category.value, 0.3)

    @staticmethod
    def _beat_to_pacing(beat: NarrativeBeat) -> PacingMode:
        pacing_str = _BEAT_PACING_MAP.get(beat.value, "steady")
        return _coerce_enum(PacingMode, pacing_str, PacingMode.STEADY)

    def _beat_interval(self, music: MusicSelection) -> float:
        bpm = _safe_float(music.bpm, 120.0)
        if bpm <= 0:
            return 0.5
        return 60.0 / bpm

    def _touch(self, project: TrailerProject) -> None:
        project.updated_at = _now()

    # ------------------------------------------------------------------
    # Clip Lifecycle
    # ------------------------------------------------------------------

    def register_clip(
        self,
        clip_id: str,
        source_session: str,
        category: Any,
        duration: float = 0.0,
        quality_score: float = 0.0,
        description: str = "",
        tags: Optional[List[str]] = None,
        timestamp: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[GameplayClip]]:
        """Register a gameplay clip in the global clip pool."""
        if not clip_id or not source_session:
            return False, "clip_id and source_session are required", None

        cat = _coerce_enum(ClipCategory, category)
        if cat is None:
            return False, f"invalid category: {category}", None

        with self._lock:
            if clip_id in self._clips:
                return False, f"clip_id already exists: {clip_id}", None

            clip = GameplayClip(
                clip_id=clip_id,
                source_session=source_session,
                timestamp=timestamp or _now(),
                duration=max(0.0, _safe_float(duration, 0.0)),
                category=cat,
                quality_score=_clamp(_safe_float(quality_score, 0.0),
                                     _QUALITY_MIN, _QUALITY_MAX),
                description=description,
                tags=list(tags) if tags else [],
                metadata=metadata or {},
            )
            self._clips[clip_id] = clip
            _evict_fifo_dict(self._clips, _MAX_CLIPS)
            self._emit(
                "clip_registered",
                description=f"Clip {clip_id} registered from {source_session}",
                data={"clip_id": clip_id, "category": cat.value,
                      "duration": clip.duration, "quality": clip.quality_score},
            )
            return True, "success", clip

    def get_clip(self, clip_id: str) -> Optional[GameplayClip]:
        return self._clips.get(clip_id)

    def list_clips(
        self,
        category_filter: str = "",
        limit: int = 100,
    ) -> List[GameplayClip]:
        cat_enum = _coerce_enum(ClipCategory, category_filter) if category_filter else None
        cap = max(1, _safe_int(limit, 100))
        result: List[GameplayClip] = []
        for c in self._clips.values():
            if cat_enum is not None and c.category != cat_enum:
                continue
            result.append(c)
        # Return highest-quality-first for a readable highlight pool.
        result.sort(key=lambda x: x.quality_score, reverse=True)
        return result[:cap]

    def remove_clip(self, clip_id: str) -> Tuple[bool, str]:
        with self._lock:
            clip = self._clips.pop(clip_id, None)
            if clip is None:
                return False, "not found"
            # Detach the clip from any project that uses it.
            for project in self._projects.values():
                if clip_id in project.clips:
                    project.clips = [c for c in project.clips if c != clip_id]
                    self._touch(project)
            self._emit(
                "clip_removed",
                description=f"Clip {clip_id} removed",
                data={"clip_id": clip_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Project Lifecycle
    # ------------------------------------------------------------------

    def create_project(
        self,
        project_id: str,
        title: str,
        genre: Any,
        target_duration: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[TrailerProject]]:
        """Create a new trailer project."""
        if not project_id or not title:
            return False, "project_id and title are required", None

        g = _coerce_enum(TrailerGenre, genre)
        if g is None:
            return False, f"invalid genre: {genre}", None

        with self._lock:
            if project_id in self._projects:
                return False, f"project_id already exists: {project_id}", None

            duration = _safe_float(target_duration, 0.0)
            if duration <= 0:
                duration = self._config.default_target_duration

            now = _now()
            project = TrailerProject(
                project_id=project_id,
                title=title,
                genre=g,
                target_duration=duration,
                status=TrailerStatus.DRAFT,
                clips=[],
                transitions=[],
                music_track="",
                pacing=PacingMode.STEADY,
                narrative_beats=[],
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._projects[project_id] = project
            _evict_fifo_dict(self._projects, self._config.max_projects)
            self._emit(
                "project_created",
                project_id=project_id,
                description=f"Project {project_id} ({title}) created",
                data={"genre": g.value, "target_duration": duration},
            )
            return True, "success", project

    def get_project(self, project_id: str) -> Optional[TrailerProject]:
        return self._projects.get(project_id)

    def list_projects(
        self,
        genre_filter: str = "",
        status_filter: str = "",
        limit: int = 100,
    ) -> List[TrailerProject]:
        genre_enum = _coerce_enum(TrailerGenre, genre_filter) if genre_filter else None
        status_enum = _coerce_enum(TrailerStatus, status_filter) if status_filter else None
        cap = max(1, _safe_int(limit, 100))
        result: List[TrailerProject] = []
        for p in self._projects.values():
            if genre_enum is not None and p.genre != genre_enum:
                continue
            if status_enum is not None and p.status != status_enum:
                continue
            result.append(p)
        result.sort(key=lambda x: x.updated_at, reverse=True)
        return result[:cap]

    def update_project(
        self,
        project_id: str,
        title: str = "",
        genre: Any = None,
        target_duration: float = 0.0,
        status: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[TrailerProject]]:
        """Update mutable fields of a trailer project."""
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", None

            changed: List[str] = []
            if title:
                project.title = title
                changed.append("title")
            if genre is not None:
                g = _coerce_enum(TrailerGenre, genre)
                if g is None:
                    return False, f"invalid genre: {genre}", None
                project.genre = g
                changed.append("genre")
            td = _safe_float(target_duration, 0.0)
            if td > 0:
                project.target_duration = td
                changed.append("target_duration")
            if status is not None:
                st = _coerce_enum(TrailerStatus, status)
                if st is None:
                    return False, f"invalid status: {status}", None
                project.status = st
                changed.append("status")
            if metadata:
                project.metadata.update(metadata)
                changed.append("metadata")

            self._touch(project)
            self._emit(
                "project_updated",
                project_id=project_id,
                description=f"Project {project_id} updated: {', '.join(changed)}",
                data={"fields": changed},
            )
            return True, "updated", project

    def remove_project(self, project_id: str) -> Tuple[bool, str]:
        with self._lock:
            removed = self._projects.pop(project_id, None)
            if removed is None:
                return False, "not found"
            # Cascade-remove render jobs owned by this project.
            orphan_jobs = [
                jid for jid, job in self._render_jobs.items()
                if job.project_id == project_id
            ]
            for jid in orphan_jobs:
                self._render_jobs.pop(jid, None)
            self._emit(
                "project_removed",
                project_id=project_id,
                description=f"Project {project_id} removed",
                data={"orphan_render_jobs": orphan_jobs},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Project Clip Assembly
    # ------------------------------------------------------------------

    def add_clip_to_project(
        self,
        project_id: str,
        clip_id: str,
        position: int = -1,
    ) -> Tuple[bool, str, Optional[TrailerProject]]:
        """Append (or insert at position) a clip into a project's timeline."""
        if not project_id or not clip_id:
            return False, "project_id and clip_id are required", None

        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", None
            if clip_id not in self._clips:
                return False, "clip not found in global pool", None
            if clip_id in project.clips:
                return False, "clip already in project", None
            if len(project.clips) >= self._config.max_clips_per_project:
                return False, "max_clips_per_project reached", None

            if position < 0 or position >= len(project.clips):
                project.clips.append(clip_id)
            else:
                project.clips.insert(position, clip_id)
            self._touch(project)
            self._emit(
                "clip_added_to_project",
                project_id=project_id,
                description=f"Clip {clip_id} added to project {project_id}",
                data={"clip_id": clip_id, "position": position},
            )
            return True, "success", project

    def remove_clip_from_project(
        self,
        project_id: str,
        clip_id: str,
    ) -> Tuple[bool, str, Optional[TrailerProject]]:
        """Remove a clip from a project's timeline."""
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", None
            if clip_id not in project.clips:
                return False, "clip not in project", None
            project.clips = [c for c in project.clips if c != clip_id]
            # Also drop transitions that pointed to the removed clip.
            keep_transitions: List[str] = []
            for tid in project.transitions:
                t = self._transitions.get(tid)
                if t is not None and (t.source_clip == clip_id or t.target_clip == clip_id):
                    self._transitions.pop(tid, None)
                    continue
                keep_transitions.append(tid)
            project.transitions = keep_transitions
            self._touch(project)
            self._emit(
                "clip_removed_from_project",
                project_id=project_id,
                description=f"Clip {clip_id} removed from project {project_id}",
                data={"clip_id": clip_id},
            )
            return True, "success", project

    def reorder_clips(
        self,
        project_id: str,
        new_order: List[str],
    ) -> Tuple[bool, str, Optional[TrailerProject]]:
        """Reorder the clips in a project to match the supplied sequence."""
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", None
            if sorted(new_order) != sorted(project.clips):
                return False, "new_order must contain exactly the current clips", None
            project.clips = list(new_order)
            self._touch(project)
            self._emit(
                "clips_reordered",
                project_id=project_id,
                description=f"Clips reordered in project {project_id}",
                data={"clip_count": len(project.clips)},
            )
            return True, "success", project

    # ------------------------------------------------------------------
    # AI Highlight Selection
    # ------------------------------------------------------------------

    def select_highlights(
        self,
        pool_clip_ids: List[str],
        target_duration: float = 60.0,
        max_clips: int = 20,
        genre: Any = None,
    ) -> Tuple[bool, str, List[str]]:
        """Select a highlight reel from a pool of clips.

        The AI selector scores each clip by blending its base quality score
        with a genre-aware category affinity bonus. It then greedily picks
        clips in descending score order while respecting the target duration
        (with a tolerance margin) and applying a diversity penalty so that
        no single category dominates the selection.
        """
        if not pool_clip_ids:
            return False, "pool_clip_ids is empty", []

        g = _coerce_enum(TrailerGenre, genre, TrailerGenre.GAMEPLAY)
        target = max(1.0, _safe_float(target_duration, 60.0))
        cap = max(1, _safe_int(max_clips, 20))

        # Build scored candidates from the pool.
        candidates: List[Tuple[float, GameplayClip]] = []
        for cid in pool_clip_ids:
            clip = self._clips.get(cid)
            if clip is None:
                continue
            if clip.quality_score < _HIGHLIGHT_MIN_QUALITY:
                continue
            affinity = self._genre_affinity(g, clip.category)
            composite = 0.6 * clip.quality_score + 0.4 * affinity
            candidates.append((composite, clip))

        if not candidates:
            return False, "no clips in the pool met the quality threshold", []

        # Sort by composite score descending.
        candidates.sort(key=lambda pair: pair[0], reverse=True)

        selected: List[str] = []
        total_duration = 0.0
        category_counts: Dict[str, int] = {}
        duration_budget = target * _HIGHLIGHT_DURATION_TOLERANCE

        for score, clip in candidates:
            if len(selected) >= cap:
                break
            if total_duration + clip.duration > duration_budget and total_duration > 0:
                continue
            # Apply diversity penalty: if this category is already
            # over-represented, skip it unless the score is exceptional.
            count = category_counts.get(clip.category.value, 0)
            if count >= 3 and score < 0.7:
                continue
            penalty = count * _HIGHLIGHT_DIVERSITY_PENALTY
            adjusted = score - penalty
            if adjusted < _HIGHLIGHT_MIN_QUALITY:
                continue
            selected.append(clip.clip_id)
            total_duration += clip.duration
            category_counts[clip.category.value] = count + 1

        if not selected:
            return False, "could not assemble a highlight reel within constraints", []

        self._emit(
            "highlights_selected",
            description=f"Selected {len(selected)} highlights "
                       f"({total_duration:.1f}s) for genre {g.value}",
            data={"selected": selected, "total_duration": round(total_duration, 2),
                  "genre": g.value, "target_duration": target},
        )
        return True, "success", selected

    # ------------------------------------------------------------------
    # Transition Lifecycle
    # ------------------------------------------------------------------

    def add_transition(
        self,
        transition_id: str,
        transition_type: Any,
        duration: float = 0.5,
        source_clip: str = "",
        target_clip: str = "",
        project_id: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[TransitionEffect]]:
        """Create a transition effect and optionally bind it to a project."""
        if not transition_id:
            return False, "transition_id is required", None

        tt = _coerce_enum(TransitionType, transition_type)
        if tt is None:
            return False, f"invalid transition_type: {transition_type}", None

        with self._lock:
            if transition_id in self._transitions:
                return False, f"transition_id already exists: {transition_id}", None

            transition = TransitionEffect(
                transition_id=transition_id,
                type=tt,
                duration=max(0.0, _safe_float(duration, 0.5)),
                source_clip=source_clip,
                target_clip=target_clip,
                parameters=parameters or {},
                metadata=metadata or {},
            )
            self._transitions[transition_id] = transition
            _evict_fifo_dict(self._transitions, _MAX_TRANSITIONS)

            if project_id:
                project = self._projects.get(project_id)
                if project is None:
                    return False, f"project not found: {project_id}", None
                project.transitions.append(transition_id)
                self._touch(project)

            self._emit(
                "transition_added",
                project_id=project_id,
                description=f"Transition {transition_id} ({tt.value}) created",
                data={"transition_id": transition_id, "type": tt.value,
                      "source": source_clip, "target": target_clip},
            )
            return True, "success", transition

    def get_transition(self, transition_id: str) -> Optional[TransitionEffect]:
        return self._transitions.get(transition_id)

    def list_transitions(
        self,
        project_id: str = "",
        type_filter: str = "",
        limit: int = 100,
    ) -> List[TransitionEffect]:
        type_enum = _coerce_enum(TransitionType, type_filter) if type_filter else None
        cap = max(1, _safe_int(limit, 100))

        if project_id:
            project = self._projects.get(project_id)
            if project is None:
                return []
            result: List[TransitionEffect] = []
            for tid in project.transitions:
                t = self._transitions.get(tid)
                if t is None:
                    continue
                if type_enum is not None and t.type != type_enum:
                    continue
                result.append(t)
            return result[:cap]

        result = []
        for t in self._transitions.values():
            if type_enum is not None and t.type != type_enum:
                continue
            result.append(t)
        return result[:cap]

    def remove_transition(self, transition_id: str) -> Tuple[bool, str]:
        with self._lock:
            removed = self._transitions.pop(transition_id, None)
            if removed is None:
                return False, "not found"
            for project in self._projects.values():
                if transition_id in project.transitions:
                    project.transitions = [
                        t for t in project.transitions if t != transition_id
                    ]
                    self._touch(project)
            self._emit(
                "transition_removed",
                description=f"Transition {transition_id} removed",
                data={"transition_id": transition_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Music Lifecycle
    # ------------------------------------------------------------------

    def set_music(
        self,
        music_id: str,
        track_name: str,
        mood: str = "",
        bpm: float = 120.0,
        duration: float = 0.0,
        sync_mode: Any = None,
        cue_points: Optional[List[float]] = None,
        project_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MusicSelection]]:
        """Register a music track and optionally bind it to a project."""
        if not music_id or not track_name:
            return False, "music_id and track_name are required", None

        sm = _coerce_enum(MusicSyncMode, sync_mode, MusicSyncMode.BEAT_MATCH)

        with self._lock:
            music = MusicSelection(
                music_id=music_id,
                track_name=track_name,
                mood=mood,
                bpm=max(1.0, _safe_float(bpm, 120.0)),
                duration=max(0.0, _safe_float(duration, 0.0)),
                sync_mode=sm,
                cue_points=[_safe_float(cp, 0.0) for cp in cue_points] if cue_points else [],
                metadata=metadata or {},
            )
            self._music[music_id] = music
            _evict_fifo_dict(self._music, _MAX_MUSIC)

            if project_id:
                project = self._projects.get(project_id)
                if project is None:
                    return False, f"project not found: {project_id}", None
                project.music_track = music_id
                self._touch(project)

            self._emit(
                "music_set",
                project_id=project_id,
                description=f"Music {music_id} ({track_name}) registered",
                data={"music_id": music_id, "bpm": music.bpm,
                      "sync_mode": sm.value},
            )
            return True, "success", music

    def get_music(self, music_id: str) -> Optional[MusicSelection]:
        return self._music.get(music_id)

    def list_music(
        self,
        mood_filter: str = "",
        limit: int = 100,
    ) -> List[MusicSelection]:
        cap = max(1, _safe_int(limit, 100))
        result: List[MusicSelection] = []
        for m in self._music.values():
            if mood_filter and m.mood != mood_filter:
                continue
            result.append(m)
        return result[:cap]

    def remove_music(self, music_id: str) -> Tuple[bool, str]:
        with self._lock:
            removed = self._music.pop(music_id, None)
            if removed is None:
                return False, "not found"
            # Unbind from any project that used it.
            for project in self._projects.values():
                if project.music_track == music_id:
                    project.music_track = ""
                    self._touch(project)
            self._emit(
                "music_removed",
                description=f"Music {music_id} removed",
                data={"music_id": music_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Narrative Arc Lifecycle
    # ------------------------------------------------------------------

    def create_narrative_arc(
        self,
        arc_id: str,
        beats: Optional[List[Any]] = None,
        climax_position: float = 0.7,
        project_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[NarrativeArc]]:
        """Create a narrative arc and optionally bind it to a project.

        The pacing_curve and emotional_curve are auto-derived from the
        supplied beats so that the arc is immediately usable.
        """
        if not arc_id:
            return False, "arc_id is required", None

        with self._lock:
            if arc_id in self._narrative_arcs:
                return False, f"arc_id already exists: {arc_id}", None

            resolved_beats: List[str] = []
            for b in (beats or []):
                beat = _coerce_enum(NarrativeBeat, b)
                if beat is not None:
                    resolved_beats.append(beat.value)

            if not resolved_beats:
                resolved_beats = [b.value for b in [
                    NarrativeBeat.HOOK, NarrativeBeat.SETUP,
                    NarrativeBeat.ESCALATION, NarrativeBeat.CLIMAX,
                    NarrativeBeat.RESOLUTION, NarrativeBeat.CALL_TO_ACTION,
                ]]

            climax = _clamp(_safe_float(climax_position, 0.7))

            # Derive pacing and emotional curves from the beat sequence.
            pacing_curve: List[float] = []
            emotional_curve: List[float] = []
            beat_count = len(resolved_beats)
            for idx, beat_value in enumerate(resolved_beats):
                pos = idx / max(1, beat_count - 1)
                beat_enum = _coerce_enum(NarrativeBeat, beat_value, NarrativeBeat.SETUP)
                pacing_curve.append(self._beat_pacing_intensity(beat_enum, pos, climax))
                emotional_curve.append(self._beat_emotional_intensity(beat_enum, pos, climax))

            arc = NarrativeArc(
                arc_id=arc_id,
                beats=resolved_beats,
                pacing_curve=[round(v, 4) for v in pacing_curve],
                emotional_curve=[round(v, 4) for v in emotional_curve],
                climax_position=round(climax, 4),
                metadata=metadata or {},
            )
            self._narrative_arcs[arc_id] = arc
            _evict_fifo_dict(self._narrative_arcs, _MAX_NARRATIVE_ARCS)

            if project_id:
                project = self._projects.get(project_id)
                if project is None:
                    return False, f"project not found: {project_id}", None
                project.narrative_beats = [
                    {"beat": b, "position": round(i / max(1, beat_count - 1), 4)}
                    for i, b in enumerate(resolved_beats)
                ]
                self._touch(project)

            self._emit(
                "narrative_arc_created",
                project_id=project_id,
                description=f"Narrative arc {arc_id} created with {beat_count} beats",
                data={"arc_id": arc_id, "beats": resolved_beats,
                      "climax_position": round(climax, 4)},
            )
            return True, "success", arc

    @staticmethod
    def _beat_pacing_intensity(
        beat: NarrativeBeat, position: float, climax_pos: float,
    ) -> float:
        """Derive a 0..1 pacing intensity for a beat at a given position."""
        base = {
            NarrativeBeat.HOOK: 0.6,
            NarrativeBeat.SETUP: 0.3,
            NarrativeBeat.ESCALATION: 0.55,
            NarrativeBeat.TWIST: 0.7,
            NarrativeBeat.CLIMAX: 0.95,
            NarrativeBeat.RESOLUTION: 0.4,
            NarrativeBeat.CALL_TO_ACTION: 0.8,
        }.get(beat, 0.5)
        # Intensity rises as we approach the climax position.
        proximity = 1.0 - min(1.0, abs(position - climax_pos))
        return _clamp(base * 0.7 + proximity * 0.3)

    @staticmethod
    def _beat_emotional_intensity(
        beat: NarrativeBeat, position: float, climax_pos: float,
    ) -> float:
        """Derive a 0..1 emotional intensity for a beat at a given position."""
        base = {
            NarrativeBeat.HOOK: 0.4,
            NarrativeBeat.SETUP: 0.25,
            NarrativeBeat.ESCALATION: 0.5,
            NarrativeBeat.TWIST: 0.75,
            NarrativeBeat.CLIMAX: 1.0,
            NarrativeBeat.RESOLUTION: 0.55,
            NarrativeBeat.CALL_TO_ACTION: 0.65,
        }.get(beat, 0.4)
        return _clamp(base)

    def get_narrative_arc(self, arc_id: str) -> Optional[NarrativeArc]:
        return self._narrative_arcs.get(arc_id)

    def list_narrative_arcs(self, limit: int = 100) -> List[NarrativeArc]:
        cap = max(1, _safe_int(limit, 100))
        return list(self._narrative_arcs.values())[:cap]

    def remove_narrative_arc(self, arc_id: str) -> Tuple[bool, str]:
        with self._lock:
            removed = self._narrative_arcs.pop(arc_id, None)
            if removed is None:
                return False, "not found"
            self._emit(
                "narrative_arc_removed",
                description=f"Narrative arc {arc_id} removed",
                data={"arc_id": arc_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Pacing
    # ------------------------------------------------------------------

    def set_pacing(
        self,
        project_id: str,
        pacing: Any,
    ) -> Tuple[bool, str, Optional[TrailerProject]]:
        """Set the overall pacing mode for a project."""
        if not project_id:
            return False, "project_id is required", None
        pm = _coerce_enum(PacingMode, pacing)
        if pm is None:
            return False, f"invalid pacing: {pacing}", None

        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", None
            project.pacing = pm
            self._touch(project)
            self._emit(
                "pacing_set",
                project_id=project_id,
                description=f"Pacing set to {pm.value} for project {project_id}",
                data={"pacing": pm.value},
            )
            return True, "success", project

    def auto_pace(
        self,
        project_id: str,
    ) -> Tuple[bool, str, Optional[TrailerProject]]:
        """Auto-derive pacing for a project from its narrative beats.

        The AI auto-pacer examines the project's narrative beats, maps each
        beat to a pacing mode, and selects the dominant pacing mode for the
        overall project. It also populates per-beat pacing descriptors in the
        project's narrative_beats list so downstream rendering can vary cut
        speed across the timeline.
        """
        if not project_id:
            return False, "project_id is required", None

        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", None

            beats = project.narrative_beats
            if not beats:
                return False, "project has no narrative beats; create an arc first", None

            pacing_counts: Dict[str, int] = {}
            for beat_entry in beats:
                beat_value = beat_entry.get("beat", "") if isinstance(beat_entry, dict) else str(beat_entry)
                beat_enum = _coerce_enum(NarrativeBeat, beat_value, NarrativeBeat.SETUP)
                pacing = self._beat_to_pacing(beat_enum)
                pacing_counts[pacing.value] = pacing_counts.get(pacing.value, 0) + 1
                if isinstance(beat_entry, dict):
                    beat_entry["pacing"] = pacing.value

            if not pacing_counts:
                return False, "could not derive pacing from beats", None

            # The dominant pacing is the most frequent one; ties favor the
            # pacing associated with the climax beat.
            dominant_str = max(pacing_counts, key=lambda k: pacing_counts[k])
            dominant = _coerce_enum(PacingMode, dominant_str, PacingMode.STEADY)
            project.pacing = dominant
            self._touch(project)

            self._emit(
                "auto_pace_completed",
                project_id=project_id,
                description=f"Auto-paced project {project_id} as {dominant.value}",
                data={"dominant_pacing": dominant.value,
                      "pacing_distribution": pacing_counts},
            )
            return True, "success", project

    # ------------------------------------------------------------------
    # Music Synchronization
    # ------------------------------------------------------------------

    def sync_music(
        self,
        project_id: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Align clip boundaries to music beats for a polished cut.

        The AI synchronizer computes the beat interval from the bound music
        track's BPM, then for each clip boundary snaps it to the nearest beat
        or cue point. It returns an alignment report with per-boundary
        adjustments and the overall sync quality.
        """
        if not project_id:
            return False, "project_id is required", {}

        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", {}
            if not project.clips:
                return False, "project has no clips to synchronize", {}
            if not project.music_track:
                return False, "project has no music track bound", {}

            music = self._music.get(project.music_track)
            if music is None:
                return False, "bound music track not found in library", {}

            clips = self._project_clips(project_id)
            if not clips:
                return False, "no resolvable clips in project", {}

            beat_interval = self._beat_interval(music)
            cue_points = list(music.cue_points) if music.cue_points else []

            # Walk the timeline and compute cumulative boundaries.
            boundaries: List[float] = [0.0]
            cumulative = 0.0
            for clip in clips:
                cumulative += clip.duration
                boundaries.append(round(cumulative, 4))

            adjustments: List[Dict[str, Any]] = []
            snapped_count = 0
            total_drift = 0.0

            for idx in range(1, len(boundaries) - 1):
                original = boundaries[idx]
                snapped = original

                if music.sync_mode == MusicSyncMode.BEAT_MATCH:
                    # Snap to nearest beat.
                    if beat_interval > 0:
                        nearest_beat = round(original / beat_interval) * beat_interval
                        snapped = round(nearest_beat, 4)
                elif music.sync_mode == MusicSyncMode.PHRASE_ALIGN:
                    # Snap to nearest cue point, or to a phrase boundary
                    # (every 8 beats) if no cue points are nearby.
                    if cue_points:
                        nearest_cue = min(cue_points, key=lambda cp: abs(cp - original))
                        if abs(nearest_cue - original) <= beat_interval * 4:
                            snapped = round(nearest_cue, 4)
                    elif beat_interval > 0:
                        phrase_len = beat_interval * 8
                        nearest_phrase = round(original / phrase_len) * phrase_len
                        snapped = round(nearest_phrase, 4)
                elif music.sync_mode == MusicSyncMode.EMOTIONAL_CUE:
                    # Snap only to the nearest cue point.
                    if cue_points:
                        nearest_cue = min(cue_points, key=lambda cp: abs(cp - original))
                        snapped = round(nearest_cue, 4)
                elif music.sync_mode == MusicSyncMode.DYNAMIC:
                    # Blend beat-matching with cue-point snapping.
                    beat_snap = original
                    if beat_interval > 0:
                        beat_snap = round(original / beat_interval) * beat_interval
                    if cue_points:
                        nearest_cue = min(cue_points, key=lambda cp: abs(cp - original))
                        if abs(nearest_cue - original) < abs(beat_snap - original):
                            snapped = round(nearest_cue, 4)
                        else:
                            snapped = round(beat_snap, 4)
                    else:
                        snapped = round(beat_snap, 4)
                else:
                    # NONE: no adjustment.
                    pass

                drift = round(abs(snapped - original), 4)
                if drift > 0.001:
                    snapped_count += 1
                total_drift += drift
                adjustments.append({
                    "boundary_index": idx,
                    "original": original,
                    "snapped": snapped,
                    "drift": drift,
                })

            sync_quality = 1.0
            if adjustments:
                avg_drift = total_drift / len(adjustments)
                sync_quality = _clamp(1.0 - avg_drift / max(beat_interval, 0.1))

            project.metadata["last_sync"] = {
                "timestamp": _now(),
                "sync_mode": music.sync_mode.value,
                "bpm": music.bpm,
                "beat_interval": round(beat_interval, 4),
                "snapped_boundaries": snapped_count,
                "sync_quality": round(sync_quality, 4),
            }
            self._touch(project)

            report = {
                "project_id": project_id,
                "music_id": music.music_id,
                "sync_mode": music.sync_mode.value,
                "bpm": music.bpm,
                "beat_interval": round(beat_interval, 4),
                "total_boundaries": len(adjustments),
                "snapped_boundaries": snapped_count,
                "sync_quality": round(sync_quality, 4),
                "adjustments": adjustments,
            }
            self._emit(
                "music_synced",
                project_id=project_id,
                description=f"Music synced for project {project_id} "
                           f"(quality={sync_quality:.2f})",
                data={"sync_quality": round(sync_quality, 4),
                      "snapped_boundaries": snapped_count},
            )
            return True, "success", report

    # ------------------------------------------------------------------
    # Render Job Lifecycle
    # ------------------------------------------------------------------

    def start_render(
        self,
        job_id: str,
        project_id: str,
        resolution: str = "",
        fps: int = 0,
        format: str = "",
        quality_preset: str = "high",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[RenderJob]]:
        """Start a render job for a project."""
        if not job_id or not project_id:
            return False, "job_id and project_id are required", None

        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", None
            if not project.clips:
                return False, "project has no clips to render", None
            if job_id in self._render_jobs:
                return False, f"job_id already exists: {job_id}", None

            job = RenderJob(
                job_id=job_id,
                project_id=project_id,
                resolution=resolution or self._config.default_resolution,
                fps=fps if fps > 0 else self._config.default_fps,
                format=format or "mp4",
                quality_preset=quality_preset,
                status=TrailerStatus.RENDERING,
                progress=0.0,
                output_path="",
                metadata=metadata or {},
            )
            self._render_jobs[job_id] = job
            _evict_fifo_dict(self._render_jobs, _MAX_RENDER_JOBS)

            project.status = TrailerStatus.RENDERING
            self._touch(project)

            self._emit(
                "render_started",
                project_id=project_id,
                description=f"Render job {job_id} started for project {project_id}",
                data={"job_id": job_id, "resolution": job.resolution,
                      "fps": job.fps, "format": job.format},
            )
            return True, "success", job

    def get_render_job(self, job_id: str) -> Optional[RenderJob]:
        return self._render_jobs.get(job_id)

    def list_render_jobs(
        self,
        project_id: str = "",
        status_filter: str = "",
        limit: int = 100,
    ) -> List[RenderJob]:
        status_enum = _coerce_enum(TrailerStatus, status_filter) if status_filter else None
        cap = max(1, _safe_int(limit, 100))
        result: List[RenderJob] = []
        for j in self._render_jobs.values():
            if project_id and j.project_id != project_id:
                continue
            if status_enum is not None and j.status != status_enum:
                continue
            result.append(j)
        result.sort(key=lambda x: x.job_id, reverse=True)
        return result[:cap]

    def cancel_render(self, job_id: str) -> Tuple[bool, str, Optional[RenderJob]]:
        """Cancel an in-progress render job."""
        with self._lock:
            job = self._render_jobs.get(job_id)
            if job is None:
                return False, "not found", None
            if job.status in (TrailerStatus.COMPLETED, TrailerStatus.FAILED):
                return False, f"cannot cancel job in status {job.status.value}", None

            job.status = TrailerStatus.FAILED
            job.metadata["cancel_reason"] = "cancelled by user"

            project = self._projects.get(job.project_id)
            if project is not None:
                project.status = TrailerStatus.FAILED
                self._touch(project)

            self._emit(
                "render_cancelled",
                project_id=job.project_id,
                description=f"Render job {job_id} cancelled",
                data={"job_id": job_id},
            )
            return True, "cancelled", job

    def _advance_render(self, job: RenderJob, dt: float) -> None:
        """Advance a single render job's progress by dt seconds."""
        if job.status != TrailerStatus.RENDERING:
            return
        step = min(_RENDER_PROGRESS_MAX_STEP,
                   dt * _RENDER_PROGRESS_PER_SECOND)
        job.progress = _clamp(job.progress + step, _PROGRESS_MIN, _PROGRESS_MAX)
        if job.progress >= _PROGRESS_MAX:
            job.progress = 1.0
            job.status = TrailerStatus.COMPLETED
            job.output_path = f"/renders/{job.project_id}/{job.job_id}.{job.format}"
            project = self._projects.get(job.project_id)
            if project is not None:
                project.status = TrailerStatus.COMPLETED
                self._touch(project)
            self._emit(
                "render_completed",
                project_id=job.project_id,
                description=f"Render job {job.job_id} completed: {job.output_path}",
                data={"job_id": job.job_id, "output_path": job.output_path},
            )

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish_trailer(
        self,
        project_id: str,
    ) -> Tuple[bool, str, Optional[TrailerProject]]:
        """Promote a completed project to published status."""
        if not project_id:
            return False, "project_id is required", None

        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False, "project not found", None
            if project.status != TrailerStatus.COMPLETED:
                return False, (
                    f"project must be COMPLETED before publishing "
                    f"(current: {project.status.value})"
                ), None

            project.status = TrailerStatus.PUBLISHED
            project.metadata["published_at"] = _now()
            self._touch(project)

            self._emit(
                "trailer_published",
                project_id=project_id,
                description=f"Trailer {project_id} ({project.title}) published",
                data={"title": project.title, "genre": project.genre.value},
            )
            return True, "success", project

    # ------------------------------------------------------------------
    # Event Log and Observability
    # ------------------------------------------------------------------

    def list_events(
        self,
        project_id: str = "",
        limit: int = 100,
    ) -> List[TrailerDirectorEvent]:
        cap = max(1, _safe_int(limit, 100))
        result: List[TrailerDirectorEvent] = []
        # Walk newest-first for a readable recent-activity feed.
        for e in reversed(self._events):
            if project_id and e.project_id != project_id:
                continue
            result.append(e)
            if len(result) >= cap:
                break
        return result

    def get_status(self) -> Dict[str, Any]:
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "projects": len(self._projects),
            "clips": len(self._clips),
            "transitions": len(self._transitions),
            "music": len(self._music),
            "narrative_arcs": len(self._narrative_arcs),
            "render_jobs": len(self._render_jobs),
            "events": len(self._events),
            "tick_count": self._tick_count,
            "config": self._config.to_dict(),
        }

    def get_stats(self) -> TrailerDirectorStats:
        self._refresh_stats()
        return self._stats

    def get_snapshot(self) -> TrailerDirectorSnapshot:
        self._refresh_stats()
        return TrailerDirectorSnapshot(
            timestamp=_now(),
            projects=[p.to_dict() for p in list(self._projects.values())[-100:]],
            clips=[c.to_dict() for c in list(self._clips.values())[-100:]],
            render_jobs=[j.to_dict() for j in list(self._render_jobs.values())[-50:]],
            stats=self._stats.to_dict(),
        )

    def get_config(self) -> TrailerDirectorConfig:
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, TrailerDirectorConfig]:
        """Update tunable configuration fields.

        Only known fields on TrailerDirectorConfig are accepted. Numeric
        fields are coerced and clamped to safe ranges.
        """
        with self._lock:
            known = set(self._config.__dataclass_fields__.keys())
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in known or key == "metadata":
                    continue
                if key == "max_projects":
                    self._config.max_projects = max(1, _safe_int(value, 2000))
                elif key == "max_clips_per_project":
                    self._config.max_clips_per_project = max(1, _safe_int(value, 50))
                elif key == "default_target_duration":
                    self._config.default_target_duration = max(1.0, _safe_float(value, 60.0))
                elif key == "default_resolution":
                    self._config.default_resolution = str(value) if value else "1920x1080"
                elif key == "default_fps":
                    self._config.default_fps = max(1, _safe_int(value, 30))
                elif key == "auto_select_clips":
                    self._config.auto_select_clips = bool(value)
                elif key == "auto_sync_music":
                    self._config.auto_sync_music = bool(value)
                elif key == "auto_pace_narrative":
                    self._config.auto_pace_narrative = bool(value)
                else:
                    continue
                applied.append(key)

            if not applied:
                return False, "no valid config fields supplied", self._config

            self._emit(
                "config_updated",
                description=f"Config updated: {', '.join(applied)}",
                data={"fields": applied},
            )
            return True, "updated", self._config

    # ------------------------------------------------------------------
    # Tick and Lifecycle
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the director by one tick.

        Increments the tick counter, refreshes statistics, and advances all
        active render jobs by the supplied time delta. When auto-select,
        auto-sync, or auto-pace are enabled, those AI passes run for
        eligible projects.
        """
        dt_seconds = max(0.0, _safe_float(dt, 1.0))
        with self._lock:
            self._tick_count += 1
            self._refresh_stats()

            # Advance active render jobs.
            completed_jobs: List[str] = []
            for job in self._render_jobs.values():
                if job.status == TrailerStatus.RENDERING:
                    self._advance_render(job, dt_seconds)
                    if job.status == TrailerStatus.COMPLETED:
                        completed_jobs.append(job.job_id)

            # Auto-select highlights for draft projects that have no clips.
            auto_selected: List[str] = []
            if self._config.auto_select_clips:
                for project in self._projects.values():
                    if project.status == TrailerStatus.DRAFT and not project.clips:
                        pool = list(self._clips.keys())
                        ok, _, selected = self.select_highlights(
                            pool,
                            target_duration=project.target_duration,
                            genre=project.genre,
                        )
                        if ok and selected:
                            for cid in selected:
                                project.clips.append(cid)
                            auto_selected.append(project.project_id)
                            self._touch(project)

            # Auto-sync music for editing projects that have music bound.
            auto_synced: List[str] = []
            if self._config.auto_sync_music:
                for project in self._projects.values():
                    if (project.status == TrailerStatus.EDITING
                            and project.music_track
                            and project.clips):
                        ok, _, _ = self.sync_music(project.project_id)
                        if ok:
                            auto_synced.append(project.project_id)

            # Auto-pace projects that have narrative beats but no pacing set.
            auto_paced: List[str] = []
            if self._config.auto_pace_narrative:
                for project in self._projects.values():
                    if (project.status in (TrailerStatus.EDITING,
                                            TrailerStatus.SELECTING)
                            and project.narrative_beats):
                        ok, _, _ = self.auto_pace(project.project_id)
                        if ok:
                            auto_paced.append(project.project_id)

            self._emit(
                "tick",
                description=f"Tick {self._tick_count}",
                data={
                    "tick": self._tick_count,
                    "completed_jobs": completed_jobs,
                    "auto_selected": auto_selected,
                    "auto_synced": auto_synced,
                    "auto_paced": auto_paced,
                },
            )
            return {
                "status": "ok",
                "tick": self._tick_count,
                "projects": len(self._projects),
                "clips": len(self._clips),
                "render_jobs": len(self._render_jobs),
                "completed_jobs": completed_jobs,
                "auto_selected": auto_selected,
                "auto_synced": auto_synced,
                "auto_paced": auto_paced,
                "stats": self._stats.to_dict(),
            }

    def reset(self) -> None:
        """Clear all director state and re-seed the canonical dataset."""
        with self._lock:
            self._clips.clear()
            self._projects.clear()
            self._transitions.clear()
            self._music.clear()
            self._narrative_arcs.clear()
            self._render_jobs.clear()
            self._events.clear()
            self._config = TrailerDirectorConfig()
            self._stats = TrailerDirectorStats()
            self._tick_count = 0
            self._initialized = False
            self._seed()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the director with a canonical set of trailer data."""
        base_time = datetime.utcnow()

        # ----------------------------------------------------------
        # Gameplay Clips (10)
        # ----------------------------------------------------------
        clip_seeds = [
            ("clip_boss_fight_01", "sess_raid_01", ClipCategory.BOSS_FIGHT,
             18.5, 0.92, "Epic raid boss takedown with full party coordination",
             ["raid", "boss", "coop", "endgame"]),
            ("clip_explosion_03", "sess_combat_03", ClipCategory.EXPLOSION,
             6.2, 0.85, "Massive environmental explosion during a set-piece battle",
             ["explosion", "setpiece", "combat"]),
            ("clip_emotional_02", "sess_story_02", ClipCategory.EMOTIONAL_MOMENT,
             24.0, 0.88, "Emotional character farewell cutscene",
             ["story", "emotional", "cutscene"]),
            ("clip_funny_01", "sess_free_01", ClipCategory.FUNNY_MOMENT,
             8.5, 0.72, "Unexpected physics glitch sends NPC flying",
             ["funny", "glitch", "physics"]),
            ("clip_achievement_04", "sess_progress_04", ClipCategory.ACHIEVEMENT,
             12.0, 0.81, "Player unlocks a prestigious legendary achievement",
             ["achievement", "milestone", "progression"]),
            ("clip_cutscene_01", "sess_story_01", ClipCategory.CUTSCENE,
             32.0, 0.86, "Opening cinematic introducing the main antagonist",
             ["cutscene", "cinematic", "intro", "antagonist"]),
            ("clip_intro_01", "sess_intro_01", ClipCategory.INTRO,
             15.0, 0.78, "Title card sequence with logo reveal",
             ["intro", "title", "logo"]),
            ("clip_outro_01", "sess_outro_01", ClipCategory.OUTRO,
             10.0, 0.70, "Closing credits and call-to-action card",
             ["outro", "credits", "cta"]),
            ("clip_gameplay_highlight_02", "sess_pvp_02", ClipCategory.GAMEPLAY_HIGHLIGHT,
             14.5, 0.83, "Skilled PvP combo string leading to a decisive win",
             ["pvp", "combo", "skill", "highlight"]),
            ("clip_custom_01", "sess_custom_01", ClipCategory.CUSTOM,
             20.0, 0.65, "Community-requested montage of exploration moments",
             ["exploration", "montage", "community"]),
        ]
        for idx, (cid, sess, cat, dur, quality, desc, tags) in enumerate(clip_seeds):
            ts = (base_time - timedelta(hours=len(clip_seeds) - idx)).isoformat() + "Z"
            clip = GameplayClip(
                clip_id=cid,
                source_session=sess,
                timestamp=ts,
                duration=dur,
                category=cat,
                quality_score=quality,
                description=desc,
                tags=tags,
                metadata={"seed": True},
            )
            self._clips[cid] = clip

        # ----------------------------------------------------------
        # Trailer Projects (5)
        # ----------------------------------------------------------
        project_seeds = [
            ("proj_announce_01", "Season 4 Announcement Trailer",
             TrailerGenre.ANNOUNCEMENT, 90.0,
             TrailerStatus.EDITING,
             ["clip_intro_01", "clip_cutscene_01", "clip_boss_fight_01",
              "clip_explosion_03", "clip_achievement_04", "clip_outro_01"],
             "music_epic_01"),
            ("proj_gameplay_01", "Gameplay Highlights Reel",
             TrailerGenre.GAMEPLAY, 60.0,
             TrailerStatus.SELECTING,
             ["clip_gameplay_highlight_02", "clip_boss_fight_01",
              "clip_explosion_03", "clip_achievement_04"],
             "music_hype_01"),
            ("proj_story_01", "Story Cinematic Trailer",
             TrailerGenre.STORY, 120.0,
             TrailerStatus.DRAFT,
             ["clip_cutscene_01", "clip_emotional_02"],
             "music_cinematic_01"),
            ("proj_teaser_01", "Pre-Launch Teaser",
             TrailerGenre.TEASER, 30.0,
             TrailerStatus.COMPLETED,
             ["clip_intro_01", "clip_boss_fight_01"],
             "music_teaser_01"),
            ("proj_update_01", "Patch 2.5 Update Trailer",
             TrailerGenre.UPDATE, 45.0,
             TrailerStatus.DRAFT,
             [],
             ""),
        ]
        for idx, (pid, title, genre, dur, status, clip_ids, music_id) in enumerate(project_seeds):
            now = (base_time - timedelta(hours=len(project_seeds) - idx)).isoformat() + "Z"
            project = TrailerProject(
                project_id=pid,
                title=title,
                genre=genre,
                target_duration=dur,
                status=status,
                clips=list(clip_ids),
                transitions=[],
                music_track=music_id,
                pacing=PacingMode.STEADY,
                narrative_beats=[],
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            )
            self._projects[pid] = project

        # ----------------------------------------------------------
        # Transitions (6)
        # ----------------------------------------------------------
        transition_seeds = [
            ("trans_01", TransitionType.CROSSFADE, 0.8,
             "clip_intro_01", "clip_cutscene_01", "proj_announce_01",
             {"curve": "ease_in_out"}),
            ("trans_02", TransitionType.WHIP_PAN, 0.3,
             "clip_cutscene_01", "clip_boss_fight_01", "proj_announce_01",
             {"direction": "left"}),
            ("trans_03", TransitionType.CUT, 0.0,
             "clip_gameplay_highlight_02", "clip_boss_fight_01", "proj_gameplay_01",
             {}),
            ("trans_04", TransitionType.ZOOM, 0.5,
             "clip_boss_fight_01", "clip_explosion_03", "proj_gameplay_01",
             {"scale": 1.5}),
            ("trans_05", TransitionType.DISSOLVE, 1.2,
             "clip_cutscene_01", "clip_emotional_02", "proj_story_01",
             {"layers": 3}),
            ("trans_06", TransitionType.GLITCH, 0.4,
             "clip_intro_01", "clip_boss_fight_01", "proj_teaser_01",
             {"intensity": 0.7}),
        ]
        for tid, tt, dur, src, tgt, pid, params in transition_seeds:
            transition = TransitionEffect(
                transition_id=tid,
                type=tt,
                duration=dur,
                source_clip=src,
                target_clip=tgt,
                parameters=params,
                metadata={"seed": True},
            )
            self._transitions[tid] = transition
            project = self._projects.get(pid)
            if project is not None:
                project.transitions.append(tid)

        # ----------------------------------------------------------
        # Music Selections (5)
        # ----------------------------------------------------------
        music_seeds = [
            ("music_epic_01", "Triumphant Skies", "epic", 140.0, 180.0,
             MusicSyncMode.DYNAMIC, [0.0, 30.0, 60.0, 90.0, 120.0, 150.0]),
            ("music_cinematic_01", "Whispers of Dawn", "cinematic", 90.0, 240.0,
             MusicSyncMode.PHRASE_ALIGN, [0.0, 32.0, 64.0, 96.0, 128.0, 160.0]),
            ("music_hype_01", "Adrenaline Rush", "hype", 160.0, 120.0,
             MusicSyncMode.BEAT_MATCH, []),
            ("music_emotional_01", "Fading Light", "emotional", 70.0, 200.0,
             MusicSyncMode.EMOTIONAL_CUE, [0.0, 40.0, 80.0, 120.0, 160.0]),
            ("music_teaser_01", "Mystery Pulse", "tension", 128.0, 60.0,
             MusicSyncMode.BEAT_MATCH, [0.0, 15.0, 30.0, 45.0]),
        ]
        for mid, name, mood, bpm, dur, sm, cues in music_seeds:
            music = MusicSelection(
                music_id=mid,
                track_name=name,
                mood=mood,
                bpm=bpm,
                duration=dur,
                sync_mode=sm,
                cue_points=cues,
                metadata={"seed": True},
            )
            self._music[mid] = music

        # ----------------------------------------------------------
        # Narrative Arcs (4)
        # ----------------------------------------------------------
        arc_seeds = [
            ("arc_classic_01",
             [NarrativeBeat.HOOK, NarrativeBeat.SETUP, NarrativeBeat.ESCALATION,
              NarrativeBeat.CLIMAX, NarrativeBeat.RESOLUTION,
              NarrativeBeat.CALL_TO_ACTION],
             0.7, "proj_announce_01"),
            ("arc_teaser_01",
             [NarrativeBeat.HOOK, NarrativeBeat.TWIST, NarrativeBeat.CALL_TO_ACTION],
             0.5, "proj_teaser_01"),
            ("arc_hype_01",
             [NarrativeBeat.HOOK, NarrativeBeat.ESCALATION, NarrativeBeat.CLIMAX,
              NarrativeBeat.CALL_TO_ACTION],
             0.65, "proj_gameplay_01"),
            ("arc_documentary_01",
             [NarrativeBeat.SETUP, NarrativeBeat.ESCALATION, NarrativeBeat.CLIMAX,
              NarrativeBeat.RESOLUTION],
             0.75, ""),
        ]
        for arc_id, beats, climax, pid in arc_seeds:
            beat_values = [b.value for b in beats]
            beat_count = len(beat_values)
            pacing_curve: List[float] = []
            emotional_curve: List[float] = []
            for idx, bv in enumerate(beat_values):
                pos = idx / max(1, beat_count - 1)
                beat_enum = _coerce_enum(NarrativeBeat, bv, NarrativeBeat.SETUP)
                pacing_curve.append(round(self._beat_pacing_intensity(beat_enum, pos, climax), 4))
                emotional_curve.append(round(self._beat_emotional_intensity(beat_enum, pos, climax), 4))
            arc = NarrativeArc(
                arc_id=arc_id,
                beats=beat_values,
                pacing_curve=pacing_curve,
                emotional_curve=emotional_curve,
                climax_position=round(climax, 4),
                metadata={"seed": True},
            )
            self._narrative_arcs[arc_id] = arc
            if pid:
                project = self._projects.get(pid)
                if project is not None:
                    project.narrative_beats = [
                        {"beat": bv, "position": round(i / max(1, beat_count - 1), 4)}
                        for i, bv in enumerate(beat_values)
                    ]
                    self._touch(project)

        # ----------------------------------------------------------
        # Render Jobs (3)
        # ----------------------------------------------------------
        render_seeds = [
            ("render_01", "proj_teaser_01", "1920x1080", 30, "mp4", "high",
             TrailerStatus.COMPLETED, 1.0,
             "/renders/proj_teaser_01/render_01.mp4"),
            ("render_02", "proj_announce_01", "3840x2160", 60, "mp4", "ultra",
             TrailerStatus.RENDERING, 0.45, ""),
            ("render_03", "proj_gameplay_01", "1920x1080", 60, "mp4", "high",
             TrailerStatus.RENDERING, 0.12, ""),
        ]
        for jid, pid, res, fps, fmt, qp, status, prog, out in render_seeds:
            job = RenderJob(
                job_id=jid,
                project_id=pid,
                resolution=res,
                fps=fps,
                format=fmt,
                quality_preset=qp,
                status=status,
                progress=prog,
                output_path=out,
                metadata={"seed": True},
            )
            self._render_jobs[jid] = job

        # ----------------------------------------------------------
        # Events (4)
        # ----------------------------------------------------------
        self._emit(
            "director_seeded",
            description="AI Trailer Director initialized with canonical dataset",
            data={
                "projects": len(self._projects),
                "clips": len(self._clips),
                "transitions": len(self._transitions),
                "music": len(self._music),
                "narrative_arcs": len(self._narrative_arcs),
                "render_jobs": len(self._render_jobs),
            },
        )
        self._emit(
            "render_completed",
            project_id="proj_teaser_01",
            description="Render job render_01 completed: /renders/proj_teaser_01/render_01.mp4",
            data={"job_id": "render_01",
                  "output_path": "/renders/proj_teaser_01/render_01.mp4"},
        )
        self._emit(
            "music_synced",
            project_id="proj_announce_01",
            description="Music synced for project proj_announce_01 (quality=0.92)",
            data={"sync_quality": 0.92, "snapped_boundaries": 3},
        )
        self._emit(
            "highlights_selected",
            description="Selected 4 highlights (51.2s) for genre gameplay",
            data={"selected": ["clip_gameplay_highlight_02", "clip_boss_fight_01",
                               "clip_explosion_03", "clip_achievement_04"],
                  "total_duration": 51.2, "genre": "gameplay"},
        )

        self._refresh_stats()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_ai_trailer_director() -> AITrailerDirector:
    """Return the shared AITrailerDirector singleton instance."""
    return AITrailerDirector.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "TrailerGenre",
    "ClipCategory",
    "TransitionType",
    "PacingMode",
    "MusicSyncMode",
    "TrailerStatus",
    "NarrativeBeat",
    # Data classes
    "GameplayClip",
    "TrailerProject",
    "TransitionEffect",
    "MusicSelection",
    "NarrativeArc",
    "RenderJob",
    "TrailerDirectorConfig",
    "TrailerDirectorStats",
    "TrailerDirectorSnapshot",
    "TrailerDirectorEvent",
    # Main system
    "AITrailerDirector",
    "get_ai_trailer_director",
]
