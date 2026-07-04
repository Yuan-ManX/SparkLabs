"""
SparkLabs Engine - Procedural Music Composer

Composes original music procedurally using music-theoretic primitives.
Supports multiple genres, mood-to-music mapping, motif development,
harmonic progression, and real-time adaptation to gameplay events.

Architecture:
  ProceduralMusicComposer (singleton)
    |-- Composition, Track, Measure, Note, ChordProgression, Motif,
    |   MoodMapping, CompositionTemplate, AdaptationRule,
    |   MusicSnapshot, MusicEvent
    |-- Genre, ScaleType, MoodState, TrackRole, CompositionStatus,
        AdaptationTrigger, MusicEventKind

Core Capabilities:
  - create_composition / update_composition / get_composition /
    list_compositions / delete_composition: lifecycle management.
  - add_track / remove_track / update_track: multi-track composition
    with roles (MELODY, HARMONY, BASS, PERCUSSION, PAD, COUNTER_MELODY).
  - add_measure / remove_measure / reorder_measures: build the
    timeline measure by measure.
  - compose_motif / develop_motif: generate a short melodic motif and
    apply variation techniques (sequence, inversion, retrograde,
    augmentation, diminution).
  - set_progression / get_progression: harmonic chord progressions
    with roman-numeral labels.
  - map_mood / get_mood_mapping: translate gameplay moods into musical
    parameters (tempo, key, dynamics, density).
  - set_template / list_templates: reusable composition templates.
  - create_adaptation_rule / evaluate_adaptation: real-time music
    adaptation based on gameplay triggers (COMBAT, EXPLORATION, etc.).
  - export_composition: serialize a composition into a playable note
    sequence with timing, velocity, and instrument assignments.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and lifecycle management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ProceduralMusicComposer.get_instance` or the module-level
:func:`get_procedural_music_composer` factory.
"""

from __future__ import annotations

import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_COMPOSITIONS: int = 200
_MAX_TRACKS_PER_COMPOSITION: int = 16
_MAX_MEASURES_PER_TRACK: int = 256
_MAX_MOTIFS: int = 500
_MAX_TEMPLATES: int = 100
_MAX_ADAPTATION_RULES: int = 100
_MAX_MAPPINGS: int = 50
_MAX_EVENTS: int = 3000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload."""
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
    """Convert a dataclass instance to a plain dictionary."""
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
# Music Theory Constants
# ---------------------------------------------------------------------------

# Note names in chromatic scale
_NOTE_NAMES: List[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Scale intervals (semitones from root)
_SCALE_INTERVALS: Dict[str, List[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
}

# Common chord progressions (roman numeral scale degrees, 1-indexed)
_PROGRESSIONS: Dict[str, List[List[int]]] = {
    "I-IV-V-I": [[1, 3, 5], [4, 6, 1], [5, 7, 2], [1, 3, 5]],
    "I-V-vi-IV": [[1, 3, 5], [5, 7, 2], [6, 1, 3], [4, 6, 1]],
    "ii-V-I": [[2, 4, 6], [5, 7, 2], [1, 3, 5]],
    "vi-IV-I-V": [[6, 1, 3], [4, 6, 1], [1, 3, 5], [5, 7, 2]],
    "I-vi-IV-V": [[1, 3, 5], [6, 1, 3], [4, 6, 1], [5, 7, 2]],
    "i-iv-VII-iii": [[1, 3, 5], [4, 6, 1], [7, 2, 4], [3, 5, 7]],
}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class Genre(Enum):
    """Musical genre for composition."""
    FANTASY = "fantasy"
    COMBAT = "combat"
    AMBIENT = "ambient"
    CHIPTUNE = "chiptune"
    ORCHESTRAL = "orchestral"
    ELECTRONIC = "electronic"
    FOLK = "folk"
    HORROR = "horror"
    JAZZ = "jazz"
    ROCK = "rock"


class ScaleType(Enum):
    """Musical scale type."""
    MAJOR = "major"
    MINOR = "minor"
    HARMONIC_MINOR = "harmonic_minor"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    DORIAN = "dorian"
    MIXOLYDIAN = "mixolydian"
    LYDIAN = "lydian"
    PHRYGIAN = "phrygian"
    LOCRIAN = "locrian"
    CHROMATIC = "chromatic"


class MoodState(Enum):
    """Gameplay mood that maps to musical parameters."""
    CALM = "calm"
    TENSE = "tense"
    TRIUMPHANT = "triumphant"
    MELANCHOLY = "melancholy"
    MYSTERIOUS = "mysterious"
    ENERGETIC = "energetic"
    PEACEFUL = "peaceful"
    DREAD = "dread"
    HEROIC = "heroic"
    PLAYFUL = "playful"


class TrackRole(Enum):
    """Role of a track within a composition."""
    MELODY = "melody"
    HARMONY = "harmony"
    BASS = "bass"
    PERCUSSION = "percussion"
    PAD = "pad"
    COUNTER_MELODY = "counter_melody"
    ARPEGGIO = "arpeggio"
    DRONE = "drone"


class CompositionStatus(Enum):
    """Lifecycle status of a composition."""
    DRAFT = "draft"
    COMPOSING = "composing"
    COMPLETE = "complete"
    EXPORTED = "exported"
    ARCHIVED = "archived"


class AdaptationTrigger(Enum):
    """Gameplay event that triggers musical adaptation."""
    COMBAT_START = "combat_start"
    COMBAT_END = "combat_end"
    LEVEL_UP = "level_up"
    LOW_HEALTH = "low_health"
    BOSS_ENCOUNTER = "boss_encounter"
    DISCOVERY = "discovery"
    DEATH = "death"
    VICTORY = "victory"
    DIALOGUE = "dialogue"
    CUTSCENE = "cutscene"
    IDLE = "idle"
    EXPLORE = "explore"


class MusicEventKind(Enum):
    """Audit event kinds emitted by the music composer."""
    COMPOSITION_CREATED = "composition_created"
    COMPOSITION_UPDATED = "composition_updated"
    COMPOSITION_DELETED = "composition_deleted"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"
    MEASURE_ADDED = "measure_added"
    MOTIF_COMPOSED = "motif_composed"
    MOTIF_DEVELOPED = "motif_developed"
    PROGRESSION_SET = "progression_set"
    MOOD_MAPPED = "mood_mapped"
    TEMPLATE_CREATED = "template_created"
    ADAPTATION_RULE_CREATED = "adaptation_rule_created"
    ADAPTATION_TRIGGERED = "adaptation_triggered"
    COMPOSITION_EXPORTED = "composition_exported"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Note:
    """A single musical note."""
    pitch: int  # MIDI note number (0-127)
    duration: float  # in beats
    velocity: int = 80  # 0-127
    offset: float = 0.0  # beat offset from measure start

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    @property
    def name(self) -> str:
        """Human-readable note name."""
        octave = self.pitch // 12 - 1
        name = _NOTE_NAMES[self.pitch % 12]
        return f"{name}{octave}"


@dataclass
class Measure:
    """A measure containing notes."""
    measure_id: str
    time_signature: Tuple[int, int] = (4, 4)
    notes: List[Note] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "measure_id": self.measure_id,
            "time_signature": list(self.time_signature),
            "notes": [n.to_dict() for n in self.notes],
        }


@dataclass
class Track:
    """A musical track within a composition."""
    track_id: str
    name: str
    role: TrackRole
    instrument: str = "piano"
    volume: float = 0.8
    muted: bool = False
    measures: List[Measure] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChordProgression:
    """A harmonic chord progression."""
    progression_id: str
    name: str
    key_root: int  # 0=C, 1=C#, ...
    scale: ScaleType
    chords: List[List[int]]  # list of scale-degree triads [1,3,5]
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Motif:
    """A short melodic motif."""
    motif_id: str
    name: str
    notes: List[Note]
    key_root: int = 0
    scale: ScaleType = ScaleType.MAJOR
    development_history: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MoodMapping:
    """Maps a gameplay mood to musical parameters."""
    mapping_id: str
    mood: MoodState
    tempo_bpm: int
    key_root: int
    scale: ScaleType
    dynamics: float  # 0.0-1.0
    density: float  # 0.0-1.0, note density
    genre: Genre
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompositionTemplate:
    """A reusable composition template."""
    template_id: str
    name: str
    genre: Genre
    default_tempo: int
    default_key: int
    default_scale: ScaleType
    track_roles: List[TrackRole]
    progression_name: str
    description: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AdaptationRule:
    """A rule that adapts music based on gameplay triggers."""
    rule_id: str
    name: str
    trigger: AdaptationTrigger
    target_mood: MoodState
    transition_duration: float = 2.0  # seconds
    enabled: bool = True
    description: str = ""
    last_triggered: Optional[str] = None
    trigger_count: int = 0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Composition:
    """A complete musical composition."""
    composition_id: str
    name: str
    genre: Genre
    tempo_bpm: int = 120
    key_root: int = 0  # 0=C
    scale: ScaleType = ScaleType.MAJOR
    tracks: List[Track] = field(default_factory=list)
    progression: Optional[ChordProgression] = None
    motifs: List[Motif] = field(default_factory=list)
    status: CompositionStatus = CompositionStatus.DRAFT
    duration_seconds: float = 0.0
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExportedSequence:
    """An exported playable note sequence."""
    export_id: str
    composition_id: str
    total_notes: int
    total_duration: float
    tracks: List[Dict[str, Any]]
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicStats:
    """Aggregate statistics."""
    total_compositions: int = 0
    total_tracks: int = 0
    total_motifs: int = 0
    total_templates: int = 0
    total_mappings: int = 0
    total_adaptation_rules: int = 0
    total_exports: int = 0
    total_events: int = 0
    composition_counter: int = 0
    track_counter: int = 0
    motif_counter: int = 0
    template_counter: int = 0
    mapping_counter: int = 0
    rule_counter: int = 0
    export_counter: int = 0
    event_counter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicSnapshot:
    """Point-in-time snapshot of the full state."""
    compositions: List[Dict[str, Any]] = field(default_factory=list)
    templates: List[Dict[str, Any]] = field(default_factory=list)
    mappings: List[Dict[str, Any]] = field(default_factory=list)
    rules: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicEvent:
    """An audit event."""
    event_id: str
    kind: MusicEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Procedural Music Composer Singleton
# ---------------------------------------------------------------------------


class ProceduralMusicComposer:
    """AI-driven procedural music composition engine.

    Composes original music using music-theoretic primitives including
    scales, chord progressions, motif development, and mood mapping.
    Supports real-time adaptation to gameplay events.
    """

    _instance: Optional["ProceduralMusicComposer"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "ProceduralMusicComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ProceduralMusicComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls()
        return cls._instance  # type: ignore[return-value]

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._inner_lock: threading.RLock = threading.RLock()
            self._compositions: Dict[str, Composition] = {}
            self._motifs: Dict[str, Motif] = {}
            self._templates: Dict[str, CompositionTemplate] = {}
            self._mappings: Dict[str, MoodMapping] = {}
            self._adaptation_rules: Dict[str, AdaptationRule] = {}
            self._exports: Dict[str, ExportedSequence] = {}
            self._events: List[MusicEvent] = []

            self._composition_counter: int = 0
            self._track_counter: int = 0
            self._motif_counter: int = 0
            self._template_counter: int = 0
            self._mapping_counter: int = 0
            self._rule_counter: int = 0
            self._export_counter: int = 0
            self._event_counter: int = 0

            self._initialized: bool = True
            self._seed()

    # -- Event Recording ---------------------------------------------------

    def _record_event(self, kind: MusicEventKind, **data: Any) -> None:
        """Record an audit event."""
        event = MusicEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # -- Music Theory Helpers ----------------------------------------------

    def _scale_notes(self, key_root: int, scale: ScaleType) -> List[int]:
        """Return the pitch classes (0-11) for a given key and scale."""
        intervals = _SCALE_INTERVALS.get(scale.value, _SCALE_INTERVALS["major"])
        return [(key_root + iv) % 12 for iv in intervals]

    def _midi_note(self, pitch_class: int, octave: int) -> int:
        """Convert a pitch class and octave to a MIDI note number."""
        return (octave + 1) * 12 + pitch_class

    def _generate_motif_notes(
        self,
        key_root: int,
        scale: ScaleType,
        num_notes: int,
        rng: random.Random,
        base_octave: int = 4,
    ) -> List[Note]:
        """Generate a random melodic motif using scale tones."""
        scale_pcs = self._scale_notes(key_root, scale)
        notes: List[Note] = []
        current_octave = base_octave
        for i in range(num_notes):
            pc = rng.choice(scale_pcs)
            # Random walk octave movement
            if rng.random() < 0.2:
                current_octave = max(2, min(6, current_octave + rng.choice([-1, 1])))
            pitch = self._midi_note(pc, current_octave)
            duration = rng.choice([0.25, 0.5, 0.5, 1.0])
            velocity = rng.randint(60, 100)
            notes.append(Note(pitch=pitch, duration=duration, velocity=velocity, offset=float(i) * 0.5))
        return notes

    def _apply_sequence(self, motif: Motif, steps: int) -> List[Note]:
        """Apply sequence (transposition) development to a motif."""
        result: List[Note] = []
        for step in range(steps):
            transpose = step * 2  # whole tone steps up
            for n in motif.notes:
                result.append(Note(
                    pitch=n.pitch + transpose,
                    duration=n.duration,
                    velocity=n.velocity,
                    offset=n.offset + step * 4.0,
                ))
        return result

    def _apply_inversion(self, motif: Motif) -> List[Note]:
        """Apply inversion (mirror around first note) to a motif."""
        if not motif.notes:
            return []
        axis = motif.notes[0].pitch
        return [Note(
            pitch=axis - (n.pitch - axis),
            duration=n.duration,
            velocity=n.velocity,
            offset=n.offset,
        ) for n in motif.notes]

    def _apply_retrograde(self, motif: Motif) -> List[Note]:
        """Apply retrograde (reverse order) to a motif."""
        return list(reversed([Note(
            pitch=n.pitch,
            duration=n.duration,
            velocity=n.velocity,
            offset=n.offset,
        ) for n in motif.notes]))

    def _apply_augmentation(self, motif: Motif, factor: float = 2.0) -> List[Note]:
        """Apply augmentation (lengthen durations) to a motif."""
        return [Note(
            pitch=n.pitch,
            duration=n.duration * factor,
            velocity=n.velocity,
            offset=n.offset * factor,
        ) for n in motif.notes]

    def _apply_diminution(self, motif: Motif, factor: float = 0.5) -> List[Note]:
        """Apply diminution (shorten durations) to a motif."""
        return [Note(
            pitch=n.pitch,
            duration=n.duration * factor,
            velocity=n.velocity,
            offset=n.offset * factor,
        ) for n in motif.notes]

    # -- Composition Management --------------------------------------------

    def create_composition(
        self,
        name: str,
        genre: Genre,
        tempo_bpm: int = 120,
        key_root: int = 0,
        scale: ScaleType = ScaleType.MAJOR,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Composition:
        """Create a new composition."""
        with self._inner_lock:
            comp = Composition(
                composition_id=_new_id("cmp"),
                name=name,
                genre=genre,
                tempo_bpm=tempo_bpm,
                key_root=key_root,
                scale=scale,
                description=description,
                tags=tags or [],
            )
            self._compositions[comp.composition_id] = comp
            self._composition_counter += 1
            _evict_fifo_dict(self._compositions, _MAX_COMPOSITIONS)
            self._record_event(
                MusicEventKind.COMPOSITION_CREATED,
                composition_id=comp.composition_id,
                name=name,
            )
            return comp

    def update_composition(
        self,
        composition_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Composition]:
        """Update a composition's mutable fields."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return None
            if "name" in updates:
                comp.name = updates["name"]
            if "tempo_bpm" in updates:
                comp.tempo_bpm = int(updates["tempo_bpm"])
            if "key_root" in updates:
                comp.key_root = int(updates["key_root"])
            if "scale" in updates:
                comp.scale = ScaleType(updates["scale"])
            if "status" in updates:
                comp.status = CompositionStatus(updates["status"])
            if "description" in updates:
                comp.description = updates["description"]
            if "tags" in updates:
                comp.tags = updates["tags"]
            comp.updated_at = _now()
            self._record_event(
                MusicEventKind.COMPOSITION_UPDATED,
                composition_id=composition_id,
            )
            return comp

    def get_composition(self, composition_id: str) -> Optional[Composition]:
        """Get a single composition by ID."""
        with self._inner_lock:
            return self._compositions.get(composition_id)

    def list_compositions(
        self,
        genre: Optional[Genre] = None,
        status: Optional[CompositionStatus] = None,
    ) -> List[Composition]:
        """List compositions, optionally filtered."""
        with self._inner_lock:
            items = list(self._compositions.values())
            if genre is not None:
                items = [c for c in items if c.genre == genre]
            if status is not None:
                items = [c for c in items if c.status == status]
            return items

    def delete_composition(self, composition_id: str) -> bool:
        """Delete a composition."""
        with self._inner_lock:
            if composition_id not in self._compositions:
                return False
            self._compositions.pop(composition_id, None)
            self._record_event(
                MusicEventKind.COMPOSITION_DELETED,
                composition_id=composition_id,
            )
            return True

    # -- Track Management --------------------------------------------------

    def add_track(
        self,
        composition_id: str,
        name: str,
        role: TrackRole,
        instrument: str = "piano",
        volume: float = 0.8,
    ) -> Optional[Track]:
        """Add a track to a composition."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return None
            if len(comp.tracks) >= _MAX_TRACKS_PER_COMPOSITION:
                return None
            track = Track(
                track_id=_new_id("trk"),
                name=name,
                role=role,
                instrument=instrument,
                volume=volume,
            )
            comp.tracks.append(track)
            self._track_counter += 1
            comp.updated_at = _now()
            self._record_event(
                MusicEventKind.TRACK_ADDED,
                composition_id=composition_id,
                track_id=track.track_id,
            )
            return track

    def remove_track(self, composition_id: str, track_id: str) -> bool:
        """Remove a track from a composition."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return False
            before = len(comp.tracks)
            comp.tracks = [t for t in comp.tracks if t.track_id != track_id]
            if len(comp.tracks) == before:
                return False
            comp.updated_at = _now()
            self._record_event(
                MusicEventKind.TRACK_REMOVED,
                composition_id=composition_id,
                track_id=track_id,
            )
            return True

    def update_track(
        self,
        composition_id: str,
        track_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Track]:
        """Update a track's mutable fields."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return None
            for track in comp.tracks:
                if track.track_id == track_id:
                    if "name" in updates:
                        track.name = updates["name"]
                    if "instrument" in updates:
                        track.instrument = updates["instrument"]
                    if "volume" in updates:
                        track.volume = float(updates["volume"])
                    if "muted" in updates:
                        track.muted = bool(updates["muted"])
                    comp.updated_at = _now()
                    return track
            return None

    # -- Measure Management ------------------------------------------------

    def add_measure(
        self,
        composition_id: str,
        track_id: str,
        time_signature: Tuple[int, int] = (4, 4),
        notes: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Measure]:
        """Add a measure to a track."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return None
            for track in comp.tracks:
                if track.track_id == track_id:
                    if len(track.measures) >= _MAX_MEASURES_PER_TRACK:
                        return None
                    measure = Measure(
                        measure_id=_new_id("msr"),
                        time_signature=time_signature,
                    )
                    if notes:
                        for n in notes:
                            measure.notes.append(Note(
                                pitch=int(n.get("pitch", 60)),
                                duration=float(n.get("duration", 1.0)),
                                velocity=int(n.get("velocity", 80)),
                                offset=float(n.get("offset", 0.0)),
                            ))
                    track.measures.append(measure)
                    comp.updated_at = _now()
                    self._record_event(
                        MusicEventKind.MEASURE_ADDED,
                        composition_id=composition_id,
                        track_id=track_id,
                        measure_id=measure.measure_id,
                    )
                    return measure
            return None

    def remove_measure(self, composition_id: str, track_id: str, measure_id: str) -> bool:
        """Remove a measure from a track."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return False
            for track in comp.tracks:
                if track.track_id == track_id:
                    before = len(track.measures)
                    track.measures = [m for m in track.measures if m.measure_id != measure_id]
                    if len(track.measures) < before:
                        comp.updated_at = _now()
                        return True
                    return False
            return False

    # -- Motif Composition -------------------------------------------------

    def compose_motif(
        self,
        name: str,
        key_root: int = 0,
        scale: ScaleType = ScaleType.MAJOR,
        num_notes: int = 8,
        seed: Optional[int] = None,
    ) -> Motif:
        """Compose a new melodic motif."""
        with self._inner_lock:
            rng = random.Random(seed) if seed is not None else random.Random()
            notes = self._generate_motif_notes(key_root, scale, num_notes, rng)
            motif = Motif(
                motif_id=_new_id("mtf"),
                name=name,
                notes=notes,
                key_root=key_root,
                scale=scale,
            )
            self._motifs[motif.motif_id] = motif
            self._motif_counter += 1
            _evict_fifo_dict(self._motifs, _MAX_MOTIFS)
            self._record_event(
                MusicEventKind.MOTIF_COMPOSED,
                motif_id=motif.motif_id,
                name=name,
            )
            return motif

    def develop_motif(
        self,
        motif_id: str,
        technique: str,
        name: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Motif]:
        """Develop a motif using a variation technique.

        Techniques: sequence, inversion, retrograde, augmentation, diminution.
        """
        with self._inner_lock:
            original = self._motifs.get(motif_id)
            if original is None:
                return None
            params = params or {}
            if technique == "sequence":
                steps = int(params.get("steps", 3))
                notes = self._apply_sequence(original, steps)
                history = f"sequence({steps})"
            elif technique == "inversion":
                notes = self._apply_inversion(original)
                history = "inversion"
            elif technique == "retrograde":
                notes = self._apply_retrograde(original)
                history = "retrograde"
            elif technique == "augmentation":
                factor = float(params.get("factor", 2.0))
                notes = self._apply_augmentation(original, factor)
                history = f"augmentation({factor})"
            elif technique == "diminution":
                factor = float(params.get("factor", 0.5))
                notes = self._apply_diminution(original, factor)
                history = f"diminution({factor})"
            else:
                return None
            new_history = original.development_history + [history]
            developed = Motif(
                motif_id=_new_id("mtf"),
                name=name or f"{original.name}_{technique}",
                notes=notes,
                key_root=original.key_root,
                scale=original.scale,
                development_history=new_history,
            )
            self._motifs[developed.motif_id] = developed
            self._motif_counter += 1
            _evict_fifo_dict(self._motifs, _MAX_MOTIFS)
            self._record_event(
                MusicEventKind.MOTIF_DEVELOPED,
                motif_id=developed.motif_id,
                source_motif_id=motif_id,
                technique=technique,
            )
            return developed

    def get_motif(self, motif_id: str) -> Optional[Motif]:
        """Get a single motif by ID."""
        with self._inner_lock:
            return self._motifs.get(motif_id)

    def list_motifs(self, limit: int = 100) -> List[Motif]:
        """List motifs."""
        with self._inner_lock:
            return list(self._motifs.values())[-limit:]

    # -- Chord Progression -------------------------------------------------

    def set_progression(
        self,
        composition_id: str,
        name: str,
        key_root: int,
        scale: ScaleType,
        progression_name: Optional[str] = None,
        custom_chords: Optional[List[List[int]]] = None,
    ) -> Optional[ChordProgression]:
        """Set the chord progression for a composition."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return None
            if custom_chords is not None:
                chords = custom_chords
            elif progression_name and progression_name in _PROGRESSIONS:
                chords = _PROGRESSIONS[progression_name]
            else:
                chords = _PROGRESSIONS["I-IV-V-I"]
            prog = ChordProgression(
                progression_id=_new_id("prg"),
                name=name,
                key_root=key_root,
                scale=scale,
                chords=chords,
            )
            comp.progression = prog
            comp.updated_at = _now()
            self._record_event(
                MusicEventKind.PROGRESSION_SET,
                composition_id=composition_id,
                progression_id=prog.progression_id,
            )
            return prog

    def get_progression(self, composition_id: str) -> Optional[ChordProgression]:
        """Get the chord progression for a composition."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return None
            return comp.progression

    # -- Mood Mapping ------------------------------------------------------

    def map_mood(
        self,
        mood: MoodState,
        tempo_bpm: int,
        key_root: int,
        scale: ScaleType,
        dynamics: float,
        density: float,
        genre: Genre,
    ) -> MoodMapping:
        """Create a mood-to-music mapping."""
        with self._inner_lock:
            mapping = MoodMapping(
                mapping_id=_new_id("map"),
                mood=mood,
                tempo_bpm=tempo_bpm,
                key_root=key_root,
                scale=scale,
                dynamics=max(0.0, min(1.0, dynamics)),
                density=max(0.0, min(1.0, density)),
                genre=genre,
            )
            self._mappings[mapping.mapping_id] = mapping
            self._mapping_counter += 1
            _evict_fifo_dict(self._mappings, _MAX_MAPPINGS)
            self._record_event(
                MusicEventKind.MOOD_MAPPED,
                mapping_id=mapping.mapping_id,
                mood=mood.value,
            )
            return mapping

    def get_mood_mapping(self, mood: MoodState) -> Optional[MoodMapping]:
        """Get the mapping for a specific mood."""
        with self._inner_lock:
            for m in self._mappings.values():
                if m.mood == mood:
                    return m
            return None

    def list_mood_mappings(self) -> List[MoodMapping]:
        """List all mood mappings."""
        with self._inner_lock:
            return list(self._mappings.values())

    # -- Templates ---------------------------------------------------------

    def create_template(
        self,
        name: str,
        genre: Genre,
        default_tempo: int,
        default_key: int,
        default_scale: ScaleType,
        track_roles: List[TrackRole],
        progression_name: str,
        description: str = "",
    ) -> CompositionTemplate:
        """Create a reusable composition template."""
        with self._inner_lock:
            template = CompositionTemplate(
                template_id=_new_id("tpl"),
                name=name,
                genre=genre,
                default_tempo=default_tempo,
                default_key=default_key,
                default_scale=default_scale,
                track_roles=track_roles,
                progression_name=progression_name,
                description=description,
            )
            self._templates[template.template_id] = template
            self._template_counter += 1
            _evict_fifo_dict(self._templates, _MAX_TEMPLATES)
            self._record_event(
                MusicEventKind.TEMPLATE_CREATED,
                template_id=template.template_id,
                name=name,
            )
            return template

    def list_templates(self, genre: Optional[Genre] = None) -> List[CompositionTemplate]:
        """List templates, optionally filtered by genre."""
        with self._inner_lock:
            items = list(self._templates.values())
            if genre is not None:
                items = [t for t in items if t.genre == genre]
            return items

    def get_template(self, template_id: str) -> Optional[CompositionTemplate]:
        """Get a single template by ID."""
        with self._inner_lock:
            return self._templates.get(template_id)

    def apply_template(
        self,
        template_id: str,
        composition_name: str,
    ) -> Optional[Composition]:
        """Create a composition from a template."""
        with self._inner_lock:
            template = self._templates.get(template_id)
            if template is None:
                return None
            comp = self.create_composition(
                name=composition_name,
                genre=template.genre,
                tempo_bpm=template.default_tempo,
                key_root=template.default_key,
                scale=template.default_scale,
                description=f"From template: {template.name}",
            )
            # Add tracks based on template roles
            for role in template.track_roles:
                self.add_track(
                    composition_id=comp.composition_id,
                    name=role.value.capitalize(),
                    role=role,
                )
            # Set progression
            self.set_progression(
                composition_id=comp.composition_id,
                name=template.progression_name,
                key_root=template.default_key,
                scale=template.default_scale,
                progression_name=template.progression_name,
            )
            return self._compositions.get(comp.composition_id)

    # -- Adaptation Rules --------------------------------------------------

    def create_adaptation_rule(
        self,
        name: str,
        trigger: AdaptationTrigger,
        target_mood: MoodState,
        transition_duration: float = 2.0,
        description: str = "",
    ) -> AdaptationRule:
        """Create a musical adaptation rule."""
        with self._inner_lock:
            rule = AdaptationRule(
                rule_id=_new_id("arul"),
                name=name,
                trigger=trigger,
                target_mood=target_mood,
                transition_duration=transition_duration,
                description=description,
            )
            self._adaptation_rules[rule.rule_id] = rule
            self._rule_counter += 1
            _evict_fifo_dict(self._adaptation_rules, _MAX_ADAPTATION_RULES)
            self._record_event(
                MusicEventKind.ADAPTATION_RULE_CREATED,
                rule_id=rule.rule_id,
                name=name,
            )
            return rule

    def list_adaptation_rules(self, enabled_only: bool = False) -> List[AdaptationRule]:
        """List adaptation rules."""
        with self._inner_lock:
            items = list(self._adaptation_rules.values())
            if enabled_only:
                items = [r for r in items if r.enabled]
            return items

    def evaluate_adaptation(
        self,
        trigger: AdaptationTrigger,
    ) -> List[AdaptationRule]:
        """Evaluate adaptation rules for a trigger. Returns triggered rules."""
        with self._inner_lock:
            triggered: List[AdaptationRule] = []
            for rule in self._adaptation_rules.values():
                if rule.enabled and rule.trigger == trigger:
                    rule.last_triggered = _now()
                    rule.trigger_count += 1
                    triggered.append(rule)
                    self._record_event(
                        MusicEventKind.ADAPTATION_TRIGGERED,
                        rule_id=rule.rule_id,
                        trigger=trigger.value,
                        target_mood=rule.target_mood.value,
                    )
            return triggered

    # -- Export ------------------------------------------------------------

    def export_composition(self, composition_id: str) -> Optional[ExportedSequence]:
        """Export a composition as a playable note sequence."""
        with self._inner_lock:
            comp = self._compositions.get(composition_id)
            if comp is None:
                return None
            total_notes = 0
            track_data: List[Dict[str, Any]] = []
            beats_per_second = comp.tempo_bpm / 60.0
            for track in comp.tracks:
                if track.muted:
                    continue
                track_notes: List[Dict[str, Any]] = []
                for measure in track.measures:
                    for note in measure.notes:
                        track_notes.append({
                            "pitch": note.pitch,
                            "note_name": note.name,
                            "start_time": round(note.offset / beats_per_second, 4),
                            "duration": round(note.duration / beats_per_second, 4),
                            "velocity": note.velocity,
                        })
                        total_notes += 1
                track_data.append({
                    "track_id": track.track_id,
                    "name": track.name,
                    "role": track.role.value,
                    "instrument": track.instrument,
                    "volume": track.volume,
                    "notes": track_notes,
                })
            # Estimate duration
            max_duration = 0.0
            for td in track_data:
                for n in td["notes"]:
                    end = n["start_time"] + n["duration"]
                    if end > max_duration:
                        max_duration = end
            export = ExportedSequence(
                export_id=_new_id("exp"),
                composition_id=composition_id,
                total_notes=total_notes,
                total_duration=round(max_duration, 2),
                tracks=track_data,
            )
            self._exports[export.export_id] = export
            self._export_counter += 1
            comp.status = CompositionStatus.EXPORTED
            comp.duration_seconds = max_duration
            comp.updated_at = _now()
            self._record_event(
                MusicEventKind.COMPOSITION_EXPORTED,
                composition_id=composition_id,
                export_id=export.export_id,
                total_notes=total_notes,
            )
            return export

    def get_export(self, export_id: str) -> Optional[ExportedSequence]:
        """Get an exported sequence by ID."""
        with self._inner_lock:
            return self._exports.get(export_id)

    def list_exports(self, limit: int = 50) -> List[ExportedSequence]:
        """List recent exports."""
        with self._inner_lock:
            return list(self._exports.values())[-limit:]

    # -- Observability -----------------------------------------------------

    def list_events(self, limit: int = 100) -> List[MusicEvent]:
        """List recent audit events."""
        with self._inner_lock:
            return self._events[-limit:]

    def get_stats(self) -> MusicStats:
        """Return aggregate statistics."""
        with self._inner_lock:
            total_tracks = sum(len(c.tracks) for c in self._compositions.values())
            return MusicStats(
                total_compositions=len(self._compositions),
                total_tracks=total_tracks,
                total_motifs=len(self._motifs),
                total_templates=len(self._templates),
                total_mappings=len(self._mappings),
                total_adaptation_rules=len(self._adaptation_rules),
                total_exports=len(self._exports),
                total_events=len(self._events),
                composition_counter=self._composition_counter,
                track_counter=self._track_counter,
                motif_counter=self._motif_counter,
                template_counter=self._template_counter,
                mapping_counter=self._mapping_counter,
                rule_counter=self._rule_counter,
                export_counter=self._export_counter,
                event_counter=self._event_counter,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary for health checks."""
        with self._inner_lock:
            return {
                "initialized": self._initialized,
                "total_compositions": len(self._compositions),
                "total_motifs": len(self._motifs),
                "total_templates": len(self._templates),
                "total_mappings": len(self._mappings),
                "total_adaptation_rules": len(self._adaptation_rules),
                "total_exports": len(self._exports),
                "total_events": len(self._events),
                "capacities": {
                    "max_compositions": _MAX_COMPOSITIONS,
                    "max_tracks_per_composition": _MAX_TRACKS_PER_COMPOSITION,
                    "max_measures_per_track": _MAX_MEASURES_PER_TRACK,
                    "max_motifs": _MAX_MOTIFS,
                    "max_templates": _MAX_TEMPLATES,
                    "max_adaptation_rules": _MAX_ADAPTATION_RULES,
                    "max_mappings": _MAX_MAPPINGS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> MusicSnapshot:
        """Capture a point-in-time snapshot."""
        with self._inner_lock:
            return MusicSnapshot(
                compositions=[c.to_dict() for c in self._compositions.values()],
                templates=[t.to_dict() for t in self._templates.values()],
                mappings=[m.to_dict() for m in self._mappings.values()],
                rules=[r.to_dict() for r in self._adaptation_rules.values()],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        """Reset to seed state."""
        with self._inner_lock:
            self._compositions.clear()
            self._motifs.clear()
            self._templates.clear()
            self._mappings.clear()
            self._adaptation_rules.clear()
            self._exports.clear()
            self._events.clear()
            self._composition_counter = 0
            self._track_counter = 0
            self._motif_counter = 0
            self._template_counter = 0
            self._mapping_counter = 0
            self._rule_counter = 0
            self._export_counter = 0
            self._event_counter = 0
            self._record_event(MusicEventKind.SYSTEM_RESET)
            self._seed()

    # -- Seeding -----------------------------------------------------------

    def _seed(self) -> None:
        """Seed with initial demo data."""
        # Mood mappings
        self.map_mood(MoodState.CALM, 70, 0, ScaleType.MAJOR, 0.4, 0.3, Genre.AMBIENT)
        self.map_mood(MoodState.TENSE, 140, 9, ScaleType.MINOR, 0.8, 0.7, Genre.COMBAT)
        self.map_mood(MoodState.TRIUMPHANT, 128, 0, ScaleType.MIXOLYDIAN, 0.9, 0.8, Genre.ORCHESTRAL)
        self.map_mood(MoodState.MELANCHOLY, 60, 7, ScaleType.MINOR, 0.5, 0.4, Genre.ORCHESTRAL)
        self.map_mood(MoodState.MYSTERIOUS, 80, 1, ScaleType.PHRYGIAN, 0.5, 0.5, Genre.AMBIENT)

        # Templates
        self.create_template(
            name="Fantasy Overworld",
            genre=Genre.FANTASY,
            default_tempo=100,
            default_key=0,
            default_scale=ScaleType.MAJOR,
            track_roles=[TrackRole.MELODY, TrackRole.HARMONY, TrackRole.BASS, TrackRole.PERCUSSION],
            progression_name="I-V-vi-IV",
            description="Uplifting fantasy exploration theme.",
        )
        self.create_template(
            name="Boss Battle",
            genre=Genre.COMBAT,
            default_tempo=160,
            default_key=9,
            default_scale=ScaleType.HARMONIC_MINOR,
            track_roles=[TrackRole.MELODY, TrackRole.BASS, TrackRole.PERCUSSION, TrackRole.ARPEGGIO],
            progression_name="i-iv-VII-iii",
            description="Intense boss encounter music.",
        )
        self.create_template(
            name="Peaceful Village",
            genre=Genre.FOLK,
            default_tempo=80,
            default_key=2,
            default_scale=ScaleType.MAJOR,
            track_roles=[TrackRole.MELODY, TrackRole.HARMONY, TrackRole.BASS],
            progression_name="I-IV-V-I",
            description="Relaxing town theme.",
        )

        # Adaptation rules
        self.create_adaptation_rule(
            name="Combat Music",
            trigger=AdaptationTrigger.COMBAT_START,
            target_mood=MoodState.TENSE,
            transition_duration=1.5,
            description="Switch to tense combat music when combat starts.",
        )
        self.create_adaptation_rule(
            name="Victory Fanfare",
            trigger=AdaptationTrigger.VICTORY,
            target_mood=MoodState.TRIUMPHANT,
            transition_duration=0.5,
            description="Play triumphant music on victory.",
        )
        self.create_adaptation_rule(
            name="Exploration Calm",
            trigger=AdaptationTrigger.EXPLORE,
            target_mood=MoodState.CALM,
            transition_duration=3.0,
            description="Calm music during exploration.",
        )

        # A sample composition
        comp = self.create_composition(
            name="Hero's Journey Theme",
            genre=Genre.FANTASY,
            tempo_bpm=110,
            key_root=0,
            scale=ScaleType.MAJOR,
            description="Main theme for the hero's journey.",
            tags=["theme", "main"],
        )
        melody = self.add_track(comp.composition_id, "Lead Melody", TrackRole.MELODY, instrument="flute")
        self.add_track(comp.composition_id, "Harmony", TrackRole.HARMONY, instrument="strings")
        self.add_track(comp.composition_id, "Bass", TrackRole.BASS, instrument="cello")

        # Compose a motif and add it to the melody track
        motif = self.compose_motif("Hero Motif", key_root=0, scale=ScaleType.MAJOR, num_notes=8, seed=42)
        if melody:
            self.add_measure(
                composition_id=comp.composition_id,
                track_id=melody.track_id,
                notes=[{"pitch": n.pitch, "duration": n.duration, "velocity": n.velocity, "offset": n.offset} for n in motif.notes],
            )

        # Set progression
        self.set_progression(
            composition_id=comp.composition_id,
            name="I-V-vi-IV",
            key_root=0,
            scale=ScaleType.MAJOR,
            progression_name="I-V-vi-IV",
        )


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_procedural_music_composer() -> ProceduralMusicComposer:
    """Return the singleton ProceduralMusicComposer instance."""
    return ProceduralMusicComposer.get_instance()
