"""
SparkLabs Agent - AI Music Composer

An AI-native fusion module that composes adaptive, dynamic music for the
SparkLabs game engine. The composer treats a game score as a living system:
reusable themes are assembled from phrases and instrument voices, then
instantiated into tracks that carry layered dynamic voices, intensity-driven
mixing, and mood transitions that react to the live game context in real time.

This module embodies the AI-native principle: music is not a static asset
but an adaptive construction that scales to narrative beats, shifts mood on
the fly as the game context changes, layers voices in and out based on
dynamic intensity, and records a full event timeline that can be replayed,
audited, and tuned.

Architecture:
  AIMusicComposer (singleton)
    |-- InstrumentVoice, MusicalPhrase, MusicalTheme, MusicTrack,
        DynamicLayer, MoodMapping, CompositionSession,
        MusicComposerConfig, MusicComposerStats, MusicComposerSnapshot,
        MusicComposerEvent
    |-- MusicMood, MusicGenre, InstrumentFamily, TrackLayer,
        CompositionStatus, TransitionType, DynamicIntensity

Core Capabilities:
  - register_instrument / get_instrument / list_instruments /
    remove_instrument: instrument voice library management across every
    instrument family (strings, brass, woodwinds, percussion, keyboard,
    synth, bass, guitar, vocal).
  - register_phrase / get_phrase / list_phrases / remove_phrase: melodic
    and rhythmic phrase library management with note-level data.
  - register_theme / get_theme / list_themes / remove_theme: reusable
    theme assembly binding mood, genre, phrases, and instrument sets.
  - compose_track / get_track / list_tracks / remove_track: track
    composition from a theme with layered voices and playback state.
  - add_track_layer / get_track_layer / list_track_layers /
    remove_track_layer: dynamic voice layer management with intensity
    triggers.
  - set_track_intensity / start_track / stop_track / transition_to_mood:
    live playback control and adaptive mood transitions.
  - register_mood_mapping / get_mood_mapping / list_mood_mappings /
    remove_mood_mapping: game-context to mood mapping rules.
  - create_session / get_session / list_sessions / remove_session /
    update_session_mood / get_active_track: composition session lifecycle
    tied to a live game context.
  - generate_variation: procedural phrase variation generation.
  - list_events / get_stats / get_status / get_snapshot / set_config /
    get_config / tick / reset: observability, tuning, and state management.
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

_MAX_INSTRUMENTS: int = 1000
_MAX_PHRASES: int = 4000
_MAX_THEMES: int = 1000
_MAX_TRACKS: int = 500
_MAX_LAYERS: int = 4000
_MAX_MOOD_MAPPINGS: int = 1000
_MAX_SESSIONS: int = 200
_MAX_PHRASES_PER_THEME: int = 64
_MAX_EVENTS: int = 8000
_MAX_INTENSITY_HISTORY: int = 256
_MAX_TRANSITION_QUEUE: int = 64


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


# Ordered ranking of dynamic intensity levels, used to decide whether a
# layer should be audible given the current track intensity.
_INTENSITY_RANK: Dict[Any, int] = {}  # populated after DynamicIntensity is defined


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class MusicMood(str, Enum):
    """Emotional colour of a musical passage."""
    CALM = "calm"
    TENSE = "tense"
    TRIUMPHANT = "triumphant"
    MELANCHOLIC = "melancholic"
    MYSTERIOUS = "mysterious"
    EPIC = "epic"
    PLAYFUL = "playful"
    DARK = "dark"
    HOPEFUL = "hopeful"
    URGENT = "urgent"
    ROMANTIC = "romantic"
    CHAOTIC = "chaotic"


class MusicGenre(str, Enum):
    """Stylistic family that drives instrument selection and arrangement."""
    ORCHESTRAL = "orchestral"
    ELECTRONIC = "electronic"
    ROCK = "rock"
    AMBIENT = "ambient"
    FOLK = "folk"
    JAZZ = "jazz"
    CHIPTUNE = "chiptune"
    HYBRID = "hybrid"
    CINEMATIC = "cinematic"


class InstrumentFamily(str, Enum):
    """Top-level grouping of an instrument voice."""
    STRINGS = "strings"
    BRASS = "brass"
    WOODWINDS = "woodwinds"
    PERCUSSION = "percussion"
    KEYBOARD = "keyboard"
    SYNTH = "synth"
    BASS = "bass"
    GUITAR = "guitar"
    VOCAL = "vocal"


class TrackLayer(str, Enum):
    """Role a voice plays inside a track arrangement."""
    BASE = "base"
    MELODY = "melody"
    HARMONY = "harmony"
    RHYTHM = "rhythm"
    COUNTER_MELODY = "counter_melody"
    PAD = "pad"
    PERCUSSION = "percussion"
    BASSLINE = "bassline"


class CompositionStatus(str, Enum):
    """Lifecycle state of a composed track."""
    DRAFT = "draft"
    ARRANGING = "arranging"
    READY = "ready"
    PLAYING = "playing"
    TRANSITIONING = "transitioning"
    STOPPED = "stopped"


class TransitionType(str, Enum):
    """How a track moves between moods or sections."""
    CROSSFADE = "crossfade"
    HARD_CUT = "hard_cut"
    CRESCENDO = "crescendo"
    DECRESCENDO = "decrescendo"
    INTERLUDE = "interlude"


class DynamicIntensity(str, Enum):
    """Dynamic loudness band, from pianissimo to fortissimo."""
    PP = "pp"
    P = "p"
    MP = "mp"
    MF = "mf"
    F = "f"
    FF = "ff"


# Populate the intensity ranking now that the enum exists.
_INTENSITY_RANK = {
    DynamicIntensity.PP: 0,
    DynamicIntensity.P: 1,
    DynamicIntensity.MP: 2,
    DynamicIntensity.MF: 3,
    DynamicIntensity.F: 4,
    DynamicIntensity.FF: 5,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class InstrumentVoice:
    """A single instrument voice available for arrangement."""
    voice_id: str
    name: str
    family: InstrumentFamily
    midi_program: int = 0
    volume: float = 0.8
    pan: float = 0.0
    reverb: float = 0.3
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicalPhrase:
    """A short melodic or rhythmic fragment built from note events."""
    phrase_id: str
    notes: List[Dict[str, Any]]
    tempo: int = 120
    time_signature: str = "4/4"
    key_signature: str = "C"
    duration_beats: float = 4.0
    mood: MusicMood = MusicMood.CALM
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicalTheme:
    """A reusable theme binding mood, genre, phrases, and instruments."""
    theme_id: str
    name: str
    mood: MusicMood
    genre: MusicGenre
    key_signature: str = "C"
    tempo: int = 120
    time_signature: str = "4/4"
    primary_phrases: List[str] = field(default_factory=list)
    variation_phrases: List[str] = field(default_factory=list)
    instrument_ids: List[str] = field(default_factory=list)
    intensity: DynamicIntensity = DynamicIntensity.MF
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicTrack:
    """A composed track with layered voices and playback state."""
    track_id: str
    name: str
    theme_id: str
    mood: MusicMood = MusicMood.CALM
    genre: MusicGenre = MusicGenre.ORCHESTRAL
    layers: List[str] = field(default_factory=list)
    current_intensity: DynamicIntensity = DynamicIntensity.MF
    status: CompositionStatus = CompositionStatus.DRAFT
    duration_seconds: float = 0.0
    loop_enabled: bool = True
    transition_type: TransitionType = TransitionType.CROSSFADE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DynamicLayer:
    """A single voice layer inside a track with an intensity trigger."""
    layer_id: str
    track_id: str
    layer_type: TrackLayer
    instrument_id: str
    volume: float = 0.7
    active: bool = True
    trigger_intensity: DynamicIntensity = DynamicIntensity.MF
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MoodMapping:
    """Rule mapping a game context to a target mood and intensity."""
    mapping_id: str
    game_context: str
    target_mood: MusicMood
    intensity: DynamicIntensity = DynamicIntensity.MF
    transition_speed: float = 2.0
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompositionSession:
    """A live composition session tied to a game context."""
    session_id: str
    game_context: str
    current_mood: MusicMood
    current_track_id: str = ""
    current_theme_id: str = ""
    intensity_history: List[Dict[str, Any]] = field(default_factory=list)
    transition_queue: List[Dict[str, Any]] = field(default_factory=list)
    start_time: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicComposerConfig:
    """Global tuning parameters for the music composer."""
    max_themes: int = 1000
    max_tracks: int = 500
    max_sessions: int = 200
    max_phrases_per_theme: int = 64
    default_tempo: int = 120
    default_key_signature: str = "C"
    adaptive_layering_enabled: bool = True
    mood_transition_speed: float = 2.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicComposerStats:
    """Aggregate counters describing composer activity."""
    total_themes: int = 0
    total_tracks: int = 0
    active_tracks: int = 0
    total_sessions: int = 0
    total_compositions: int = 0
    total_transitions: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicComposerSnapshot:
    """Full state snapshot for persistence and inspection."""
    timestamp: str = field(default_factory=_now)
    themes: List[Dict[str, Any]] = field(default_factory=list)
    tracks: List[Dict[str, Any]] = field(default_factory=list)
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    instruments: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicComposerEvent:
    """An audit event recorded on the composer timeline."""
    event_id: str
    event_type: str
    timestamp: str
    track_id: str = ""
    session_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# AI Music Composer Singleton
# ---------------------------------------------------------------------------


# Module-level lock and singleton holder for double-checked locking.
_lock = threading.RLock()
_instance: Optional["AIMusicComposer"] = None


class AIMusicComposer:
    """
    AI-native fusion module that composes adaptive dynamic music for the
    SparkLabs game engine. The composer owns the instrument library, phrase
    library, theme registry, composed tracks, dynamic voice layers, mood
    mappings, and live composition sessions as a single coherent state
    machine.

    Implements a singleton via module-level double-checked locking. All
    mutations to internal state are guarded by an instance lock so the
    composer is safe to call from multiple threads. Seed population is
    guarded by a dedicated init lock so re-entrancy during reset cannot
    double-seed the canonical dataset.
    """

    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._instruments: Dict[str, InstrumentVoice] = {}
        self._phrases: Dict[str, MusicalPhrase] = {}
        self._themes: Dict[str, MusicalTheme] = {}
        self._tracks: Dict[str, MusicTrack] = {}
        self._layers: Dict[str, DynamicLayer] = {}
        self._mood_mappings: Dict[str, MoodMapping] = {}
        self._sessions: Dict[str, CompositionSession] = {}
        self._events: List[MusicComposerEvent] = []
        self._config = MusicComposerConfig()
        self._stats = MusicComposerStats()
        self._tick_count: int = 0
        self._composition_counter: int = 0
        self._transition_counter: int = 0
        self._initialized: bool = False
        self._seed()

    @classmethod
    def get_instance(cls) -> "AIMusicComposer":
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls()
        return _instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, data: Dict[str, Any],
              track_id: str = "", session_id: str = "") -> None:
        event = MusicComposerEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            timestamp=_now(),
            track_id=track_id,
            session_id=session_id,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_themes = len(self._themes)
        self._stats.total_tracks = len(self._tracks)
        self._stats.active_tracks = sum(
            1 for t in self._tracks.values()
            if t.status == CompositionStatus.PLAYING
        )
        self._stats.total_sessions = len(self._sessions)
        self._stats.total_compositions = self._composition_counter
        self._stats.total_transitions = self._transition_counter
        self._stats.tick_count = self._tick_count

    def _intensity_rank(self, intensity: DynamicIntensity) -> int:
        return _INTENSITY_RANK.get(intensity, 3)

    def _resolve_active_layers(self, track: MusicTrack) -> int:
        """Activate layers whose trigger intensity is at or below current."""
        current_rank = self._intensity_rank(track.current_intensity)
        changed = 0
        for layer_id in track.layers:
            layer = self._layers.get(layer_id)
            if layer is None:
                continue
            should_be_active = (
                self._intensity_rank(layer.trigger_intensity) <= current_rank
            )
            if layer.active != should_be_active:
                layer.active = should_be_active
                changed += 1
        return changed

    def _compute_track_duration(self, theme: MusicalTheme) -> float:
        """Estimate track duration in seconds from its phrase set."""
        phrases = [
            self._phrases.get(pid)
            for pid in (theme.primary_phrases + theme.variation_phrases)
            if self._phrases.get(pid) is not None
        ]
        if not phrases:
            tempo = theme.tempo or self._config.default_tempo or 120
            return (4.0 * 60.0) / max(1, tempo)
        total_beats = sum(p.duration_beats for p in phrases)
        tempo = theme.tempo or self._config.default_tempo or 120
        return (total_beats * 60.0) / max(1, tempo)

    # ------------------------------------------------------------------
    # Instrument Management
    # ------------------------------------------------------------------

    def register_instrument(self, voice_id, name, family,
                            midi_program=0, volume=0.8, pan=0.0,
                            reverb=0.3, is_active=True,
                            metadata=None) -> Tuple[bool, str, Optional[InstrumentVoice]]:
        """Register an instrument voice in the composer library."""
        with self._lock:
            if not voice_id:
                return False, "invalid_voice_id", None
            if voice_id in self._instruments:
                return False, "instrument_exists", None
            if len(self._instruments) >= _MAX_INSTRUMENTS:
                return False, "instruments_capacity", None
            fam = _coerce_enum(InstrumentFamily, family, InstrumentFamily.STRINGS)
            voice = InstrumentVoice(
                voice_id=voice_id,
                name=name,
                family=fam,
                midi_program=int(midi_program),
                volume=float(volume),
                pan=float(pan),
                reverb=float(reverb),
                is_active=bool(is_active),
                metadata=metadata or {},
            )
            self._instruments[voice_id] = voice
            self._emit("instrument_registered", {
                "voice_id": voice_id,
                "family": fam.value,
            })
            return True, "registered", voice

    def get_instrument(self, voice_id) -> Optional[InstrumentVoice]:
        with self._lock:
            return self._instruments.get(voice_id)

    def list_instruments(self, family_filter="") -> List[InstrumentVoice]:
        with self._lock:
            items = list(self._instruments.values())
            if family_filter:
                fam = _coerce_enum(InstrumentFamily, family_filter)
                if fam is not None:
                    items = [v for v in items if v.family == fam]
                else:
                    items = [
                        v for v in items
                        if v.family.value == family_filter
                    ]
            return items

    def remove_instrument(self, voice_id) -> Tuple[bool, str]:
        with self._lock:
            if voice_id not in self._instruments:
                return False, "not_found"
            del self._instruments[voice_id]
            self._emit("instrument_removed", {"voice_id": voice_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Phrase Management
    # ------------------------------------------------------------------

    def register_phrase(self, phrase_id, notes, tempo=120,
                        time_signature="4/4", key_signature="C",
                        duration_beats=4, mood="calm",
                        metadata=None) -> Tuple[bool, str, Optional[MusicalPhrase]]:
        """Register a musical phrase in the phrase library."""
        with self._lock:
            if not phrase_id:
                return False, "invalid_phrase_id", None
            if phrase_id in self._phrases:
                return False, "phrase_exists", None
            if len(self._phrases) >= _MAX_PHRASES:
                return False, "phrases_capacity", None
            mood_enum = _coerce_enum(MusicMood, mood, MusicMood.CALM)
            phrase = MusicalPhrase(
                phrase_id=phrase_id,
                notes=list(notes) if notes else [],
                tempo=int(tempo),
                time_signature=time_signature,
                key_signature=key_signature,
                duration_beats=float(duration_beats),
                mood=mood_enum,
                metadata=metadata or {},
            )
            self._phrases[phrase_id] = phrase
            self._emit("phrase_registered", {
                "phrase_id": phrase_id,
                "mood": mood_enum.value,
                "note_count": len(phrase.notes),
            })
            return True, "registered", phrase

    def get_phrase(self, phrase_id) -> Optional[MusicalPhrase]:
        with self._lock:
            return self._phrases.get(phrase_id)

    def list_phrases(self, mood_filter="") -> List[MusicalPhrase]:
        with self._lock:
            items = list(self._phrases.values())
            if mood_filter:
                mood = _coerce_enum(MusicMood, mood_filter)
                if mood is not None:
                    items = [p for p in items if p.mood == mood]
                else:
                    items = [
                        p for p in items
                        if p.mood.value == mood_filter
                    ]
            return items

    def remove_phrase(self, phrase_id) -> Tuple[bool, str]:
        with self._lock:
            if phrase_id not in self._phrases:
                return False, "not_found"
            del self._phrases[phrase_id]
            self._emit("phrase_removed", {"phrase_id": phrase_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Theme Management
    # ------------------------------------------------------------------

    def register_theme(self, theme_id, name, mood, genre,
                       key_signature="C", tempo=120, time_signature="4/4",
                       primary_phrases=None, variation_phrases=None,
                       instrument_ids=None, intensity="mf", description="",
                       metadata=None) -> Tuple[bool, str, Optional[MusicalTheme]]:
        """Register a reusable musical theme."""
        with self._lock:
            if not theme_id:
                return False, "invalid_theme_id", None
            if theme_id in self._themes:
                return False, "theme_exists", None
            if len(self._themes) >= self._config.max_themes:
                return False, "themes_capacity", None
            mood_enum = _coerce_enum(MusicMood, mood, MusicMood.CALM)
            genre_enum = _coerce_enum(MusicGenre, genre, MusicGenre.ORCHESTRAL)
            intensity_enum = _coerce_enum(
                DynamicIntensity, intensity, DynamicIntensity.MF
            )
            primary = list(primary_phrases) if primary_phrases else []
            if len(primary) > self._config.max_phrases_per_theme:
                return False, "too_many_phrases", None
            theme = MusicalTheme(
                theme_id=theme_id,
                name=name,
                mood=mood_enum,
                genre=genre_enum,
                key_signature=key_signature,
                tempo=int(tempo),
                time_signature=time_signature,
                primary_phrases=primary,
                variation_phrases=list(variation_phrases) if variation_phrases else [],
                instrument_ids=list(instrument_ids) if instrument_ids else [],
                intensity=intensity_enum,
                description=description,
                metadata=metadata or {},
            )
            self._themes[theme_id] = theme
            self._emit("theme_registered", {
                "theme_id": theme_id,
                "mood": mood_enum.value,
                "genre": genre_enum.value,
            })
            return True, "registered", theme

    def get_theme(self, theme_id) -> Optional[MusicalTheme]:
        with self._lock:
            return self._themes.get(theme_id)

    def list_themes(self, mood_filter="", genre_filter="") -> List[MusicalTheme]:
        with self._lock:
            items = list(self._themes.values())
            if mood_filter:
                mood = _coerce_enum(MusicMood, mood_filter)
                if mood is not None:
                    items = [t for t in items if t.mood == mood]
                else:
                    items = [
                        t for t in items
                        if t.mood.value == mood_filter
                    ]
            if genre_filter:
                genre = _coerce_enum(MusicGenre, genre_filter)
                if genre is not None:
                    items = [t for t in items if t.genre == genre]
                else:
                    items = [
                        t for t in items
                        if t.genre.value == genre_filter
                    ]
            return items

    def remove_theme(self, theme_id) -> Tuple[bool, str]:
        with self._lock:
            if theme_id not in self._themes:
                return False, "not_found"
            del self._themes[theme_id]
            self._emit("theme_removed", {"theme_id": theme_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Track Composition
    # ------------------------------------------------------------------

    def compose_track(self, track_id, name, theme_id, mood="",
                      genre="", loop_enabled=True,
                      transition_type="crossfade",
                      metadata=None) -> Tuple[bool, str, Optional[MusicTrack]]:
        """Compose a track from a theme with layered voices."""
        with self._lock:
            if not track_id:
                return False, "invalid_track_id", None
            if track_id in self._tracks:
                return False, "track_exists", None
            if len(self._tracks) >= self._config.max_tracks:
                return False, "tracks_capacity", None
            theme = self._themes.get(theme_id)
            if theme is None:
                return False, "theme_not_found", None
            mood_enum = _coerce_enum(
                MusicMood, mood or theme.mood, theme.mood
            )
            genre_enum = _coerce_enum(
                MusicGenre, genre or theme.genre, theme.genre
            )
            trans_enum = _coerce_enum(
                TransitionType, transition_type, TransitionType.CROSSFADE
            )
            track = MusicTrack(
                track_id=track_id,
                name=name,
                theme_id=theme_id,
                mood=mood_enum,
                genre=genre_enum,
                layers=[],
                current_intensity=theme.intensity,
                status=CompositionStatus.ARRANGING,
                duration_seconds=self._compute_track_duration(theme),
                loop_enabled=bool(loop_enabled),
                transition_type=trans_enum,
                metadata=metadata or {},
            )
            self._tracks[track_id] = track
            self._composition_counter += 1

            # Auto-arrange one layer per theme instrument so the track is
            # immediately playable after composition.
            layer_index = 0
            for inst_id in theme.instrument_ids:
                if inst_id not in self._instruments:
                    continue
                layer_id = f"layer_{track_id}_{layer_index}"
                layer_type = TrackLayer.BASE
                if layer_index == 0:
                    layer_type = TrackLayer.MELODY
                elif layer_index == 1:
                    layer_type = TrackLayer.HARMONY
                elif layer_index == 2:
                    layer_type = TrackLayer.BASSLINE
                elif layer_index == 3:
                    layer_type = TrackLayer.PERCUSSION
                layer = DynamicLayer(
                    layer_id=layer_id,
                    track_id=track_id,
                    layer_type=layer_type,
                    instrument_id=inst_id,
                    volume=self._instruments[inst_id].volume,
                    active=True,
                    trigger_intensity=theme.intensity,
                    metadata={"auto_arranged": True},
                )
                self._layers[layer_id] = layer
                track.layers.append(layer_id)
                layer_index += 1

            track.status = CompositionStatus.READY
            self._resolve_active_layers(track)
            self._emit("track_composed", {
                "track_id": track_id,
                "theme_id": theme_id,
                "layers": len(track.layers),
                "duration_seconds": track.duration_seconds,
            }, track_id=track_id)
            return True, "composed", track

    def get_track(self, track_id) -> Optional[MusicTrack]:
        with self._lock:
            return self._tracks.get(track_id)

    def list_tracks(self, status_filter="") -> List[MusicTrack]:
        with self._lock:
            items = list(self._tracks.values())
            if status_filter:
                status = _coerce_enum(CompositionStatus, status_filter)
                if status is not None:
                    items = [t for t in items if t.status == status]
                else:
                    items = [
                        t for t in items
                        if t.status.value == status_filter
                    ]
            return items

    def remove_track(self, track_id) -> Tuple[bool, str]:
        with self._lock:
            if track_id not in self._tracks:
                return False, "not_found"
            track = self._tracks[track_id]
            for layer_id in list(track.layers):
                self._layers.pop(layer_id, None)
            del self._tracks[track_id]
            self._emit("track_removed", {"track_id": track_id}, track_id=track_id)
            return True, "removed"

    # ------------------------------------------------------------------
    # Track Layer Management
    # ------------------------------------------------------------------

    def add_track_layer(self, layer_id, track_id, layer_type,
                        instrument_id, volume=0.7, trigger_intensity="mf",
                        metadata=None) -> Tuple[bool, str, Optional[DynamicLayer]]:
        """Add a dynamic voice layer to an existing track."""
        with self._lock:
            if not layer_id:
                return False, "invalid_layer_id", None
            if layer_id in self._layers:
                return False, "layer_exists", None
            track = self._tracks.get(track_id)
            if track is None:
                return False, "track_not_found", None
            if instrument_id not in self._instruments:
                return False, "instrument_not_found", None
            if len(self._layers) >= _MAX_LAYERS:
                return False, "layers_capacity", None
            lt = _coerce_enum(TrackLayer, layer_type, TrackLayer.BASE)
            trig = _coerce_enum(
                DynamicIntensity, trigger_intensity, DynamicIntensity.MF
            )
            layer = DynamicLayer(
                layer_id=layer_id,
                track_id=track_id,
                layer_type=lt,
                instrument_id=instrument_id,
                volume=float(volume),
                active=True,
                trigger_intensity=trig,
                metadata=metadata or {},
            )
            self._layers[layer_id] = layer
            track.layers.append(layer_id)
            self._resolve_active_layers(track)
            self._emit("layer_added", {
                "layer_id": layer_id,
                "track_id": track_id,
                "layer_type": lt.value,
                "instrument_id": instrument_id,
            }, track_id=track_id)
            return True, "added", layer

    def get_track_layer(self, layer_id) -> Optional[DynamicLayer]:
        with self._lock:
            return self._layers.get(layer_id)

    def list_track_layers(self, track_id) -> List[DynamicLayer]:
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return []
            return [
                self._layers[lid]
                for lid in track.layers
                if lid in self._layers
            ]

    def remove_track_layer(self, layer_id) -> Tuple[bool, str]:
        with self._lock:
            layer = self._layers.get(layer_id)
            if layer is None:
                return False, "not_found"
            track = self._tracks.get(layer.track_id)
            if track is not None and layer_id in track.layers:
                track.layers.remove(layer_id)
            del self._layers[layer_id]
            self._emit("layer_removed", {
                "layer_id": layer_id,
                "track_id": layer.track_id,
            }, track_id=layer.track_id)
            return True, "removed"

    # ------------------------------------------------------------------
    # Track Playback Control
    # ------------------------------------------------------------------

    def set_track_intensity(self, track_id, intensity) -> Tuple[bool, str, Optional[MusicTrack]]:
        """Set the dynamic intensity of a track and re-evaluate layers."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, "track_not_found", None
            intensity_enum = _coerce_enum(
                DynamicIntensity, intensity, track.current_intensity
            )
            track.current_intensity = intensity_enum
            changed = self._resolve_active_layers(track)
            self._emit("intensity_set", {
                "track_id": track_id,
                "intensity": intensity_enum.value,
                "layers_changed": changed,
            }, track_id=track_id)
            return True, "intensity_set", track

    def start_track(self, track_id) -> Tuple[bool, str, Optional[MusicTrack]]:
        """Start playback of a composed track."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, "track_not_found", None
            if track.status == CompositionStatus.PLAYING:
                return False, "already_playing", track
            if track.status == CompositionStatus.DRAFT:
                return False, "track_not_ready", track
            track.status = CompositionStatus.PLAYING
            self._resolve_active_layers(track)
            self._emit("track_started", {
                "track_id": track_id,
                "mood": track.mood.value,
            }, track_id=track_id)
            return True, "started", track

    def stop_track(self, track_id) -> Tuple[bool, str, Optional[MusicTrack]]:
        """Stop playback of a track."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, "track_not_found", None
            if track.status == CompositionStatus.STOPPED:
                return False, "already_stopped", track
            track.status = CompositionStatus.STOPPED
            self._emit("track_stopped", {"track_id": track_id}, track_id=track_id)
            return True, "stopped", track

    def transition_to_mood(self, track_id, target_mood,
                           transition_type="crossfade",
                           duration=3.0) -> Tuple[bool, str, Optional[MusicTrack]]:
        """Transition a playing track to a new mood."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, "track_not_found", None
            mood_enum = _coerce_enum(
                MusicMood, target_mood, track.mood
            )
            trans_enum = _coerce_enum(
                TransitionType, transition_type, TransitionType.CROSSFADE
            )
            previous_mood = track.mood
            track.mood = mood_enum
            track.transition_type = trans_enum
            if track.status == CompositionStatus.PLAYING:
                track.status = CompositionStatus.TRANSITIONING
            self._transition_counter += 1
            self._emit("mood_transition", {
                "track_id": track_id,
                "previous_mood": previous_mood.value,
                "target_mood": mood_enum.value,
                "transition_type": trans_enum.value,
                "duration": duration,
            }, track_id=track_id)
            return True, "transitioning", track

    # ------------------------------------------------------------------
    # Mood Mapping Management
    # ------------------------------------------------------------------

    def register_mood_mapping(self, mapping_id, game_context, target_mood,
                              intensity="mf", transition_speed=2.0,
                              duration=0.0,
                              metadata=None) -> Tuple[bool, str, Optional[MoodMapping]]:
        """Register a rule mapping a game context to a target mood."""
        with self._lock:
            if not mapping_id:
                return False, "invalid_mapping_id", None
            if mapping_id in self._mood_mappings:
                return False, "mapping_exists", None
            if len(self._mood_mappings) >= _MAX_MOOD_MAPPINGS:
                return False, "mappings_capacity", None
            mood_enum = _coerce_enum(MusicMood, target_mood, MusicMood.CALM)
            intensity_enum = _coerce_enum(
                DynamicIntensity, intensity, DynamicIntensity.MF
            )
            mapping = MoodMapping(
                mapping_id=mapping_id,
                game_context=game_context,
                target_mood=mood_enum,
                intensity=intensity_enum,
                transition_speed=float(transition_speed),
                duration=float(duration),
                metadata=metadata or {},
            )
            self._mood_mappings[mapping_id] = mapping
            self._emit("mood_mapping_registered", {
                "mapping_id": mapping_id,
                "game_context": game_context,
                "target_mood": mood_enum.value,
            })
            return True, "registered", mapping

    def get_mood_mapping(self, mapping_id) -> Optional[MoodMapping]:
        with self._lock:
            return self._mood_mappings.get(mapping_id)

    def list_mood_mappings(self, game_context="") -> List[MoodMapping]:
        with self._lock:
            items = list(self._mood_mappings.values())
            if game_context:
                items = [
                    m for m in items
                    if m.game_context == game_context
                ]
            return items

    def remove_mood_mapping(self, mapping_id) -> Tuple[bool, str]:
        with self._lock:
            if mapping_id not in self._mood_mappings:
                return False, "not_found"
            del self._mood_mappings[mapping_id]
            self._emit("mood_mapping_removed", {"mapping_id": mapping_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Composition Session Management
    # ------------------------------------------------------------------

    def create_session(self, session_id, game_context, initial_mood="calm",
                       metadata=None) -> Tuple[bool, str, Optional[CompositionSession]]:
        """Create a live composition session tied to a game context."""
        with self._lock:
            if not session_id:
                return False, "invalid_session_id", None
            if session_id in self._sessions:
                return False, "session_exists", None
            if len(self._sessions) >= self._config.max_sessions:
                return False, "sessions_capacity", None
            mood_enum = _coerce_enum(MusicMood, initial_mood, MusicMood.CALM)
            session = CompositionSession(
                session_id=session_id,
                game_context=game_context,
                current_mood=mood_enum,
                metadata=metadata or {},
            )
            self._sessions[session_id] = session

            # Try to bind an initial track whose mood matches the session.
            for track in self._tracks.values():
                if track.mood == mood_enum and track.status in (
                    CompositionStatus.READY,
                    CompositionStatus.PLAYING,
                    CompositionStatus.STOPPED,
                ):
                    session.current_track_id = track.track_id
                    session.current_theme_id = track.theme_id
                    break

            self._emit("session_created", {
                "session_id": session_id,
                "game_context": game_context,
                "initial_mood": mood_enum.value,
                "track_id": session.current_track_id,
            }, session_id=session_id)
            return True, "created", session

    def get_session(self, session_id) -> Optional[CompositionSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, game_context="") -> List[CompositionSession]:
        with self._lock:
            items = list(self._sessions.values())
            if game_context:
                items = [
                    s for s in items
                    if s.game_context == game_context
                ]
            return items

    def remove_session(self, session_id) -> Tuple[bool, str]:
        with self._lock:
            if session_id not in self._sessions:
                return False, "not_found"
            del self._sessions[session_id]
            self._emit("session_removed", {"session_id": session_id},
                       session_id=session_id)
            return True, "removed"

    def update_session_mood(self, session_id, new_mood,
                            transition_type="crossfade") -> Tuple[bool, str, Optional[CompositionSession]]:
        """Update the mood of a session and rebind the active track."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, "session_not_found", None
            mood_enum = _coerce_enum(MusicMood, new_mood, session.current_mood)
            trans_enum = _coerce_enum(
                TransitionType, transition_type, TransitionType.CROSSFADE
            )
            previous_mood = session.current_mood
            session.current_mood = mood_enum

            # Look up a mood mapping for this game context first.
            resolved_track_id = ""
            for mapping in self._mood_mappings.values():
                if mapping.game_context == session.game_context and \
                        mapping.target_mood == mood_enum:
                    break

            # Find a track whose mood matches the new session mood.
            for track in self._tracks.values():
                if track.mood == mood_enum and track.status in (
                    CompositionStatus.READY,
                    CompositionStatus.PLAYING,
                    CompositionStatus.TRANSITIONING,
                    CompositionStatus.STOPPED,
                ):
                    resolved_track_id = track.track_id
                    if session.current_track_id and \
                            session.current_track_id != resolved_track_id:
                        self.transition_to_mood(
                            resolved_track_id, mood_enum.value,
                            trans_enum.value,
                            self._config.mood_transition_speed,
                        )
                    session.current_track_id = resolved_track_id
                    session.current_theme_id = track.theme_id
                    break

            session.transition_queue.append({
                "timestamp": _now(),
                "previous_mood": previous_mood.value,
                "target_mood": mood_enum.value,
                "transition_type": trans_enum.value,
                "track_id": resolved_track_id,
            })
            _evict_fifo_list(session.transition_queue, _MAX_TRANSITION_QUEUE)

            session.intensity_history.append({
                "timestamp": _now(),
                "mood": mood_enum.value,
                "track_id": resolved_track_id,
            })
            _evict_fifo_list(session.intensity_history, _MAX_INTENSITY_HISTORY)

            self._emit("session_mood_updated", {
                "session_id": session_id,
                "previous_mood": previous_mood.value,
                "new_mood": mood_enum.value,
                "track_id": resolved_track_id,
            }, session_id=session_id)
            return True, "mood_updated", session

    def get_active_track(self, session_id) -> Optional[MusicTrack]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or not session.current_track_id:
                return None
            return self._tracks.get(session.current_track_id)

    # ------------------------------------------------------------------
    # Variation Generation
    # ------------------------------------------------------------------

    def generate_variation(self, theme_id,
                           variation_count=1) -> Tuple[bool, str, List[MusicalPhrase]]:
        """Generate procedural phrase variations from a theme."""
        with self._lock:
            theme = self._themes.get(theme_id)
            if theme is None:
                return False, "theme_not_found", []
            source_phrase_ids = (
                theme.primary_phrases + theme.variation_phrases
            )
            source_phrases = [
                self._phrases.get(pid)
                for pid in source_phrase_ids
                if self._phrases.get(pid) is not None
            ]
            if not source_phrases:
                return False, "no_source_phrases", []
            count = max(1, int(variation_count))
            generated: List[MusicalPhrase] = []
            for i in range(count):
                base = source_phrases[i % len(source_phrases)]
                # Apply small procedural transforms: tempo jitter and a
                # semitone transpose applied to every note pitch.
                tempo_jitter = random.randint(-8, 8)
                new_tempo = max(40, base.tempo + tempo_jitter)
                transpose = random.choice([-2, -1, 0, 1, 2, 5])
                new_notes: List[Dict[str, Any]] = []
                for note in base.notes:
                    new_note = dict(note)
                    if "pitch" in new_note and isinstance(new_note["pitch"], str):
                        new_note["pitch"] = _transpose_pitch(
                            new_note["pitch"], transpose
                        )
                    if "velocity" in new_note:
                        new_note["velocity"] = max(
                            0.0, min(1.0, float(new_note["velocity"]) +
                                     random.uniform(-0.1, 0.1))
                        )
                    new_note["variation_index"] = i
                    new_notes.append(new_note)
                variation_id = f"var_{theme_id}_{i}_{_new_id()}"
                phrase = MusicalPhrase(
                    phrase_id=variation_id,
                    notes=new_notes,
                    tempo=new_tempo,
                    time_signature=base.time_signature,
                    key_signature=base.key_signature,
                    duration_beats=base.duration_beats,
                    mood=base.mood,
                    metadata={
                        "source_phrase": base.phrase_id,
                        "theme_id": theme_id,
                        "transpose": transpose,
                        "procedural": True,
                    },
                )
                self._phrases[variation_id] = phrase
                theme.variation_phrases.append(variation_id)
                generated.append(phrase)
            self._emit("variation_generated", {
                "theme_id": theme_id,
                "count": len(generated),
            })
            return True, "generated", generated

    # ------------------------------------------------------------------
    # Events and Observability
    # ------------------------------------------------------------------

    def list_events(self, track_id="", session_id="",
                    limit=100) -> List[MusicComposerEvent]:
        with self._lock:
            items = list(self._events)
            if track_id:
                items = [e for e in items if e.track_id == track_id]
            if session_id:
                items = [e for e in items if e.session_id == session_id]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "instruments": len(self._instruments),
                "phrases": len(self._phrases),
                "themes": len(self._themes),
                "tracks": len(self._tracks),
                "layers": len(self._layers),
                "mood_mappings": len(self._mood_mappings),
                "sessions": len(self._sessions),
                "active_tracks": self._stats.active_tracks,
                "total_compositions": self._stats.total_compositions,
                "total_transitions": self._stats.total_transitions,
                "events": len(self._events),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> MusicComposerStats:
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> MusicComposerSnapshot:
        with self._lock:
            self._refresh_stats()
            return MusicComposerSnapshot(
                themes=[t.to_dict() for t in list(self._themes.values())[:50]],
                tracks=[t.to_dict() for t in list(self._tracks.values())[:50]],
                sessions=[s.to_dict() for s in list(self._sessions.values())[:50]],
                instruments=[
                    v.to_dict() for v in list(self._instruments.values())[:50]
                ],
                stats=self._stats.to_dict(),
            )

    # ------------------------------------------------------------------
    # Config and Tick
    # ------------------------------------------------------------------

    def get_config(self) -> MusicComposerConfig:
        with self._lock:
            return self._config

    def set_config(self, **kwargs) -> Tuple[bool, str, "MusicComposerConfig"]:
        """Apply keyword config updates to the composer."""
        with self._lock:
            if not kwargs:
                return False, "no_updates", self._config
            for key, value in kwargs.items():
                if key == "metadata" and isinstance(value, dict):
                    self._config.metadata.update(value)
                elif hasattr(self._config, key):
                    setattr(self._config, key, value)
            self._emit("config_updated", {"keys": list(kwargs.keys())})
            return True, "updated", self._config

    def tick(self, dt=1.0) -> Dict[str, Any]:
        """Advance the composer by one tick, resolving transient states."""
        with self._lock:
            self._tick_count += 1
            transitions_resolved = 0
            layers_adjusted = 0

            # Resolve tracks that are mid-transition back to playing.
            for track in self._tracks.values():
                if track.status == CompositionStatus.TRANSITIONING:
                    track.status = CompositionStatus.PLAYING
                    transitions_resolved += 1
                if self._config.adaptive_layering_enabled and \
                        track.status == CompositionStatus.PLAYING:
                    layers_adjusted += self._resolve_active_layers(track)

            # Process pending session transition queues: trim completed
            # entries so the queue does not grow without bound.
            for session in self._sessions.values():
                if session.transition_queue and len(session.transition_queue) > 1:
                    session.transition_queue = session.transition_queue[-1:]

            self._refresh_stats()
            return {
                "tick": self._tick_count,
                "dt": dt,
                "transitions_resolved": transitions_resolved,
                "layers_adjusted": layers_adjusted,
                "active_tracks": self._stats.active_tracks,
                "total_tracks": self._stats.total_tracks,
                "total_themes": self._stats.total_themes,
                "total_sessions": self._stats.total_sessions,
            }

    def reset(self) -> None:
        """Clear all composer state and re-seed the canonical dataset."""
        with self._lock:
            self._instruments.clear()
            self._phrases.clear()
            self._themes.clear()
            self._tracks.clear()
            self._layers.clear()
            self._mood_mappings.clear()
            self._sessions.clear()
            self._events.clear()
            self._config = MusicComposerConfig()
            self._stats = MusicComposerStats()
            self._tick_count = 0
            self._composition_counter = 0
            self._transition_counter = 0
            self._initialized = False
            self._seed()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the composer with a canonical set of musical content."""
        with self._init_lock:
            if self._initialized:
                return

            self._seed_instruments()
            self._seed_phrases()
            self._seed_themes()
            self._seed_tracks()
            self._seed_layers()
            self._seed_mood_mappings()
            self._seed_sessions()

            self._refresh_stats()
            self._emit("composer_seeded", {
                "instruments": len(self._instruments),
                "phrases": len(self._phrases),
                "themes": len(self._themes),
                "tracks": len(self._tracks),
                "layers": len(self._layers),
                "mood_mappings": len(self._mood_mappings),
                "sessions": len(self._sessions),
            })
            self._initialized = True

    def _seed_instruments(self) -> None:
        """Seed 12 instrument voices spanning every instrument family."""
        instruments = [
            InstrumentVoice(
                voice_id="inst_violin_section",
                name="Violin Section",
                family=InstrumentFamily.STRINGS,
                midi_program=48,
                volume=0.85,
                pan=-0.15,
                reverb=0.35,
                is_active=True,
                metadata={"section": "strings", "range": "G3-E6"},
            ),
            InstrumentVoice(
                voice_id="inst_cello_section",
                name="Cello Section",
                family=InstrumentFamily.STRINGS,
                midi_program=42,
                volume=0.8,
                pan=0.15,
                reverb=0.4,
                is_active=True,
                metadata={"section": "strings", "range": "C2-C5"},
            ),
            InstrumentVoice(
                voice_id="inst_trumpet",
                name="Trumpet",
                family=InstrumentFamily.BRASS,
                midi_program=56,
                volume=0.78,
                pan=0.25,
                reverb=0.3,
                is_active=True,
                metadata={"section": "brass", "range": "E3-D6"},
            ),
            InstrumentVoice(
                voice_id="inst_french_horn",
                name="French Horn",
                family=InstrumentFamily.BRASS,
                midi_program=60,
                volume=0.72,
                pan=-0.25,
                reverb=0.45,
                is_active=True,
                metadata={"section": "brass", "range": "B1-F5"},
            ),
            InstrumentVoice(
                voice_id="inst_flute",
                name="Flute",
                family=InstrumentFamily.WOODWINDS,
                midi_program=73,
                volume=0.68,
                pan=-0.2,
                reverb=0.3,
                is_active=True,
                metadata={"section": "woodwinds", "range": "C4-D7"},
            ),
            InstrumentVoice(
                voice_id="inst_clarinet",
                name="Clarinet",
                family=InstrumentFamily.WOODWINDS,
                midi_program=71,
                volume=0.66,
                pan=0.2,
                reverb=0.3,
                is_active=True,
                metadata={"section": "woodwinds", "range": "D3-Bb6"},
            ),
            InstrumentVoice(
                voice_id="inst_timpani",
                name="Timpani",
                family=InstrumentFamily.PERCUSSION,
                midi_program=47,
                volume=0.82,
                pan=0.0,
                reverb=0.5,
                is_active=True,
                metadata={"section": "percussion", "tuned": True},
            ),
            InstrumentVoice(
                voice_id="inst_snare_drum",
                name="Snare Drum",
                family=InstrumentFamily.PERCUSSION,
                midi_program=40,
                volume=0.75,
                pan=0.1,
                reverb=0.2,
                is_active=True,
                metadata={"section": "percussion", "tuned": False},
            ),
            InstrumentVoice(
                voice_id="inst_grand_piano",
                name="Grand Piano",
                family=InstrumentFamily.KEYBOARD,
                midi_program=0,
                volume=0.8,
                pan=0.0,
                reverb=0.25,
                is_active=True,
                metadata={"section": "keyboard", "range": "A0-C8"},
            ),
            InstrumentVoice(
                voice_id="inst_synth_pad",
                name="Synth Pad",
                family=InstrumentFamily.SYNTH,
                midi_program=88,
                volume=0.65,
                pan=0.0,
                reverb=0.6,
                is_active=True,
                metadata={"section": "synth", "polyphonic": True},
            ),
            InstrumentVoice(
                voice_id="inst_electric_bass",
                name="Electric Bass",
                family=InstrumentFamily.BASS,
                midi_program=33,
                volume=0.85,
                pan=0.0,
                reverb=0.15,
                is_active=True,
                metadata={"section": "bass", "range": "E1-E4"},
            ),
            InstrumentVoice(
                voice_id="inst_choir",
                name="Choir",
                family=InstrumentFamily.VOCAL,
                midi_program=52,
                volume=0.6,
                pan=0.0,
                reverb=0.55,
                is_active=True,
                metadata={"section": "vocal", "syllable": "aah"},
            ),
        ]
        for voice in instruments:
            self._instruments[voice.voice_id] = voice

    def _seed_phrases(self) -> None:
        """Seed 8 musical phrases covering distinct moods."""
        phrases = [
            MusicalPhrase(
                phrase_id="phrase_calm_melody_01",
                notes=[
                    {"pitch": "C4", "start_beat": 0.0, "duration": 2.0, "velocity": 0.6},
                    {"pitch": "E4", "start_beat": 2.0, "duration": 2.0, "velocity": 0.65},
                    {"pitch": "G4", "start_beat": 4.0, "duration": 2.0, "velocity": 0.7},
                    {"pitch": "E4", "start_beat": 6.0, "duration": 2.0, "velocity": 0.6},
                ],
                tempo=80,
                time_signature="4/4",
                key_signature="C_major",
                duration_beats=8.0,
                mood=MusicMood.CALM,
                metadata={"instrument": "inst_violin_section"},
            ),
            MusicalPhrase(
                phrase_id="phrase_tense_rhythm_01",
                notes=[
                    {"pitch": "D3", "start_beat": 0.0, "duration": 0.5, "velocity": 0.9},
                    {"pitch": "D3", "start_beat": 0.5, "duration": 0.5, "velocity": 0.9},
                    {"pitch": "F3", "start_beat": 1.0, "duration": 0.5, "velocity": 0.85},
                    {"pitch": "A3", "start_beat": 1.5, "duration": 0.5, "velocity": 0.9},
                    {"pitch": "D3", "start_beat": 2.0, "duration": 0.5, "velocity": 0.9},
                    {"pitch": "D3", "start_beat": 2.5, "duration": 0.5, "velocity": 0.9},
                    {"pitch": "C3", "start_beat": 3.0, "duration": 1.0, "velocity": 0.95},
                ],
                tempo=140,
                time_signature="4/4",
                key_signature="D_minor",
                duration_beats=4.0,
                mood=MusicMood.TENSE,
                metadata={"instrument": "inst_snare_drum"},
            ),
            MusicalPhrase(
                phrase_id="phrase_epic_chord_01",
                notes=[
                    {"pitch": "C3", "start_beat": 0.0, "duration": 4.0, "velocity": 0.95},
                    {"pitch": "G3", "start_beat": 0.0, "duration": 4.0, "velocity": 0.95},
                    {"pitch": "C4", "start_beat": 0.0, "duration": 4.0, "velocity": 0.95},
                    {"pitch": "E4", "start_beat": 0.0, "duration": 4.0, "velocity": 0.95},
                    {"pitch": "G4", "start_beat": 0.0, "duration": 4.0, "velocity": 0.95},
                ],
                tempo=120,
                time_signature="4/4",
                key_signature="C_major",
                duration_beats=4.0,
                mood=MusicMood.EPIC,
                metadata={"instrument": "inst_french_horn", "chord": "C_major"},
            ),
            MusicalPhrase(
                phrase_id="phrase_mysterious_pad_01",
                notes=[
                    {"pitch": "F#3", "start_beat": 0.0, "duration": 6.0, "velocity": 0.5},
                    {"pitch": "C#4", "start_beat": 0.0, "duration": 6.0, "velocity": 0.5},
                    {"pitch": "A4", "start_beat": 0.0, "duration": 6.0, "velocity": 0.55},
                    {"pitch": "E5", "start_beat": 2.0, "duration": 4.0, "velocity": 0.45},
                ],
                tempo=70,
                time_signature="3/4",
                key_signature="F#_minor",
                duration_beats=6.0,
                mood=MusicMood.MYSTERIOUS,
                metadata={"instrument": "inst_synth_pad", "drone": True},
            ),
            MusicalPhrase(
                phrase_id="phrase_playful_melody_01",
                notes=[
                    {"pitch": "G4", "start_beat": 0.0, "duration": 0.5, "velocity": 0.75},
                    {"pitch": "A4", "start_beat": 0.5, "duration": 0.5, "velocity": 0.75},
                    {"pitch": "B4", "start_beat": 1.0, "duration": 0.5, "velocity": 0.8},
                    {"pitch": "C5", "start_beat": 1.5, "duration": 0.5, "velocity": 0.8},
                    {"pitch": "B4", "start_beat": 2.0, "duration": 0.5, "velocity": 0.75},
                    {"pitch": "A4", "start_beat": 2.5, "duration": 0.5, "velocity": 0.75},
                    {"pitch": "G4", "start_beat": 3.0, "duration": 1.0, "velocity": 0.7},
                ],
                tempo=128,
                time_signature="4/4",
                key_signature="G_major",
                duration_beats=4.0,
                mood=MusicMood.PLAYFUL,
                metadata={"instrument": "inst_flute"},
            ),
            MusicalPhrase(
                phrase_id="phrase_dark_bass_01",
                notes=[
                    {"pitch": "A1", "start_beat": 0.0, "duration": 1.0, "velocity": 0.9},
                    {"pitch": "A1", "start_beat": 1.0, "duration": 1.0, "velocity": 0.9},
                    {"pitch": "F1", "start_beat": 2.0, "duration": 1.0, "velocity": 0.85},
                    {"pitch": "G1", "start_beat": 3.0, "duration": 1.0, "velocity": 0.9},
                ],
                tempo=100,
                time_signature="4/4",
                key_signature="A_minor",
                duration_beats=4.0,
                mood=MusicMood.DARK,
                metadata={"instrument": "inst_electric_bass"},
            ),
            MusicalPhrase(
                phrase_id="phrase_hopeful_melody_01",
                notes=[
                    {"pitch": "C4", "start_beat": 0.0, "duration": 1.5, "velocity": 0.7},
                    {"pitch": "D4", "start_beat": 1.5, "duration": 0.5, "velocity": 0.75},
                    {"pitch": "E4", "start_beat": 2.0, "duration": 1.5, "velocity": 0.8},
                    {"pitch": "G4", "start_beat": 3.5, "duration": 0.5, "velocity": 0.85},
                    {"pitch": "C5", "start_beat": 4.0, "duration": 2.0, "velocity": 0.9},
                ],
                tempo=110,
                time_signature="4/4",
                key_signature="C_major",
                duration_beats=6.0,
                mood=MusicMood.HOPEFUL,
                metadata={"instrument": "inst_grand_piano"},
            ),
            MusicalPhrase(
                phrase_id="phrase_urgent_perc_01",
                notes=[
                    {"pitch": "C3", "start_beat": 0.0, "duration": 0.25, "velocity": 0.95},
                    {"pitch": "C3", "start_beat": 0.5, "duration": 0.25, "velocity": 0.95},
                    {"pitch": "C3", "start_beat": 1.0, "duration": 0.25, "velocity": 0.95},
                    {"pitch": "C3", "start_beat": 1.25, "duration": 0.25, "velocity": 0.95},
                    {"pitch": "C3", "start_beat": 1.75, "duration": 0.25, "velocity": 0.95},
                    {"pitch": "E3", "start_beat": 2.0, "duration": 0.5, "velocity": 1.0},
                    {"pitch": "C3", "start_beat": 3.0, "duration": 1.0, "velocity": 1.0},
                ],
                tempo=160,
                time_signature="4/4",
                key_signature="E_minor",
                duration_beats=4.0,
                mood=MusicMood.URGENT,
                metadata={"instrument": "inst_timpani", "driving": True},
            ),
        ]
        for phrase in phrases:
            self._phrases[phrase.phrase_id] = phrase

    def _seed_themes(self) -> None:
        """Seed 6 reusable musical themes."""
        themes = [
            MusicalTheme(
                theme_id="theme_hero_march",
                name="Hero March",
                mood=MusicMood.EPIC,
                genre=MusicGenre.ORCHESTRAL,
                key_signature="C_major",
                tempo=120,
                time_signature="4/4",
                primary_phrases=["phrase_epic_chord_01", "phrase_hopeful_melody_01"],
                variation_phrases=["phrase_calm_melody_01"],
                instrument_ids=[
                    "inst_violin_section",
                    "inst_french_horn",
                    "inst_timpani",
                    "inst_choir",
                ],
                intensity=DynamicIntensity.F,
                description="A stately orchestral march for the hero's entrance.",
                metadata={"arc": "hero", "energy": 0.8},
            ),
            MusicalTheme(
                theme_id="theme_dungeon_ambience",
                name="Dungeon Ambience",
                mood=MusicMood.DARK,
                genre=MusicGenre.AMBIENT,
                key_signature="A_minor",
                tempo=80,
                time_signature="4/4",
                primary_phrases=["phrase_dark_bass_01", "phrase_mysterious_pad_01"],
                variation_phrases=[],
                instrument_ids=[
                    "inst_synth_pad",
                    "inst_electric_bass",
                    "inst_cello_section",
                ],
                intensity=DynamicIntensity.MP,
                description="A low drone bed for dungeon exploration.",
                metadata={"arc": "dungeon", "energy": 0.3},
            ),
            MusicalTheme(
                theme_id="theme_battle_epic",
                name="Battle Epic",
                mood=MusicMood.TENSE,
                genre=MusicGenre.ORCHESTRAL,
                key_signature="D_minor",
                tempo=140,
                time_signature="4/4",
                primary_phrases=["phrase_tense_rhythm_01", "phrase_epic_chord_01"],
                variation_phrases=["phrase_urgent_perc_01"],
                instrument_ids=[
                    "inst_trumpet",
                    "inst_timpani",
                    "inst_snare_drum",
                    "inst_cello_section",
                ],
                intensity=DynamicIntensity.FF,
                description="Driving combat cue with brass and percussion.",
                metadata={"arc": "combat", "energy": 0.95},
            ),
            MusicalTheme(
                theme_id="theme_town_peaceful",
                name="Town Peaceful",
                mood=MusicMood.PLAYFUL,
                genre=MusicGenre.FOLK,
                key_signature="G_major",
                tempo=110,
                time_signature="4/4",
                primary_phrases=["phrase_playful_melody_01", "phrase_calm_melody_01"],
                variation_phrases=[],
                instrument_ids=[
                    "inst_flute",
                    "inst_grand_piano",
                    "inst_cello_section",
                ],
                intensity=DynamicIntensity.MF,
                description="A light folk tune for a peaceful town hub.",
                metadata={"arc": "town", "energy": 0.5},
            ),
            MusicalTheme(
                theme_id="theme_mystery_forest",
                name="Mystery Forest",
                mood=MusicMood.MYSTERIOUS,
                genre=MusicGenre.AMBIENT,
                key_signature="F#_minor",
                tempo=70,
                time_signature="3/4",
                primary_phrases=["phrase_mysterious_pad_01", "phrase_dark_bass_01"],
                variation_phrases=["phrase_calm_melody_01"],
                instrument_ids=[
                    "inst_synth_pad",
                    "inst_clarinet",
                    "inst_electric_bass",
                ],
                intensity=DynamicIntensity.P,
                description="An airy ambient bed for a mysterious forest.",
                metadata={"arc": "forest", "energy": 0.25},
            ),
            MusicalTheme(
                theme_id="theme_final_boss",
                name="Final Boss",
                mood=MusicMood.CHAOTIC,
                genre=MusicGenre.CINEMATIC,
                key_signature="E_minor",
                tempo=160,
                time_signature="4/4",
                primary_phrases=["phrase_urgent_perc_01", "phrase_tense_rhythm_01"],
                variation_phrases=["phrase_epic_chord_01", "phrase_dark_bass_01"],
                instrument_ids=[
                    "inst_trumpet",
                    "inst_french_horn",
                    "inst_timpani",
                    "inst_snare_drum",
                    "inst_electric_bass",
                    "inst_choir",
                ],
                intensity=DynamicIntensity.FF,
                description="A chaotic cinematic climax for the final boss.",
                metadata={"arc": "boss", "energy": 1.0},
            ),
        ]
        for theme in themes:
            self._themes[theme.theme_id] = theme

    def _seed_tracks(self) -> None:
        """Seed 4 composed tracks from the seeded themes."""
        track_specs = [
            ("track_overworld_theme", "Overworld Theme", "theme_hero_march",
             MusicMood.EPIC, MusicGenre.ORCHESTRAL, True,
             TransitionType.CROSSFADE),
            ("track_combat_music", "Combat Music", "theme_battle_epic",
             MusicMood.TENSE, MusicGenre.ORCHESTRAL, True,
             TransitionType.CRESCENDO),
            ("track_menu_music", "Menu Music", "theme_town_peaceful",
             MusicMood.PLAYFUL, MusicGenre.FOLK, True,
             TransitionType.CROSSFADE),
            ("track_cutscene_score", "Cutscene Score", "theme_mystery_forest",
             MusicMood.MYSTERIOUS, MusicGenre.AMBIENT, False,
             TransitionType.INTERLUDE),
        ]
        for (track_id, name, theme_id, mood, genre, loop_enabled,
             transition_type) in track_specs:
            theme = self._themes.get(theme_id)
            if theme is None:
                continue
            track = MusicTrack(
                track_id=track_id,
                name=name,
                theme_id=theme_id,
                mood=mood,
                genre=genre,
                layers=[],
                current_intensity=theme.intensity,
                status=CompositionStatus.ARRANGING,
                duration_seconds=self._compute_track_duration(theme),
                loop_enabled=loop_enabled,
                transition_type=transition_type,
                metadata={"seeded": True},
            )
            self._tracks[track_id] = track
            self._composition_counter += 1

            # Auto-arrange layers from the theme instruments.
            layer_index = 0
            for inst_id in theme.instrument_ids:
                if inst_id not in self._instruments:
                    continue
                if layer_index == 0:
                    layer_type = TrackLayer.MELODY
                elif layer_index == 1:
                    layer_type = TrackLayer.HARMONY
                elif layer_index == 2:
                    layer_type = TrackLayer.BASSLINE
                elif layer_index == 3:
                    layer_type = TrackLayer.PERCUSSION
                else:
                    layer_type = TrackLayer.PAD
                layer_id = f"layer_{track_id}_{layer_index}"
                layer = DynamicLayer(
                    layer_id=layer_id,
                    track_id=track_id,
                    layer_type=layer_type,
                    instrument_id=inst_id,
                    volume=self._instruments[inst_id].volume,
                    active=True,
                    trigger_intensity=theme.intensity,
                    metadata={"auto_arranged": True, "seeded": True},
                )
                self._layers[layer_id] = layer
                track.layers.append(layer_id)
                layer_index += 1

            track.status = CompositionStatus.READY
            self._resolve_active_layers(track)
            self._emit("track_composed", {
                "track_id": track_id,
                "theme_id": theme_id,
                "layers": len(track.layers),
                "duration_seconds": track.duration_seconds,
                "seeded": True,
            }, track_id=track_id)

    def _seed_layers(self) -> None:
        """Seed 5 additional dynamic layers tied to existing tracks."""
        extra_layers = [
            DynamicLayer(
                layer_id="layer_overworld_counter_melody",
                track_id="track_overworld_theme",
                layer_type=TrackLayer.COUNTER_MELODY,
                instrument_id="inst_flute",
                volume=0.6,
                active=False,
                trigger_intensity=DynamicIntensity.F,
                metadata={"seeded": True, "role": "accent"},
            ),
            DynamicLayer(
                layer_id="layer_combat_percussion",
                track_id="track_combat_music",
                layer_type=TrackLayer.PERCUSSION,
                instrument_id="inst_snare_drum",
                volume=0.8,
                active=True,
                trigger_intensity=DynamicIntensity.F,
                metadata={"seeded": True, "role": "drive"},
            ),
            DynamicLayer(
                layer_id="layer_combat_bassline",
                track_id="track_combat_music",
                layer_type=TrackLayer.BASSLINE,
                instrument_id="inst_electric_bass",
                volume=0.78,
                active=True,
                trigger_intensity=DynamicIntensity.MF,
                metadata={"seeded": True, "role": "low_end"},
            ),
            DynamicLayer(
                layer_id="layer_menu_pad",
                track_id="track_menu_music",
                layer_type=TrackLayer.PAD,
                instrument_id="inst_synth_pad",
                volume=0.5,
                active=True,
                trigger_intensity=DynamicIntensity.MP,
                metadata={"seeded": True, "role": "bed"},
            ),
            DynamicLayer(
                layer_id="layer_cutscene_choir",
                track_id="track_cutscene_score",
                layer_type=TrackLayer.PAD,
                instrument_id="inst_choir",
                volume=0.55,
                active=False,
                trigger_intensity=DynamicIntensity.F,
                metadata={"seeded": True, "role": "climax"},
            ),
        ]
        for layer in extra_layers:
            if layer.layer_id in self._layers:
                continue
            track = self._tracks.get(layer.track_id)
            if track is None:
                continue
            self._layers[layer.layer_id] = layer
            if layer.layer_id not in track.layers:
                track.layers.append(layer.layer_id)
        # Re-evaluate layer activation for all tracks after seeding extras.
        for track in self._tracks.values():
            self._resolve_active_layers(track)

    def _seed_mood_mappings(self) -> None:
        """Seed 5 game-context to mood mapping rules."""
        mappings = [
            MoodMapping(
                mapping_id="mapping_combat",
                game_context="combat",
                target_mood=MusicMood.TENSE,
                intensity=DynamicIntensity.F,
                transition_speed=1.5,
                duration=0.0,
                metadata={"seeded": True},
            ),
            MoodMapping(
                mapping_id="mapping_exploration",
                game_context="exploration",
                target_mood=MusicMood.CALM,
                intensity=DynamicIntensity.MP,
                transition_speed=3.0,
                duration=0.0,
                metadata={"seeded": True},
            ),
            MoodMapping(
                mapping_id="mapping_dialogue",
                game_context="dialogue",
                target_mood=MusicMood.HOPEFUL,
                intensity=DynamicIntensity.P,
                transition_speed=2.5,
                duration=0.0,
                metadata={"seeded": True},
            ),
            MoodMapping(
                mapping_id="mapping_menu",
                game_context="menu",
                target_mood=MusicMood.PLAYFUL,
                intensity=DynamicIntensity.MF,
                transition_speed=2.0,
                duration=0.0,
                metadata={"seeded": True},
            ),
            MoodMapping(
                mapping_id="mapping_victory",
                game_context="victory",
                target_mood=MusicMood.TRIUMPHANT,
                intensity=DynamicIntensity.FF,
                transition_speed=1.0,
                duration=8.0,
                metadata={"seeded": True},
            ),
        ]
        for mapping in mappings:
            self._mood_mappings[mapping.mapping_id] = mapping

    def _seed_sessions(self) -> None:
        """Seed 3 live composition sessions tied to game contexts."""
        session_specs = [
            ("session_overworld", "exploration", MusicMood.CALM,
             "track_menu_music", "theme_town_peaceful"),
            ("session_dungeon", "combat", MusicMood.TENSE,
             "track_combat_music", "theme_battle_epic"),
            ("session_boss_fight", "boss_fight", MusicMood.CHAOTIC,
             "track_combat_music", "theme_final_boss"),
        ]
        for (session_id, game_context, mood, track_id,
             theme_id) in session_specs:
            session = CompositionSession(
                session_id=session_id,
                game_context=game_context,
                current_mood=mood,
                current_track_id=track_id,
                current_theme_id=theme_id,
                metadata={"seeded": True},
            )
            session.intensity_history.append({
                "timestamp": _now(),
                "mood": mood.value,
                "track_id": track_id,
            })
            self._sessions[session_id] = session
            self._emit("session_created", {
                "session_id": session_id,
                "game_context": game_context,
                "initial_mood": mood.value,
                "track_id": track_id,
                "seeded": True,
            }, session_id=session_id)


# ---------------------------------------------------------------------------
# Pitch Transposition Helper
# ---------------------------------------------------------------------------


# Maps a note name without octave to its semitone offset within an octave.
_PITCH_CLASSES = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}

# Reverse lookup from semitone offset to a canonical sharp spelling.
_PITCH_NAMES = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
]


def _transpose_pitch(pitch: str, semitones: int) -> str:
    """Transpose a pitch string such as 'C4' by a number of semitones."""
    if not pitch:
        return pitch
    # Split the letter/prefix from the trailing octave digits.
    idx = 0
    while idx < len(pitch) and not pitch[idx].isdigit():
        idx += 1
    name_part = pitch[:idx]
    octave_part = pitch[idx:]
    if not name_part or not octave_part:
        return pitch
    try:
        octave = int(octave_part)
    except ValueError:
        return pitch
    cls = _PITCH_CLASSES.get(name_part)
    if cls is None:
        return pitch
    total = cls + semitones + (octave * 12)
    new_octave, new_cls = divmod(total, 12)
    return f"{_PITCH_NAMES[new_cls]}{new_octave}"


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_ai_music_composer() -> AIMusicComposer:
    """Factory function returning the singleton AIMusicComposer instance."""
    return AIMusicComposer.get_instance()


__all__ = [
    # Enums
    "MusicMood",
    "MusicGenre",
    "InstrumentFamily",
    "TrackLayer",
    "CompositionStatus",
    "TransitionType",
    "DynamicIntensity",
    # Data classes
    "InstrumentVoice",
    "MusicalPhrase",
    "MusicalTheme",
    "MusicTrack",
    "DynamicLayer",
    "MoodMapping",
    "CompositionSession",
    "MusicComposerConfig",
    "MusicComposerStats",
    "MusicComposerSnapshot",
    "MusicComposerEvent",
    # Main system class
    "AIMusicComposer",
    # Factory
    "get_ai_music_composer",
]
