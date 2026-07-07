"""
SparkLabs Agent - AI Voice Acting Director

Orchestrates the entire voiceover production pipeline for a game. The
director manages a roster of voice actors, casts them against character
roles, schedules recording sessions, provides emotional delivery
direction with line-by-line performance cues, coordinates lip-sync
markers, and reviews recorded takes to select the best performances.

Architecture:
  VoiceActingDirector (singleton)
    |-- VoiceActor, CharacterRole, VoiceLine, DeliveryDirection,
        RecordingTake, LipSyncMarker, CastingSession, ReviewNote,
        VoiceoverProject, DirectorStats, DirectorSnapshot, DirectorEvent
    |-- VoiceGender, VoiceAgeRange, EmotionType, TakeStatus,
        SessionStatus, ProjectStatus, LipSyncStatus, ReviewVerdict,
        DirectorEventKind

Core Capabilities:
  - register_actor / update_actor / get_actor / list_actors /
    delete_actor: voice actor roster management with vocal range,
    language proficiency, and availability tracking.
  - create_character / update_character / get_character / list_characters:
    character role definitions with voice profile requirements.
  - cast_actor / uncast_actor / get_casting: assign actors to characters
    with match scoring and audition notes.
  - create_line / update_line / get_line / list_lines: script lines with
    emotion, intensity, pacing, and pronunciation guides.
  - add_direction / get_direction: per-line delivery direction with
    emotional cues, emphasis markers, and breathing instructions.
  - record_take / review_take / select_take / list_takes: recording
    session workflow with take quality scoring and selection.
  - add_lip_sync / get_lip_sync / list_lip_sync: viseme and timing
    markers for lip-sync animation coordination.
  - create_session / start_session / complete_session / list_sessions:
    recording session lifecycle management.
  - create_project / update_project / get_project / list_projects:
    voiceover project tracking across game builds.
  - generate_report / get_report / list_reports: comprehensive
    production reports with coverage analysis.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`VoiceActingDirector.get_instance` or the module-level
:func:`get_voice_acting_director` factory.
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

_MAX_ACTORS: int = 500
_MAX_CHARACTERS: int = 500
_MAX_LINES: int = 5000
_MAX_TAKES: int = 10000
_MAX_SESSIONS: int = 200
_MAX_PROJECTS: int = 100
_MAX_REPORTS: int = 200
_MAX_EVENTS: int = 5000
_MAX_DIRECTIONS_PER_LINE: int = 10
_MAX_LIP_SYNC_PER_LINE: int = 50
_MAX_TAKES_PER_LINE: int = 20


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


class VoiceGender(Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    ANY = "any"


class VoiceAgeRange(Enum):
    CHILD = "child"
    TEEN = "teen"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    MIDDLE_AGED = "middle_aged"
    SENIOR = "senior"
    ELDERLY = "elderly"


class EmotionType(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    AFRAID = "afraid"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    EXCITED = "excited"
    CALM = "calm"
    WHISPER = "whisper"
    SHOUTING = "shouting"
    SARCASTIC = "sarcastic"
    TENDER = "tender"
    MENACING = "menacing"


class TakeStatus(Enum):
    PENDING = "pending"
    RECORDED = "recorded"
    REVIEWED = "reviewed"
    SELECTED = "selected"
    REJECTED = "rejected"
    RE_RECORD = "re_record"


class SessionStatus(Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ProjectStatus(Enum):
    DRAFT = "draft"
    CASTING = "casting"
    RECORDING = "recording"
    POST_PRODUCTION = "post_production"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class LipSyncStatus(Enum):
    PENDING = "pending"
    ALIGNED = "aligned"
    MISALIGNED = "misaligned"
    MANUAL_EDIT = "manual_edit"
    APPROVED = "approved"


class ReviewVerdict(Enum):
    APPROVED = "approved"
    NEEDS_RETAKE = "needs_retake"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"


class DirectorEventKind(Enum):
    ACTOR_REGISTERED = "actor_registered"
    ACTOR_UPDATED = "actor_updated"
    ACTOR_REMOVED = "actor_removed"
    CHARACTER_CREATED = "character_created"
    CHARACTER_UPDATED = "character_updated"
    ACTOR_CAST = "actor_cast"
    ACTOR_UNCAST = "actor_uncast"
    LINE_CREATED = "line_created"
    LINE_UPDATED = "line_updated"
    DIRECTION_ADDED = "direction_added"
    TAKE_RECORDED = "take_recorded"
    TAKE_REVIEWED = "take_reviewed"
    TAKE_SELECTED = "take_selected"
    LIP_SYNC_ADDED = "lip_sync_added"
    LIP_SYNC_UPDATED = "lip_sync_updated"
    SESSION_CREATED = "session_created"
    SESSION_STARTED = "session_started"
    SESSION_COMPLETED = "session_completed"
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    REPORT_GENERATED = "report_generated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class VoiceActor:
    """A voice actor in the roster."""
    actor_id: str
    name: str
    gender: VoiceGender = VoiceGender.ANY
    age_range: VoiceAgeRange = VoiceAgeRange.ADULT
    vocal_range_low: str = ""
    vocal_range_high: str = ""
    accent: str = ""
    languages: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    bio: str = ""
    contact_info: str = ""
    rate_per_hour: float = 0.0
    availability: str = "available"
    total_lines_recorded: int = 0
    average_take_quality: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CharacterRole:
    """A character that needs voice acting."""
    character_id: str
    name: str
    game_title: str = ""
    description: str = ""
    gender: VoiceGender = VoiceGender.ANY
    age_range: VoiceAgeRange = VoiceAgeRange.ADULT
    accent_requirement: str = ""
    vocal_traits: List[str] = field(default_factory=list)
    personality: str = ""
    total_lines: int = 0
    cast_actor_id: str = ""
    project_id: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceLine:
    """A single line of dialogue that needs recording."""
    line_id: str
    character_id: str
    project_id: str
    text: str
    context: str = ""
    emotion: EmotionType = EmotionType.NEUTRAL
    intensity: float = 0.5
    pacing: str = "normal"
    pronunciation_guide: str = ""
    estimated_duration_seconds: float = 0.0
    scene_reference: str = ""
    sequence_order: int = 0
    status: str = "pending"
    selected_take_id: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DeliveryDirection:
    """Per-line delivery direction from the director."""
    direction_id: str
    line_id: str
    emotion_cue: str = ""
    emphasis_words: List[str] = field(default_factory=list)
    pacing_instruction: str = ""
    breathing_instruction: str = ""
    pitch_guidance: str = ""
    volume_level: str = "normal"
    additional_notes: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RecordingTake:
    """A recorded take of a voice line."""
    take_id: str
    line_id: str
    actor_id: str
    session_id: str
    audio_file: str = ""
    duration_seconds: float = 0.0
    quality_score: float = 0.0
    emotion_accuracy: float = 0.0
    pacing_accuracy: float = 0.0
    clarity: float = 0.0
    energy: float = 0.0
    status: TakeStatus = TakeStatus.PENDING
    notes: str = ""
    created_at: str = field(default_factory=_now)
    reviewed_at: str = ""
    reviewed_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LipSyncMarker:
    """Lip-sync timing markers for a voice line."""
    marker_id: str
    line_id: str
    viseme_sequence: List[Dict[str, Any]] = field(default_factory=list)
    phoneme_timings: List[Dict[str, Any]] = field(default_factory=list)
    total_duration: float = 0.0
    status: LipSyncStatus = LipSyncStatus.PENDING
    alignment_score: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CastingSession:
    """A casting decision pairing an actor with a character."""
    casting_id: str
    character_id: str
    actor_id: str
    project_id: str
    match_score: float = 0.0
    audition_notes: str = ""
    director_notes: str = ""
    is_primary: bool = True
    is_backup: bool = False
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReviewNote:
    """A director's review note on a take."""
    note_id: str
    take_id: str
    reviewer: str = "Director"
    verdict: ReviewVerdict = ReviewVerdict.CONDITIONAL
    score: float = 0.0
    comment: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RecordingSession:
    """A recording session for voice acting."""
    session_id: str
    project_id: str
    actor_id: str
    name: str = ""
    scheduled_start: str = ""
    scheduled_end: str = ""
    actual_start: str = ""
    actual_end: str = ""
    status: SessionStatus = SessionStatus.SCHEDULED
    lines_planned: int = 0
    lines_completed: int = 0
    total_takes: int = 0
    studio_location: str = ""
    notes: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceoverProject:
    """A voiceover production project."""
    project_id: str
    name: str
    game_title: str = ""
    build_version: str = ""
    description: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    total_characters: int = 0
    total_lines: int = 0
    recorded_lines: int = 0
    reviewed_lines: int = 0
    selected_lines: int = 0
    budget: float = 0.0
    spent: float = 0.0
    start_date: str = ""
    target_completion: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorReport:
    """A comprehensive production report."""
    report_id: str
    project_id: str
    title: str = "Voiceover Production Report"
    summary: str = ""
    coverage_percentage: float = 0.0
    total_lines: int = 0
    recorded_lines: int = 0
    selected_lines: int = 0
    pending_lines: int = 0
    total_takes: int = 0
    average_quality: float = 0.0
    total_actors: int = 0
    total_sessions: int = 0
    budget_used: float = 0.0
    character_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorStats:
    """Aggregate statistics."""
    total_actors: int = 0
    total_characters: int = 0
    total_lines: int = 0
    total_takes: int = 0
    total_sessions: int = 0
    total_projects: int = 0
    total_reports: int = 0
    total_castings: int = 0
    total_lip_sync_markers: int = 0
    total_directions: int = 0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorSnapshot:
    """Full state snapshot."""
    actors: List[Dict[str, Any]] = field(default_factory=list)
    characters: List[Dict[str, Any]] = field(default_factory=list)
    lines: List[Dict[str, Any]] = field(default_factory=list)
    takes: List[Dict[str, Any]] = field(default_factory=list)
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    projects: List[Dict[str, Any]] = field(default_factory=list)
    castings: List[Dict[str, Any]] = field(default_factory=list)
    lip_sync_markers: List[Dict[str, Any]] = field(default_factory=list)
    directions: List[Dict[str, Any]] = field(default_factory=list)
    reports: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorEvent:
    """Audit event."""
    event_id: str
    kind: DirectorEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Voice Acting Director Singleton
# ---------------------------------------------------------------------------


class VoiceActingDirector:
    """AI Voice Acting Director - orchestrates voiceover production."""

    _instance: Optional["VoiceActingDirector"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "VoiceActingDirector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "VoiceActingDirector":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._actors: Dict[str, VoiceActor] = {}
            self._characters: Dict[str, CharacterRole] = {}
            self._lines: Dict[str, VoiceLine] = {}
            self._directions: Dict[str, DeliveryDirection] = {}
            self._takes: Dict[str, RecordingTake] = {}
            self._lip_sync: Dict[str, LipSyncMarker] = {}
            self._castings: Dict[str, CastingSession] = {}
            self._sessions: Dict[str, RecordingSession] = {}
            self._projects: Dict[str, VoiceoverProject] = {}
            self._reports: Dict[str, DirectorReport] = {}
            self._events: List[DirectorEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(self, kind: DirectorEventKind, data: Dict[str, Any]) -> None:
        event = DirectorEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # --- Actor Management ---

    def register_actor(self, name: str, gender: VoiceGender = VoiceGender.ANY,
                       age_range: VoiceAgeRange = VoiceAgeRange.ADULT,
                       vocal_range_low: str = "", vocal_range_high: str = "",
                       accent: str = "", languages: List[str] = None,
                       tags: List[str] = None, bio: str = "",
                       contact_info: str = "", rate_per_hour: float = 0.0,
                       availability: str = "available") -> VoiceActor:
        with self._lock:
            actor = VoiceActor(
                actor_id=_new_id("act"),
                name=name,
                gender=gender,
                age_range=age_range,
                vocal_range_low=vocal_range_low,
                vocal_range_high=vocal_range_high,
                accent=accent,
                languages=languages or [],
                tags=tags or [],
                bio=bio,
                contact_info=contact_info,
                rate_per_hour=rate_per_hour,
                availability=availability,
            )
            self._actors[actor.actor_id] = actor
            _evict_fifo_dict(self._actors, _MAX_ACTORS)
            self._emit(DirectorEventKind.ACTOR_REGISTERED, {"actor_id": actor.actor_id, "name": name})
            return actor

    def update_actor(self, actor_id: str, updates: Dict[str, Any]) -> Optional[VoiceActor]:
        with self._lock:
            actor = self._actors.get(actor_id)
            if actor is None:
                return None
            for k, v in updates.items():
                if k == "gender" and isinstance(v, str):
                    try:
                        v = VoiceGender(v)
                    except ValueError:
                        continue
                elif k == "age_range" and isinstance(v, str):
                    try:
                        v = VoiceAgeRange(v)
                    except ValueError:
                        continue
                if hasattr(actor, k) and k not in ("actor_id", "created_at"):
                    setattr(actor, k, v)
            actor.updated_at = _now()
            self._emit(DirectorEventKind.ACTOR_UPDATED, {"actor_id": actor_id})
            return actor

    def get_actor(self, actor_id: str) -> Optional[VoiceActor]:
        with self._lock:
            return self._actors.get(actor_id)

    def list_actors(self, gender: VoiceGender = None,
                    age_range: VoiceAgeRange = None,
                    language: str = None) -> List[VoiceActor]:
        with self._lock:
            items = list(self._actors.values())
            if gender is not None:
                items = [a for a in items if a.gender == gender or a.gender == VoiceGender.ANY]
            if age_range is not None:
                items = [a for a in items if a.age_range == age_range]
            if language is not None:
                items = [a for a in items if language in a.languages]
            return items

    def delete_actor(self, actor_id: str) -> bool:
        with self._lock:
            if actor_id not in self._actors:
                return False
            del self._actors[actor_id]
            self._emit(DirectorEventKind.ACTOR_REMOVED, {"actor_id": actor_id})
            return True

    # --- Character Management ---

    def create_character(self, name: str, game_title: str = "",
                         description: str = "", gender: VoiceGender = VoiceGender.ANY,
                         age_range: VoiceAgeRange = VoiceAgeRange.ADULT,
                         accent_requirement: str = "",
                         vocal_traits: List[str] = None,
                         personality: str = "", project_id: str = "") -> CharacterRole:
        with self._lock:
            char = CharacterRole(
                character_id=_new_id("chr"),
                name=name,
                game_title=game_title,
                description=description,
                gender=gender,
                age_range=age_range,
                accent_requirement=accent_requirement,
                vocal_traits=vocal_traits or [],
                personality=personality,
                project_id=project_id,
            )
            self._characters[char.character_id] = char
            _evict_fifo_dict(self._characters, _MAX_CHARACTERS)
            self._emit(DirectorEventKind.CHARACTER_CREATED, {"character_id": char.character_id, "name": name})
            return char

    def update_character(self, character_id: str, updates: Dict[str, Any]) -> Optional[CharacterRole]:
        with self._lock:
            char = self._characters.get(character_id)
            if char is None:
                return None
            for k, v in updates.items():
                if k == "gender" and isinstance(v, str):
                    try:
                        v = VoiceGender(v)
                    except ValueError:
                        continue
                elif k == "age_range" and isinstance(v, str):
                    try:
                        v = VoiceAgeRange(v)
                    except ValueError:
                        continue
                if hasattr(char, k) and k not in ("character_id", "created_at"):
                    setattr(char, k, v)
            char.updated_at = _now()
            self._emit(DirectorEventKind.CHARACTER_UPDATED, {"character_id": character_id})
            return char

    def get_character(self, character_id: str) -> Optional[CharacterRole]:
        with self._lock:
            return self._characters.get(character_id)

    def list_characters(self, project_id: str = None) -> List[CharacterRole]:
        with self._lock:
            items = list(self._characters.values())
            if project_id is not None:
                items = [c for c in items if c.project_id == project_id]
            return items

    # --- Casting ---

    def cast_actor(self, character_id: str, actor_id: str,
                   project_id: str = "", match_score: float = 0.0,
                   audition_notes: str = "", director_notes: str = "",
                   is_primary: bool = True, is_backup: bool = False) -> Optional[CastingSession]:
        with self._lock:
            if character_id not in self._characters or actor_id not in self._actors:
                return None
            casting = CastingSession(
                casting_id=_new_id("cst"),
                character_id=character_id,
                actor_id=actor_id,
                project_id=project_id,
                match_score=match_score,
                audition_notes=audition_notes,
                director_notes=director_notes,
                is_primary=is_primary,
                is_backup=is_backup,
            )
            self._castings[casting.casting_id] = casting
            if is_primary:
                char = self._characters[character_id]
                char.cast_actor_id = actor_id
                char.updated_at = _now()
            self._emit(DirectorEventKind.ACTOR_CAST, {
                "character_id": character_id, "actor_id": actor_id,
            })
            return casting

    def uncast_actor(self, character_id: str) -> bool:
        with self._lock:
            char = self._characters.get(character_id)
            if char is None:
                return False
            char.cast_actor_id = ""
            char.updated_at = _now()
            for casting in self._castings.values():
                if casting.character_id == character_id:
                    casting.is_primary = False
            self._emit(DirectorEventKind.ACTOR_UNCAST, {"character_id": character_id})
            return True

    def get_casting(self, character_id: str) -> Optional[CastingSession]:
        with self._lock:
            for c in self._castings.values():
                if c.character_id == character_id and c.is_primary:
                    return c
            return None

    def list_castings(self, project_id: str = None) -> List[CastingSession]:
        with self._lock:
            items = list(self._castings.values())
            if project_id is not None:
                items = [c for c in items if c.project_id == project_id]
            return items

    # --- Line Management ---

    def create_line(self, character_id: str, text: str, project_id: str = "",
                    context: str = "", emotion: EmotionType = EmotionType.NEUTRAL,
                    intensity: float = 0.5, pacing: str = "normal",
                    pronunciation_guide: str = "",
                    estimated_duration_seconds: float = 0.0,
                    scene_reference: str = "", sequence_order: int = 0) -> Optional[VoiceLine]:
        with self._lock:
            if character_id not in self._characters:
                return None
            line = VoiceLine(
                line_id=_new_id("vln"),
                character_id=character_id,
                project_id=project_id,
                text=text,
                context=context,
                emotion=emotion,
                intensity=intensity,
                pacing=pacing,
                pronunciation_guide=pronunciation_guide,
                estimated_duration_seconds=estimated_duration_seconds,
                scene_reference=scene_reference,
                sequence_order=sequence_order,
            )
            self._lines[line.line_id] = line
            _evict_fifo_dict(self._lines, _MAX_LINES)
            char = self._characters[character_id]
            char.total_lines += 1
            self._emit(DirectorEventKind.LINE_CREATED, {"line_id": line.line_id})
            return line

    def update_line(self, line_id: str, updates: Dict[str, Any]) -> Optional[VoiceLine]:
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return None
            for k, v in updates.items():
                if k == "emotion" and isinstance(v, str):
                    try:
                        v = EmotionType(v)
                    except ValueError:
                        continue
                if hasattr(line, k) and k not in ("line_id", "created_at"):
                    setattr(line, k, v)
            line.updated_at = _now()
            self._emit(DirectorEventKind.LINE_UPDATED, {"line_id": line_id})
            return line

    def get_line(self, line_id: str) -> Optional[VoiceLine]:
        with self._lock:
            return self._lines.get(line_id)

    def list_lines(self, character_id: str = None, project_id: str = None,
                   status: str = None, limit: int = 100) -> List[VoiceLine]:
        with self._lock:
            items = list(self._lines.values())
            if character_id is not None:
                items = [l for l in items if l.character_id == character_id]
            if project_id is not None:
                items = [l for l in items if l.project_id == project_id]
            if status is not None:
                items = [l for l in items if l.status == status]
            items.sort(key=lambda x: x.sequence_order)
            return items[:limit]

    # --- Delivery Direction ---

    def add_direction(self, line_id: str, emotion_cue: str = "",
                      emphasis_words: List[str] = None,
                      pacing_instruction: str = "",
                      breathing_instruction: str = "",
                      pitch_guidance: str = "",
                      volume_level: str = "normal",
                      additional_notes: str = "") -> Optional[DeliveryDirection]:
        with self._lock:
            if line_id not in self._lines:
                return None
            existing = [d for d in self._directions.values() if d.line_id == line_id]
            if len(existing) >= _MAX_DIRECTIONS_PER_LINE:
                return None
            direction = DeliveryDirection(
                direction_id=_new_id("dir"),
                line_id=line_id,
                emotion_cue=emotion_cue,
                emphasis_words=emphasis_words or [],
                pacing_instruction=pacing_instruction,
                breathing_instruction=breathing_instruction,
                pitch_guidance=pitch_guidance,
                volume_level=volume_level,
                additional_notes=additional_notes,
            )
            self._directions[direction.direction_id] = direction
            self._emit(DirectorEventKind.DIRECTION_ADDED, {"direction_id": direction.direction_id, "line_id": line_id})
            return direction

    def get_direction(self, line_id: str) -> Optional[DeliveryDirection]:
        with self._lock:
            for d in self._directions.values():
                if d.line_id == line_id:
                    return d
            return None

    def list_directions(self, line_id: str = None) -> List[DeliveryDirection]:
        with self._lock:
            items = list(self._directions.values())
            if line_id is not None:
                items = [d for d in items if d.line_id == line_id]
            return items

    # --- Take Management ---

    def record_take(self, line_id: str, actor_id: str, session_id: str = "",
                    audio_file: str = "", duration_seconds: float = 0.0,
                    quality_score: float = 0.0, emotion_accuracy: float = 0.0,
                    pacing_accuracy: float = 0.0, clarity: float = 0.0,
                    energy: float = 0.0, notes: str = "") -> Optional[RecordingTake]:
        with self._lock:
            if line_id not in self._lines or actor_id not in self._actors:
                return None
            existing = [t for t in self._takes.values() if t.line_id == line_id]
            if len(existing) >= _MAX_TAKES_PER_LINE:
                return None
            take = RecordingTake(
                take_id=_new_id("tak"),
                line_id=line_id,
                actor_id=actor_id,
                session_id=session_id,
                audio_file=audio_file,
                duration_seconds=duration_seconds,
                quality_score=quality_score,
                emotion_accuracy=emotion_accuracy,
                pacing_accuracy=pacing_accuracy,
                clarity=clarity,
                energy=energy,
                status=TakeStatus.RECORDED,
                notes=notes,
            )
            self._takes[take.take_id] = take
            _evict_fifo_dict(self._takes, _MAX_TAKES)
            actor = self._actors[actor_id]
            actor.total_lines_recorded += 1
            if actor.total_lines_recorded > 0:
                actor.average_take_quality = (
                    (actor.average_take_quality * (actor.total_lines_recorded - 1) + quality_score)
                    / actor.total_lines_recorded
                )
            self._emit(DirectorEventKind.TAKE_RECORDED, {"take_id": take.take_id, "line_id": line_id})
            return take

    def review_take(self, take_id: str, reviewer: str = "Director",
                    verdict: ReviewVerdict = ReviewVerdict.CONDITIONAL,
                    score: float = 0.0, comment: str = "") -> Optional[RecordingTake]:
        with self._lock:
            take = self._takes.get(take_id)
            if take is None:
                return None
            take.status = TakeStatus.REVIEWED
            take.reviewed_at = _now()
            take.reviewed_by = reviewer
            if score > 0:
                take.quality_score = score
            self._emit(DirectorEventKind.TAKE_REVIEWED, {"take_id": take_id, "verdict": verdict.value})
            return take

    def select_take(self, take_id: str) -> Optional[RecordingTake]:
        with self._lock:
            take = self._takes.get(take_id)
            if take is None:
                return None
            line = self._lines.get(take.line_id)
            if line is None:
                return None
            for t in self._takes.values():
                if t.line_id == take.line_id and t.take_id != take_id:
                    if t.status == TakeStatus.SELECTED:
                        t.status = TakeStatus.REVIEWED
            take.status = TakeStatus.SELECTED
            line.selected_take_id = take_id
            line.status = "selected"
            line.updated_at = _now()
            self._emit(DirectorEventKind.TAKE_SELECTED, {"take_id": take_id, "line_id": take.line_id})
            return take

    def list_takes(self, line_id: str = None, actor_id: str = None,
                   status: TakeStatus = None, limit: int = 100) -> List[RecordingTake]:
        with self._lock:
            items = list(self._takes.values())
            if line_id is not None:
                items = [t for t in items if t.line_id == line_id]
            if actor_id is not None:
                items = [t for t in items if t.actor_id == actor_id]
            if status is not None:
                items = [t for t in items if t.status == status]
            return items[:limit]

    # --- Lip Sync ---

    def add_lip_sync(self, line_id: str, viseme_sequence: List[Dict[str, Any]] = None,
                     phoneme_timings: List[Dict[str, Any]] = None,
                     total_duration: float = 0.0,
                     alignment_score: float = 0.0) -> Optional[LipSyncMarker]:
        with self._lock:
            if line_id not in self._lines:
                return None
            existing = [m for m in self._lip_sync.values() if m.line_id == line_id]
            if len(existing) >= _MAX_LIP_SYNC_PER_LINE:
                return None
            marker = LipSyncMarker(
                marker_id=_new_id("lsn"),
                line_id=line_id,
                viseme_sequence=viseme_sequence or [],
                phoneme_timings=phoneme_timings or [],
                total_duration=total_duration,
                alignment_score=alignment_score,
                status=LipSyncStatus.PENDING if alignment_score < 0.8 else LipSyncStatus.ALIGNED,
            )
            self._lip_sync[marker.marker_id] = marker
            self._emit(DirectorEventKind.LIP_SYNC_ADDED, {"marker_id": marker.marker_id, "line_id": line_id})
            return marker

    def update_lip_sync(self, marker_id: str, updates: Dict[str, Any]) -> Optional[LipSyncMarker]:
        with self._lock:
            marker = self._lip_sync.get(marker_id)
            if marker is None:
                return None
            for k, v in updates.items():
                if k == "status" and isinstance(v, str):
                    try:
                        v = LipSyncStatus(v)
                    except ValueError:
                        continue
                if hasattr(marker, k) and k not in ("marker_id", "created_at"):
                    setattr(marker, k, v)
            marker.updated_at = _now()
            self._emit(DirectorEventKind.LIP_SYNC_UPDATED, {"marker_id": marker_id})
            return marker

    def get_lip_sync(self, line_id: str) -> Optional[LipSyncMarker]:
        with self._lock:
            for m in self._lip_sync.values():
                if m.line_id == line_id:
                    return m
            return None

    def list_lip_sync(self, line_id: str = None, status: LipSyncStatus = None) -> List[LipSyncMarker]:
        with self._lock:
            items = list(self._lip_sync.values())
            if line_id is not None:
                items = [m for m in items if m.line_id == line_id]
            if status is not None:
                items = [m for m in items if m.status == status]
            return items

    # --- Session Management ---

    def create_session(self, project_id: str, actor_id: str, name: str = "",
                       scheduled_start: str = "", scheduled_end: str = "",
                       studio_location: str = "", notes: str = "",
                       lines_planned: int = 0) -> Optional[RecordingSession]:
        with self._lock:
            if actor_id not in self._actors:
                return None
            session = RecordingSession(
                session_id=_new_id("ses"),
                project_id=project_id,
                actor_id=actor_id,
                name=name,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                studio_location=studio_location,
                notes=notes,
                lines_planned=lines_planned,
            )
            self._sessions[session.session_id] = session
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            self._emit(DirectorEventKind.SESSION_CREATED, {"session_id": session.session_id})
            return session

    def start_session(self, session_id: str) -> Optional[RecordingSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = SessionStatus.IN_PROGRESS
            session.actual_start = _now()
            session.updated_at = _now()
            self._emit(DirectorEventKind.SESSION_STARTED, {"session_id": session_id})
            return session

    def complete_session(self, session_id: str) -> Optional[RecordingSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = SessionStatus.COMPLETED
            session.actual_end = _now()
            session.updated_at = _now()
            takes_in_session = [t for t in self._takes.values() if t.session_id == session_id]
            session.total_takes = len(takes_in_session)
            session.lines_completed = len(set(t.line_id for t in takes_in_session))
            self._emit(DirectorEventKind.SESSION_COMPLETED, {"session_id": session_id})
            return session

    def get_session(self, session_id: str) -> Optional[RecordingSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, project_id: str = None, actor_id: str = None,
                      status: SessionStatus = None) -> List[RecordingSession]:
        with self._lock:
            items = list(self._sessions.values())
            if project_id is not None:
                items = [s for s in items if s.project_id == project_id]
            if actor_id is not None:
                items = [s for s in items if s.actor_id == actor_id]
            if status is not None:
                items = [s for s in items if s.status == status]
            return items

    # --- Project Management ---

    def create_project(self, name: str, game_title: str = "",
                       build_version: str = "", description: str = "",
                       budget: float = 0.0, start_date: str = "",
                       target_completion: str = "") -> VoiceoverProject:
        with self._lock:
            project = VoiceoverProject(
                project_id=_new_id("prj"),
                name=name,
                game_title=game_title,
                build_version=build_version,
                description=description,
                budget=budget,
                start_date=start_date,
                target_completion=target_completion,
            )
            self._projects[project.project_id] = project
            _evict_fifo_dict(self._projects, _MAX_PROJECTS)
            self._emit(DirectorEventKind.PROJECT_CREATED, {"project_id": project.project_id, "name": name})
            return project

    def update_project(self, project_id: str, updates: Dict[str, Any]) -> Optional[VoiceoverProject]:
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return None
            for k, v in updates.items():
                if k == "status" and isinstance(v, str):
                    try:
                        v = ProjectStatus(v)
                    except ValueError:
                        continue
                if hasattr(project, k) and k not in ("project_id", "created_at"):
                    setattr(project, k, v)
            project.updated_at = _now()
            self._emit(DirectorEventKind.PROJECT_UPDATED, {"project_id": project_id})
            return project

    def get_project(self, project_id: str) -> Optional[VoiceoverProject]:
        with self._lock:
            return self._projects.get(project_id)

    def list_projects(self, status: ProjectStatus = None) -> List[VoiceoverProject]:
        with self._lock:
            items = list(self._projects.values())
            if status is not None:
                items = [p for p in items if p.status == status]
            return items

    # --- Reporting ---

    def generate_report(self, project_id: str, title: str = "Voiceover Production Report") -> Optional[DirectorReport]:
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return None
            lines = [l for l in self._lines.values() if l.project_id == project_id]
            takes = [t for t in self._takes.values() if any(t.line_id == l.line_id for l in lines)]
            selected = [l for l in lines if l.status == "selected"]
            recorded = [l for l in lines if l.status in ("recorded", "reviewed", "selected")]
            characters = [c for c in self._characters.values() if c.project_id == project_id]
            sessions = [s for s in self._sessions.values() if s.project_id == project_id]
            avg_quality = sum(t.quality_score for t in takes) / len(takes) if takes else 0.0
            coverage = (len(recorded) / len(lines) * 100) if lines else 0.0

            char_breakdown = []
            for char in characters:
                char_lines = [l for l in lines if l.character_id == char.character_id]
                char_selected = [l for l in char_lines if l.status == "selected"]
                char_breakdown.append({
                    "character_id": char.character_id,
                    "name": char.name,
                    "total_lines": len(char_lines),
                    "selected_lines": len(char_selected),
                    "cast_actor_id": char.cast_actor_id,
                })

            recommendations: List[str] = []
            if coverage < 50:
                recommendations.append("Recording coverage is below 50% - prioritize remaining lines.")
            if avg_quality < 0.7 and takes:
                recommendations.append("Average take quality is below threshold - consider re-recording sessions.")
            uncast = [c for c in characters if not c.cast_actor_id]
            if uncast:
                recommendations.append(f"{len(uncast)} characters are uncast - complete casting before recording.")
            pending_lines = [l for l in lines if l.status == "pending"]
            if pending_lines:
                recommendations.append(f"{len(pending_lines)} lines are pending recording.")

            report = DirectorReport(
                report_id=_new_id("rpt"),
                project_id=project_id,
                title=title,
                summary=f"Project '{project.name}' - {coverage:.1f}% coverage, {len(selected)}/{len(lines)} lines selected.",
                coverage_percentage=round(coverage, 2),
                total_lines=len(lines),
                recorded_lines=len(recorded),
                selected_lines=len(selected),
                pending_lines=len(pending_lines),
                total_takes=len(takes),
                average_quality=round(avg_quality, 4),
                total_actors=len(set(t.actor_id for t in takes)),
                total_sessions=len(sessions),
                budget_used=project.spent,
                character_breakdown=char_breakdown,
                recommendations=recommendations,
            )
            self._reports[report.report_id] = report
            _evict_fifo_dict(self._reports, _MAX_REPORTS)
            self._emit(DirectorEventKind.REPORT_GENERATED, {"report_id": report.report_id, "project_id": project_id})
            return report

    def get_report(self, report_id: str) -> Optional[DirectorReport]:
        with self._lock:
            return self._reports.get(report_id)

    def list_reports(self, project_id: str = None, limit: int = 50) -> List[DirectorReport]:
        with self._lock:
            items = list(self._reports.values())
            if project_id is not None:
                items = [r for r in items if r.project_id == project_id]
            return items[:limit]

    # --- Observability ---

    def list_events(self, limit: int = 100) -> List[DirectorEvent]:
        with self._lock:
            return list(self._events[:limit])

    def get_stats(self) -> DirectorStats:
        with self._lock:
            return DirectorStats(
                total_actors=len(self._actors),
                total_characters=len(self._characters),
                total_lines=len(self._lines),
                total_takes=len(self._takes),
                total_sessions=len(self._sessions),
                total_projects=len(self._projects),
                total_reports=len(self._reports),
                total_castings=len(self._castings),
                total_lip_sync_markers=len(self._lip_sync),
                total_directions=len(self._directions),
                total_events=len(self._events),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_actors": len(self._actors),
                "total_characters": len(self._characters),
                "total_lines": len(self._lines),
                "total_takes": len(self._takes),
                "total_sessions": len(self._sessions),
                "total_projects": len(self._projects),
                "total_reports": len(self._reports),
                "total_castings": len(self._castings),
                "total_lip_sync_markers": len(self._lip_sync),
                "total_directions": len(self._directions),
                "total_events": len(self._events),
                "capacities": {
                    "max_actors": _MAX_ACTORS,
                    "max_characters": _MAX_CHARACTERS,
                    "max_lines": _MAX_LINES,
                    "max_takes": _MAX_TAKES,
                    "max_sessions": _MAX_SESSIONS,
                    "max_projects": _MAX_PROJECTS,
                    "max_reports": _MAX_REPORTS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> DirectorSnapshot:
        with self._lock:
            return DirectorSnapshot(
                actors=[a.to_dict() for a in list(self._actors.values())[:50]],
                characters=[c.to_dict() for c in list(self._characters.values())[:50]],
                lines=[l.to_dict() for l in list(self._lines.values())[:100]],
                takes=[t.to_dict() for t in list(self._takes.values())[:100]],
                sessions=[s.to_dict() for s in list(self._sessions.values())[:50]],
                projects=[p.to_dict() for p in list(self._projects.values())[:50]],
                castings=[c.to_dict() for c in list(self._castings.values())[:50]],
                lip_sync_markers=[m.to_dict() for m in list(self._lip_sync.values())[:50]],
                directions=[d.to_dict() for d in list(self._directions.values())[:50]],
                reports=[r.to_dict() for r in list(self._reports.values())[:20]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._actors.clear()
            self._characters.clear()
            self._lines.clear()
            self._directions.clear()
            self._takes.clear()
            self._lip_sync.clear()
            self._castings.clear()
            self._sessions.clear()
            self._projects.clear()
            self._reports.clear()
            self._events.clear()
            self._seed_data()

    def _seed_data(self) -> None:
        # Seed actors
        a1 = self.register_actor(
            name="Elena Vance", gender=VoiceGender.FEMALE,
            age_range=VoiceAgeRange.YOUNG_ADULT,
            vocal_range_low="G3", vocal_range_high="E5",
            accent="North American", languages=["English"],
            tags=["protagonist", "narrator"], bio="Classical training with game VO experience.",
            rate_per_hour=250.0,
        )
        a2 = self.register_actor(
            name="Marcus Cole", gender=VoiceGender.MALE,
            age_range=VoiceAgeRange.MIDDLE_AGED,
            vocal_range_low="C2", vocal_range_high="G4",
            accent="British RP", languages=["English"],
            tags=["antagonist", "deep_voice"], bio="Theatre veteran with baritone voice.",
            rate_per_hour=300.0,
        )
        a3 = self.register_actor(
            name="Yuki Tanaka", gender=VoiceGender.FEMALE,
            age_range=VoiceAgeRange.ADULT,
            vocal_range_low="A3", vocal_range_high="C5",
            accent="Neutral American", languages=["English", "Japanese"],
            tags=["supporting", "versatile"], bio="Bilingual actor with anime and game credits.",
            rate_per_hour=200.0,
        )

        # Seed project
        p1 = self.create_project(
            name="Crystal Realm VO", game_title="Crystal Realm",
            build_version="1.2.0", description="Full voiceover production for main story campaign.",
            budget=50000.0, start_date="2026-07-01", target_completion="2026-09-30",
        )
        p1.status = ProjectStatus.RECORDING
        p1.updated_at = _now()

        # Seed characters
        c1 = self.create_character(
            name="Aria", game_title="Crystal Realm",
            description="Brave protagonist on a quest to restore the shattered crystals.",
            gender=VoiceGender.FEMALE, age_range=VoiceAgeRange.YOUNG_ADULT,
            accent_requirement="North American",
            vocal_traits=["bright", "energetic", "empathetic"],
            personality="Determined, compassionate, occasionally reckless.",
            project_id=p1.project_id,
        )
        c2 = self.create_character(
            name="Lord Malachar", game_title="Crystal Realm",
            description="The antagonist seeking to harness the crystals' power.",
            gender=VoiceGender.MALE, age_range=VoiceAgeRange.MIDDLE_AGED,
            accent_requirement="British RP",
            vocal_traits=["deep", "commanding", "sinister"],
            personality="Calculating, ruthless, charismatic.",
            project_id=p1.project_id,
        )
        c3 = self.create_character(
            name="Sage Mira", game_title="Crystal Realm",
            description="Wise mentor who guides Aria on her journey.",
            gender=VoiceGender.FEMALE, age_range=VoiceAgeRange.ADULT,
            accent_requirement="Neutral",
            vocal_traits=["calm", "warm", "measured"],
            personality="Patient, knowledgeable, mysterious.",
            project_id=p1.project_id,
        )

        # Cast actors
        self.cast_actor(c1.character_id, a1.actor_id, p1.project_id, match_score=0.95,
                        director_notes="Perfect vocal match for protagonist.")
        self.cast_actor(c2.character_id, a2.actor_id, p1.project_id, match_score=0.92,
                        director_notes="Ideal baritone for antagonist.")
        self.cast_actor(c3.character_id, a3.actor_id, p1.project_id, match_score=0.88,
                        director_notes="Strong versatility for mentor role.")

        # Seed lines
        l1 = self.create_line(c1.character_id,
                              "The crystals... I can feel them calling to me. I won't let them down.",
                              project_id=p1.project_id, context="Opening monologue",
                              emotion=EmotionType.TENDER, intensity=0.7, pacing="slow",
                              scene_reference="Act 1 - Scene 1", sequence_order=1,
                              estimated_duration_seconds=4.5)
        l2 = self.create_line(c1.character_id,
                              "You'll never get away with this, Malachar!",
                              project_id=p1.project_id, context="Confrontation",
                              emotion=EmotionType.ANGRY, intensity=0.9, pacing="fast",
                              scene_reference="Act 2 - Scene 5", sequence_order=2,
                              estimated_duration_seconds=2.0)
        l3 = self.create_line(c2.character_id,
                              "Foolish child. Power belongs to those willing to seize it.",
                              project_id=p1.project_id, context="Antagonist speech",
                              emotion=EmotionType.MENACING, intensity=0.8, pacing="measured",
                              scene_reference="Act 2 - Scene 5", sequence_order=3,
                              estimated_duration_seconds=3.5)
        l4 = self.create_line(c3.character_id,
                              "Trust in the light within you, Aria. It has never failed you before.",
                              project_id=p1.project_id, context="Mentor guidance",
                              emotion=EmotionType.CALM, intensity=0.4, pacing="slow",
                              scene_reference="Act 1 - Scene 3", sequence_order=4,
                              estimated_duration_seconds=4.0)

        # Seed directions
        self.add_direction(l1.line_id, emotion_cue="whispered determination",
                           emphasis_words=["crystals", "calling"],
                           pacing_instruction="Slow build, accelerate at end",
                           breathing_instruction="Deep breath before 'calling'",
                           pitch_guidance="Start low, rise on 'calling'",
                           volume_level="soft")
        self.add_direction(l3.line_id, emotion_cue="cold authority",
                           emphasis_words=["Foolish", "seize"],
                           pacing_instruction="Deliberate pauses",
                           breathing_instruction="Steady, controlled",
                           pitch_guidance="Low register, dip on 'seize'",
                           volume_level="normal")

        # Seed takes
        t1 = self.record_take(l1.line_id, a1.actor_id, quality_score=0.92,
                              emotion_accuracy=0.95, pacing_accuracy=0.90,
                              clarity=0.93, energy=0.88)
        t2 = self.record_take(l1.line_id, a1.actor_id, quality_score=0.85,
                              emotion_accuracy=0.80, pacing_accuracy=0.85,
                              clarity=0.90, energy=0.82)
        t3 = self.record_take(l3.line_id, a2.actor_id, quality_score=0.89,
                              emotion_accuracy=0.92, pacing_accuracy=0.85,
                              clarity=0.91, energy=0.87)

        # Select best takes
        self.select_take(t1.take_id)
        self.select_take(t3.take_id)

        # Seed lip sync
        self.add_lip_sync(l1.line_id,
                          viseme_sequence=[{"t": 0.0, "v": "PP"}, {"t": 0.3, "v": "AA"}],
                          phoneme_timings=[{"t": 0.0, "p": "T"}, {"t": 0.1, "p": "AH"}],
                          total_duration=4.5, alignment_score=0.94)
        self.add_lip_sync(l3.line_id,
                          viseme_sequence=[{"t": 0.0, "v": "FF"}, {"t": 0.4, "v": "UH"}],
                          phoneme_timings=[{"t": 0.0, "p": "F"}, {"t": 0.2, "p": "UH"}],
                          total_duration=3.5, alignment_score=0.88)

        # Seed session
        s1 = self.create_session(p1.project_id, a1.actor_id,
                                 name="Aria Recording Session 1",
                                 scheduled_start="2026-07-05T10:00:00Z",
                                 scheduled_end="2026-07-05T14:00:00Z",
                                 studio_location="Studio A", lines_planned=4)
        s1.status = SessionStatus.COMPLETED
        s1.actual_start = "2026-07-05T10:05:00Z"
        s1.actual_end = "2026-07-05T13:45:00Z"
        s1.lines_completed = 2
        s1.total_takes = 2
        s1.updated_at = _now()

        # Update project stats
        p1.total_characters = 3
        p1.total_lines = 4
        p1.recorded_lines = 3
        p1.selected_lines = 2
        p1.spent = 1500.0
        p1.updated_at = _now()


def get_voice_acting_director() -> VoiceActingDirector:
    """Factory function to get the singleton VoiceActingDirector instance."""
    return VoiceActingDirector.get_instance()
