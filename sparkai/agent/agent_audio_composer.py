"""
SparkLabs Agent - Audio Composer

AI-driven procedural audio and music generation system for game
development. Generates music tracks, sound effects, ambient layers,
and full audio scenes from high-level descriptions. Supports
genre-based composition, mood-driven atmosphere design, spatial 3D
audio configuration, and multi-layer instrument arrangement.

Architecture:
  AudioComposer
    |-- CompositionSession (tracks an active composition workflow)
    |-- MusicTrack (multi-section song with instrument arrangement)
    |-- SoundEffect (event-triggered one-shot audio with variations)
    |-- AudioClip (generic audio container for ambient/UI layers)
    |-- AudioScene (complete audio mix for a game scene)

Design Principles:
  - PROCEDURAL: algorithms generate varied, non-repetitive audio
  - GENRE-AWARE: instrument selection respects genre conventions
  - MOOD-DRIVEN: composition parameters respond to emotional context
  - SPATIAL: 3D audio positioning for immersive environments
  - ITERATIVE: variations and refinements without restarting
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AudioCategory(Enum):
    MUSIC = "music"
    SFX = "sfx"
    AMBIENT = "ambient"
    UI = "ui"
    VOICE = "voice"
    FOLEY = "foley"


class MusicGenre(Enum):
    ORCHESTRAL = "orchestral"
    ELECTRONIC = "electronic"
    CHIPTUNE = "chiptune"
    AMBIENT_DRONE = "ambient_drone"
    ROCK = "rock"
    JAZZ = "jazz"
    FOLK = "folk"
    CINEMATIC = "cinematic"
    LO_FI = "lo_fi"


class Mood(Enum):
    CALM = "calm"
    TENSE = "tense"
    HAPPY = "happy"
    SAD = "sad"
    EPIC = "epic"
    MYSTERIOUS = "mysterious"
    ENERGETIC = "energetic"
    DARK = "dark"
    PEACEFUL = "peaceful"


class InstrumentType(Enum):
    PIANO = "piano"
    STRINGS = "strings"
    BRASS = "brass"
    WOODWINDS = "woodwinds"
    PERCUSSION = "percussion"
    SYNTH_LEAD = "synth_lead"
    SYNTH_PAD = "synth_pad"
    BASS = "bass"
    GUITAR = "guitar"
    CHOIR = "choir"
    DRUMS = "drums"
    CHIPTUNE_SQUARE = "chiptune_square"
    CHIPTUNE_TRIANGLE = "chiptune_triangle"
    NOISE = "noise"


# ------------------------------------------------------------------
# Genre-to-instrument presets for automatic arrangement
# ------------------------------------------------------------------

GENRE_INSTRUMENT_PRESETS: Dict[str, List[Dict[str, Any]]] = {
    "orchestral": [
        {"instrument": InstrumentType.STRINGS.value, "volume": 0.85, "pan": 0.0, "role": "melody"},
        {"instrument": InstrumentType.BRASS.value, "volume": 0.70, "pan": 0.2, "role": "harmony"},
        {"instrument": InstrumentType.WOODWINDS.value, "volume": 0.60, "pan": -0.2, "role": "counterpoint"},
        {"instrument": InstrumentType.PERCUSSION.value, "volume": 0.75, "pan": 0.0, "role": "rhythm"},
        {"instrument": InstrumentType.CHOIR.value, "volume": 0.50, "pan": 0.0, "role": "pad"},
    ],
    "electronic": [
        {"instrument": InstrumentType.SYNTH_LEAD.value, "volume": 0.80, "pan": 0.0, "role": "melody"},
        {"instrument": InstrumentType.SYNTH_PAD.value, "volume": 0.70, "pan": 0.3, "role": "harmony"},
        {"instrument": InstrumentType.BASS.value, "volume": 0.85, "pan": 0.0, "role": "bass"},
        {"instrument": InstrumentType.DRUMS.value, "volume": 0.80, "pan": 0.0, "role": "rhythm"},
        {"instrument": InstrumentType.NOISE.value, "volume": 0.30, "pan": 0.0, "role": "fx"},
    ],
    "chiptune": [
        {"instrument": InstrumentType.CHIPTUNE_SQUARE.value, "volume": 0.80, "pan": 0.0, "role": "melody"},
        {"instrument": InstrumentType.CHIPTUNE_TRIANGLE.value, "volume": 0.75, "pan": -0.2, "role": "harmony"},
        {"instrument": InstrumentType.NOISE.value, "volume": 0.50, "pan": 0.0, "role": "percussion"},
        {"instrument": InstrumentType.SYNTH_LEAD.value, "volume": 0.60, "pan": 0.2, "role": "accent"},
    ],
    "ambient_drone": [
        {"instrument": InstrumentType.SYNTH_PAD.value, "volume": 0.85, "pan": 0.0, "role": "drone"},
        {"instrument": InstrumentType.STRINGS.value, "volume": 0.55, "pan": 0.4, "role": "texture"},
        {"instrument": InstrumentType.NOISE.value, "volume": 0.25, "pan": -0.3, "role": "atmosphere"},
        {"instrument": InstrumentType.CHOIR.value, "volume": 0.40, "pan": 0.0, "role": "pad"},
    ],
    "rock": [
        {"instrument": InstrumentType.GUITAR.value, "volume": 0.85, "pan": -0.3, "role": "lead"},
        {"instrument": InstrumentType.GUITAR.value, "volume": 0.70, "pan": 0.3, "role": "rhythm"},
        {"instrument": InstrumentType.BASS.value, "volume": 0.85, "pan": 0.0, "role": "bass"},
        {"instrument": InstrumentType.DRUMS.value, "volume": 0.90, "pan": 0.0, "role": "rhythm"},
        {"instrument": InstrumentType.PIANO.value, "volume": 0.50, "pan": 0.0, "role": "accent"},
    ],
    "jazz": [
        {"instrument": InstrumentType.PIANO.value, "volume": 0.80, "pan": 0.0, "role": "melody"},
        {"instrument": InstrumentType.BASS.value, "volume": 0.75, "pan": 0.0, "role": "bass"},
        {"instrument": InstrumentType.DRUMS.value, "volume": 0.70, "pan": 0.0, "role": "rhythm"},
        {"instrument": InstrumentType.BRASS.value, "volume": 0.65, "pan": 0.3, "role": "harmony"},
        {"instrument": InstrumentType.WOODWINDS.value, "volume": 0.55, "pan": -0.2, "role": "counterpoint"},
    ],
    "folk": [
        {"instrument": InstrumentType.GUITAR.value, "volume": 0.80, "pan": 0.0, "role": "melody"},
        {"instrument": InstrumentType.STRINGS.value, "volume": 0.60, "pan": -0.3, "role": "harmony"},
        {"instrument": InstrumentType.WOODWINDS.value, "volume": 0.55, "pan": 0.3, "role": "counterpoint"},
        {"instrument": InstrumentType.PERCUSSION.value, "volume": 0.60, "pan": 0.0, "role": "rhythm"},
        {"instrument": InstrumentType.BASS.value, "volume": 0.65, "pan": 0.0, "role": "bass"},
    ],
    "cinematic": [
        {"instrument": InstrumentType.STRINGS.value, "volume": 0.88, "pan": 0.0, "role": "melody"},
        {"instrument": InstrumentType.BRASS.value, "volume": 0.82, "pan": 0.15, "role": "harmony"},
        {"instrument": InstrumentType.CHOIR.value, "volume": 0.70, "pan": 0.0, "role": "pad"},
        {"instrument": InstrumentType.PERCUSSION.value, "volume": 0.85, "pan": 0.0, "role": "rhythm"},
        {"instrument": InstrumentType.SYNTH_PAD.value, "volume": 0.50, "pan": -0.2, "role": "texture"},
    ],
    "lo_fi": [
        {"instrument": InstrumentType.PIANO.value, "volume": 0.75, "pan": 0.0, "role": "melody"},
        {"instrument": InstrumentType.DRUMS.value, "volume": 0.70, "pan": 0.0, "role": "rhythm"},
        {"instrument": InstrumentType.BASS.value, "volume": 0.75, "pan": 0.0, "role": "bass"},
        {"instrument": InstrumentType.NOISE.value, "volume": 0.20, "pan": 0.0, "role": "vinyl_crackle"},
        {"instrument": InstrumentType.SYNTH_PAD.value, "volume": 0.40, "pan": 0.3, "role": "pad"},
    ],
}

# ------------------------------------------------------------------
# Pre-seeded music presets
# ------------------------------------------------------------------

MUSIC_PRESETS: Dict[str, Dict[str, Any]] = {
    "battle_theme": {
        "genre": MusicGenre.ORCHESTRAL.value,
        "mood": Mood.TENSE.value,
        "bpm": 140,
        "key_signature": "D_minor",
        "time_signature": "4/4",
        "duration_target": 120.0,
        "sections": [
            {"name": "intro", "start_beat": 0, "end_beat": 8, "intensity": 0.6, "description": "Percussive build-up"},
            {"name": "verse", "start_beat": 8, "end_beat": 32, "intensity": 0.8, "description": "Main battle rhythm with brass"},
            {"name": "chorus", "start_beat": 32, "end_beat": 48, "intensity": 1.0, "description": "Full orchestral climax"},
            {"name": "bridge", "start_beat": 48, "end_beat": 56, "intensity": 0.5, "description": "Tension release, strings solo"},
            {"name": "outro", "start_beat": 56, "end_beat": 64, "intensity": 0.7, "description": "Final crescendo and resolution"},
        ],
        "description": "High-intensity orchestral battle music with driving percussion",
    },
    "exploration_theme": {
        "genre": MusicGenre.AMBIENT_DRONE.value,
        "mood": Mood.CALM.value,
        "bpm": 80,
        "key_signature": "C_major",
        "time_signature": "3/4",
        "duration_target": 180.0,
        "sections": [
            {"name": "intro", "start_beat": 0, "end_beat": 8, "intensity": 0.2, "description": "Gentle pad swell"},
            {"name": "verse", "start_beat": 8, "end_beat": 40, "intensity": 0.4, "description": "Layered textures unfold"},
            {"name": "chorus", "start_beat": 40, "end_beat": 56, "intensity": 0.5, "description": "Emotional peak with strings"},
            {"name": "bridge", "start_beat": 56, "end_beat": 64, "intensity": 0.3, "description": "Return to minimal drone"},
            {"name": "outro", "start_beat": 64, "end_beat": 72, "intensity": 0.1, "description": "Fade to silence"},
        ],
        "description": "Spacious ambient drone for open-world exploration",
    },
    "menu_theme": {
        "genre": MusicGenre.LO_FI.value,
        "mood": Mood.CALM.value,
        "bpm": 90,
        "key_signature": "A_minor",
        "time_signature": "4/4",
        "duration_target": 90.0,
        "sections": [
            {"name": "intro", "start_beat": 0, "end_beat": 4, "intensity": 0.3, "description": "Vinyl crackle and piano"},
            {"name": "verse", "start_beat": 4, "end_beat": 20, "intensity": 0.4, "description": "Laid-back groove"},
            {"name": "chorus", "start_beat": 20, "end_beat": 28, "intensity": 0.5, "description": "Warm pad layer swells"},
            {"name": "bridge", "start_beat": 28, "end_beat": 32, "intensity": 0.3, "description": "Minimal transition"},
            {"name": "outro", "start_beat": 32, "end_beat": 36, "intensity": 0.2, "description": "Gentle fade-out"},
        ],
        "description": "Relaxed lo-fi beat for main menu ambiance",
    },
    "boss_theme": {
        "genre": MusicGenre.CINEMATIC.value,
        "mood": Mood.EPIC.value,
        "bpm": 160,
        "key_signature": "Eb_minor",
        "time_signature": "4/4",
        "duration_target": 150.0,
        "sections": [
            {"name": "intro", "start_beat": 0, "end_beat": 8, "intensity": 0.7, "description": "Ominous brass and low strings"},
            {"name": "verse", "start_beat": 8, "end_beat": 32, "intensity": 0.85, "description": "Driving percussion, choir enters"},
            {"name": "chorus", "start_beat": 32, "end_beat": 48, "intensity": 1.0, "description": "Full cinematic onslaught"},
            {"name": "bridge", "start_beat": 48, "end_beat": 56, "intensity": 0.6, "description": "Momentary reprieve, tension builds"},
            {"name": "outro", "start_beat": 56, "end_beat": 64, "intensity": 0.9, "description": "Powerful final statement"},
        ],
        "description": "Epic cinematic boss encounter music",
    },
    "village_theme": {
        "genre": MusicGenre.FOLK.value,
        "mood": Mood.PEACEFUL.value,
        "bpm": 100,
        "key_signature": "G_major",
        "time_signature": "6/8",
        "duration_target": 120.0,
        "sections": [
            {"name": "intro", "start_beat": 0, "end_beat": 4, "intensity": 0.3, "description": "Solo guitar intro"},
            {"name": "verse", "start_beat": 4, "end_beat": 20, "intensity": 0.5, "description": "Full folk ensemble"},
            {"name": "chorus", "start_beat": 20, "end_beat": 28, "intensity": 0.6, "description": "Lively dance rhythm"},
            {"name": "bridge", "start_beat": 28, "end_beat": 32, "intensity": 0.4, "description": "Woodwind solo"},
            {"name": "outro", "start_beat": 32, "end_beat": 36, "intensity": 0.2, "description": "Gentle resolution"},
        ],
        "description": "Warm folk melody for peaceful village scenes",
    },
}

# ------------------------------------------------------------------
# Reverb preset library
# ------------------------------------------------------------------

REVERB_PRESETS: Dict[str, Dict[str, float]] = {
    "small_room": {"room_size": 0.3, "damping": 0.5, "wet_level": 0.3, "dry_level": 0.8},
    "large_hall": {"room_size": 0.8, "damping": 0.4, "wet_level": 0.5, "dry_level": 0.6},
    "cathedral": {"room_size": 1.0, "damping": 0.3, "wet_level": 0.7, "dry_level": 0.4},
    "cave": {"room_size": 0.9, "damping": 0.6, "wet_level": 0.6, "dry_level": 0.5},
    "outdoor": {"room_size": 0.1, "damping": 0.8, "wet_level": 0.1, "dry_level": 0.95},
    "plate": {"room_size": 0.5, "damping": 0.3, "wet_level": 0.4, "dry_level": 0.7},
    "spring": {"room_size": 0.2, "damping": 0.7, "wet_level": 0.35, "dry_level": 0.75},
}


@dataclass
class AudioClip:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: str = AudioCategory.MUSIC.value
    duration_seconds: float = 0.0
    bpm: Optional[float] = None
    key_signature: str = ""
    time_signature: str = "4/4"
    mood: str = Mood.CALM.value
    instrument_layers: List[Dict[str, Any]] = field(default_factory=list)
    loop_enabled: bool = False
    fade_in: float = 0.0
    fade_out: float = 0.0
    tags: List[str] = field(default_factory=list)
    priority: int = 5
    spatial_3d: bool = False
    min_distance: float = 1.0
    max_distance: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "duration_seconds": self.duration_seconds,
            "bpm": self.bpm,
            "key_signature": self.key_signature,
            "time_signature": self.time_signature,
            "mood": self.mood,
            "instrument_layers": self.instrument_layers,
            "loop_enabled": self.loop_enabled,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "tags": self.tags,
            "priority": self.priority,
            "spatial_3d": self.spatial_3d,
            "min_distance": self.min_distance,
            "max_distance": self.max_distance,
        }


@dataclass
class MusicTrack:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    genre: str = MusicGenre.ORCHESTRAL.value
    mood: str = Mood.CALM.value
    bpm: float = 120.0
    key_signature: str = "C_major"
    time_signature: str = "4/4"
    duration_seconds: float = 0.0
    sections: List[Dict[str, Any]] = field(default_factory=list)
    instrument_arrangement: List[Dict[str, Any]] = field(default_factory=list)
    loop_point_beat: float = 0.0
    transition_out_type: str = "fade"
    variation_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "genre": self.genre,
            "mood": self.mood,
            "bpm": self.bpm,
            "key_signature": self.key_signature,
            "time_signature": self.time_signature,
            "duration_seconds": self.duration_seconds,
            "sections": self.sections,
            "instrument_arrangement": self.instrument_arrangement,
            "loop_point_beat": self.loop_point_beat,
            "transition_out_type": self.transition_out_type,
            "variation_count": self.variation_count,
        }


@dataclass
class SoundEffect:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    trigger_event: str = ""
    category: str = AudioCategory.SFX.value
    duration_seconds: float = 0.0
    pitch_range: Dict[str, float] = field(default_factory=lambda: {"min": 0.8, "max": 1.2})
    volume_range: Dict[str, float] = field(default_factory=lambda: {"min": 0.7, "max": 1.0})
    variations: List[str] = field(default_factory=list)
    spatial_blend: float = 0.0
    reverb_send: float = 0.0
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_event": self.trigger_event,
            "category": self.category,
            "duration_seconds": self.duration_seconds,
            "pitch_range": self.pitch_range,
            "volume_range": self.volume_range,
            "variations": self.variations,
            "spatial_blend": self.spatial_blend,
            "reverb_send": self.reverb_send,
            "priority": self.priority,
        }


@dataclass
class AudioScene:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_name: str = ""
    ambient_track_id: str = ""
    music_playlist: List[str] = field(default_factory=list)
    sfx_triggers: Dict[str, List[str]] = field(default_factory=dict)
    master_volume: float = 1.0
    music_volume: float = 0.8
    sfx_volume: float = 1.0
    ambient_volume: float = 0.6
    spatial_audio_enabled: bool = False
    reverb_preset: str = "small_room"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scene_name": self.scene_name,
            "ambient_track_id": self.ambient_track_id,
            "music_playlist": self.music_playlist,
            "sfx_triggers": self.sfx_triggers,
            "master_volume": self.master_volume,
            "music_volume": self.music_volume,
            "sfx_volume": self.sfx_volume,
            "ambient_volume": self.ambient_volume,
            "spatial_audio_enabled": self.spatial_audio_enabled,
            "reverb_preset": self.reverb_preset,
        }


@dataclass
class CompositionSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    genre: str = MusicGenre.ORCHESTRAL.value
    mood: str = Mood.CALM.value
    bpm: float = 120.0
    duration_target: float = 60.0
    key_signature: str = "C_major"
    started_at: float = field(default_factory=time.time)
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "genre": self.genre,
            "mood": self.mood,
            "bpm": self.bpm,
            "duration_target": self.duration_target,
            "key_signature": self.key_signature,
            "started_at": self.started_at,
            "completed": self.completed,
        }


class AudioComposer:
    """
    AI-driven procedural audio and music generation engine.

    Generates music tracks, sound effects, ambient layers, and full
    audio scenes. Supports genre-aware composition, mood-driven
    arrangement, spatial 3D audio, and iterative variation generation.
    """

    _instance: Optional["AudioComposer"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_TRACKS = 200
    MAX_SFX = 500
    MAX_SCENES = 50
    MAX_SESSIONS = 30

    def __init__(self):
        self._tracks: Dict[str, MusicTrack] = {}
        self._sfx: Dict[str, SoundEffect] = {}
        self._scenes: Dict[str, AudioScene] = {}
        self._sessions: Dict[str, CompositionSession] = {}
        self._track_count: int = 0
        self._sfx_count: int = 0
        self._scene_count: int = 0
        self._session_count: int = 0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AudioComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Section generation helpers
    # ------------------------------------------------------------------

    def _generate_default_sections(
        self, bpm: float, duration_target: float
    ) -> List[Dict[str, Any]]:
        total_beats = (bpm / 60.0) * duration_target

        intro_beats = max(4, round(total_beats * 0.1))
        verse_beats = max(8, round(total_beats * 0.35))
        chorus_beats = max(8, round(total_beats * 0.25))
        bridge_beats = max(4, round(total_beats * 0.15))
        outro_beats = max(4, round(total_beats * 0.15))

        cursor = 0
        sections = []

        section_specs = [
            ("intro", intro_beats, 0.4, "Opening build-up"),
            ("verse", verse_beats, 0.65, "Main development section"),
            ("chorus", chorus_beats, 0.9, "Climactic peak"),
            ("bridge", bridge_beats, 0.5, "Transitional break"),
            ("outro", outro_beats, 0.35, "Resolution and fade"),
        ]

        for name, beats, intensity, desc in section_specs:
            sections.append({
                "name": name,
                "start_beat": cursor,
                "end_beat": cursor + beats,
                "intensity": round(intensity, 2),
                "description": desc,
            })
            cursor += beats

        return sections

    def _get_arrangement_for_genre(self, genre: str) -> List[Dict[str, Any]]:
        preset = GENRE_INSTRUMENT_PRESETS.get(genre, GENRE_INSTRUMENT_PRESETS["orchestral"])
        return [
            {
                "instrument": entry["instrument"],
                "volume": entry["volume"],
                "pan": entry["pan"],
                "role": entry["role"],
            }
            for entry in preset
        ]

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(
        self,
        name: str,
        genre: str,
        mood: str,
        bpm: float,
        duration_target: float,
        key_signature: str,
    ) -> CompositionSession:
        if len(self._sessions) >= self.MAX_SESSIONS:
            oldest = min(
                self._sessions.keys(),
                key=lambda k: self._sessions[k].started_at,
            )
            del self._sessions[oldest]

        session = CompositionSession(
            name=name,
            genre=genre,
            mood=mood,
            bpm=bpm,
            duration_target=duration_target,
            key_signature=key_signature,
        )
        self._sessions[session.id] = session
        self._session_count += 1
        return session

    # ------------------------------------------------------------------
    # Music Composition
    # ------------------------------------------------------------------

    def compose_track(self, session_id: str) -> Optional[MusicTrack]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if len(self._tracks) >= self.MAX_TRACKS:
            oldest = min(self._tracks.keys())
            del self._tracks[oldest]

        sections = self._generate_default_sections(session.bpm, session.duration_target)
        total_beats = sections[-1]["end_beat"]
        duration = (total_beats / session.bpm) * 60.0

        arrangement = self._get_arrangement_for_genre(session.genre)

        # Apply mood to instrument volumes
        mood_volume_mod = self._mood_volume_modifier(session.mood)
        for layer in arrangement:
            layer["volume"] = round(
                min(1.0, layer["volume"] * mood_volume_mod["volume"]), 2
            )
            layer["mood_intensity"] = mood_volume_mod["intensity"]

        tempo_variation = random.uniform(-5, 5)
        actual_bpm = round(session.bpm + tempo_variation, 1)

        track = MusicTrack(
            name=session.name,
            genre=session.genre,
            mood=session.mood,
            bpm=actual_bpm,
            key_signature=session.key_signature,
            time_signature="4/4",
            duration_seconds=round(duration, 2),
            sections=sections,
            instrument_arrangement=arrangement,
            loop_point_beat=float(total_beats),
            transition_out_type="fade",
            variation_count=0,
        )

        self._tracks[track.id] = track
        self._track_count += 1

        session.completed = True
        return track

    def _mood_volume_modifier(self, mood: str) -> Dict[str, float]:
        modifiers = {
            "calm": {"volume": 0.7, "intensity": 0.3},
            "tense": {"volume": 0.85, "intensity": 0.8},
            "happy": {"volume": 0.9, "intensity": 0.65},
            "sad": {"volume": 0.6, "intensity": 0.35},
            "epic": {"volume": 0.95, "intensity": 0.95},
            "mysterious": {"volume": 0.75, "intensity": 0.45},
            "energetic": {"volume": 0.92, "intensity": 0.85},
            "dark": {"volume": 0.8, "intensity": 0.75},
            "peaceful": {"volume": 0.65, "intensity": 0.25},
        }
        return modifiers.get(mood, {"volume": 0.8, "intensity": 0.5})

    # ------------------------------------------------------------------
    # Sound Effect Generation
    # ------------------------------------------------------------------

    def generate_sfx(
        self,
        name: str,
        category: str,
        trigger_event: str,
        duration_seconds: float,
        pitch_min: float,
        pitch_max: float,
        volume_min: float,
        volume_max: float,
        variation_count: int = 3,
    ) -> SoundEffect:
        if len(self._sfx) >= self.MAX_SFX:
            oldest = min(self._sfx.keys())
            del self._sfx[oldest]

        # Generate variation ids
        variations = [uuid.uuid4().hex for _ in range(max(1, variation_count))]

        # Determine spatial blend based on category
        spatial_map = {
            AudioCategory.FOLEY.value: 0.6,
            AudioCategory.AMBIENT.value: 0.4,
            AudioCategory.SFX.value: 0.5,
            AudioCategory.UI.value: 0.0,
            AudioCategory.VOICE.value: 0.7,
            AudioCategory.MUSIC.value: 0.1,
        }
        spatial_blend = spatial_map.get(category, 0.0)

        sfx = SoundEffect(
            name=name,
            trigger_event=trigger_event,
            category=category,
            duration_seconds=duration_seconds,
            pitch_range={"min": pitch_min, "max": pitch_max},
            volume_range={"min": volume_min, "max": volume_max},
            variations=variations,
            spatial_blend=spatial_blend,
            reverb_send=0.2 if category != AudioCategory.UI.value else 0.0,
            priority=5,
        )

        self._sfx[sfx.id] = sfx
        self._sfx_count += 1
        return sfx

    # ------------------------------------------------------------------
    # Ambient Generation
    # ------------------------------------------------------------------

    def generate_ambient(
        self,
        scene_name: str,
        mood: str,
        duration_seconds: float,
        layer_count: int = 4,
    ) -> AudioClip:
        ambient_instruments = [
            InstrumentType.SYNTH_PAD,
            InstrumentType.NOISE,
            InstrumentType.STRINGS,
            InstrumentType.CHOIR,
            InstrumentType.WOODWINDS,
        ]

        layers = []
        for i in range(min(layer_count, len(ambient_instruments))):
            instrument = ambient_instruments[i]
            layers.append({
                "instrument": instrument.value,
                "volume": round(random.uniform(0.3, 0.7), 2),
                "pan": round(random.uniform(-0.5, 0.5), 2),
            })

        clip = AudioClip(
            name=f"ambient_{scene_name}",
            category=AudioCategory.AMBIENT.value,
            duration_seconds=duration_seconds,
            mood=mood,
            instrument_layers=layers,
            loop_enabled=True,
            fade_in=2.0,
            fade_out=3.0,
            tags=["ambient", mood, scene_name],
            priority=3,
            spatial_3d=False,
        )

        return clip

    # ------------------------------------------------------------------
    # Audio Scene Design
    # ------------------------------------------------------------------

    def design_audio_scene(
        self,
        scene_name: str,
        ambient_mood: str,
        music_genre: str,
        sfx_events: List[str],
    ) -> AudioScene:
        if len(self._scenes) >= self.MAX_SCENES:
            oldest = min(self._scenes.keys())
            del self._scenes[oldest]

        # Create an ambient track for the scene
        ambient = self.generate_ambient(scene_name, ambient_mood, 120.0)

        # Create a default music track for the scene
        session = self.start_session(
            f"{scene_name}_music",
            music_genre,
            ambient_mood,
            120.0,
            90.0,
            "C_major",
        )
        track = self.compose_track(session.id)

        scene = AudioScene(
            scene_name=scene_name,
            ambient_track_id=ambient.id,
            music_playlist=[track.id] if track else [],
            sfx_triggers={event: [] for event in sfx_events},
            master_volume=1.0,
            music_volume=0.8,
            sfx_volume=1.0,
            ambient_volume=0.6,
            spatial_audio_enabled=False,
            reverb_preset="large_hall",
        )

        self._scenes[scene.id] = scene
        self._scene_count += 1
        return scene

    # ------------------------------------------------------------------
    # Scene Editing Operations
    # ------------------------------------------------------------------

    def add_music_to_playlist(self, scene_id: str, track_id: str) -> Optional[AudioScene]:
        scene = self._scenes.get(scene_id)
        if scene is None or track_id not in self._tracks:
            return None

        if track_id not in scene.music_playlist:
            scene.music_playlist.append(track_id)

        return scene

    def add_sfx_trigger(
        self, scene_id: str, event_name: str, sfx_ids: List[str]
    ) -> Optional[AudioScene]:
        scene = self._scenes.get(scene_id)
        if scene is None:
            return None

        if event_name not in scene.sfx_triggers:
            scene.sfx_triggers[event_name] = []

        for sfx_id in sfx_ids:
            if sfx_id in self._sfx and sfx_id not in scene.sfx_triggers[event_name]:
                scene.sfx_triggers[event_name].append(sfx_id)

        return scene

    def mix_audio_scene(
        self,
        scene_id: str,
        master_volume: float,
        music_volume: float,
        sfx_volume: float,
        ambient_volume: float,
    ) -> Optional[AudioScene]:
        scene = self._scenes.get(scene_id)
        if scene is None:
            return None

        scene.master_volume = max(0.0, min(1.0, master_volume))
        scene.music_volume = max(0.0, min(1.0, music_volume))
        scene.sfx_volume = max(0.0, min(1.0, sfx_volume))
        scene.ambient_volume = max(0.0, min(1.0, ambient_volume))

        return scene

    # ------------------------------------------------------------------
    # Variation Generation
    # ------------------------------------------------------------------

    def generate_variation(self, track_id: str) -> Optional[MusicTrack]:
        original = self._tracks.get(track_id)
        if original is None:
            return None

        if len(self._tracks) >= self.MAX_TRACKS:
            oldest = min(self._tracks.keys())
            del self._tracks[oldest]

        # Adjust tempo slightly
        tempo_shift = random.uniform(-0.15, 0.15)
        new_bpm = round(original.bpm * (1.0 + tempo_shift), 1)

        # Shift key by a random interval
        key_options = [
            "C_major", "C_minor", "D_major", "D_minor",
            "E_major", "E_minor", "F_major", "F_minor",
            "G_major", "G_minor", "A_major", "A_minor",
            "B_major", "B_minor", "Eb_minor",
        ]
        current_key = original.key_signature
        other_keys = [k for k in key_options if k != current_key]
        new_key = random.choice(other_keys) if other_keys else current_key

        # Modify section intensities
        varied_sections = []
        for section in original.sections:
            intensity_shift = random.uniform(-0.15, 0.15)
            varied_sections.append({
                **section,
                "intensity": round(
                    max(0.0, min(1.0, section["intensity"] + intensity_shift)), 2
                ),
            })

        # Adjust instrument volumes
        varied_arrangement = []
        for layer in original.instrument_arrangement:
            vol_shift = random.uniform(-0.1, 0.1)
            varied_arrangement.append({
                **layer,
                "volume": round(max(0.0, min(1.0, layer["volume"] + vol_shift)), 2),
            })

        # Alternate transition type
        transitions = ["fade", "cut", "crossfade"]
        new_transition = random.choice(
            [t for t in transitions if t != original.transition_out_type]
        )

        variation = MusicTrack(
            name=f"{original.name}_var{original.variation_count + 1}",
            genre=original.genre,
            mood=original.mood,
            bpm=new_bpm,
            key_signature=new_key,
            time_signature=original.time_signature,
            duration_seconds=round(original.duration_seconds * random.uniform(0.9, 1.1), 2),
            sections=varied_sections,
            instrument_arrangement=varied_arrangement,
            loop_point_beat=original.loop_point_beat,
            transition_out_type=new_transition,
            variation_count=original.variation_count + 1,
        )

        self._tracks[variation.id] = variation
        self._track_count += 1
        return variation

    # ------------------------------------------------------------------
    # Track Analysis
    # ------------------------------------------------------------------

    def analyze_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        track = self._tracks.get(track_id)
        if track is None:
            return None

        # Complexity: based on number of instruments and sections
        instrument_count = len(track.instrument_arrangement)
        section_count = len(track.sections)
        complexity = round(
            (instrument_count * 0.15) + (section_count * 0.1) +
            (track.bpm / 200.0 * 0.3) + (track.duration_seconds / 300.0 * 0.15),
            2,
        )
        complexity = min(1.0, complexity)

        # Density: average intensity across sections
        if track.sections:
            density = round(
                sum(s["intensity"] for s in track.sections) / len(track.sections), 2
            )
        else:
            density = 0.0

        # Mood fit
        mood_expected = self._mood_volume_modifier(track.mood)
        actual_intensity = density
        expected_intensity = mood_expected["intensity"]
        mood_fit = round(1.0 - abs(actual_intensity - expected_intensity), 2)

        # Instrument balance
        volumes = [l["volume"] for l in track.instrument_arrangement]
        if volumes:
            avg_vol = sum(volumes) / len(volumes)
            variance = sum((v - avg_vol) ** 2 for v in volumes) / len(volumes)
            instrument_balance = round(1.0 - min(1.0, variance), 2)
        else:
            instrument_balance = 1.0

        # Suggested improvements
        suggestions = []
        if instrument_count < 3:
            suggestions.append("Consider adding more instrument layers for richness")
        if density < 0.3:
            suggestions.append("Track density is very low; consider increasing intensity")
        if density > 0.9:
            suggestions.append("Track may be too dense; consider adding quiet sections")
        if track.duration_seconds < 30:
            suggestions.append("Track is very short; consider extending duration")
        if track.duration_seconds > 600:
            suggestions.append("Track is long; consider adding more section variety")
        if not suggestions:
            suggestions.append("Track is well-balanced across all metrics")

        return {
            "complexity": complexity,
            "density": density,
            "mood_fit": mood_fit,
            "instrument_balance": instrument_balance,
            "suggested_improvements": suggestions,
        }

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_track(self, track_id: str) -> Optional[MusicTrack]:
        return self._tracks.get(track_id)

    def get_sfx(self, sfx_id: str) -> Optional[SoundEffect]:
        return self._sfx.get(sfx_id)

    def get_scene(self, scene_id: str) -> Optional[AudioScene]:
        return self._scenes.get(scene_id)

    def get_session(self, session_id: str) -> Optional[CompositionSession]:
        return self._sessions.get(session_id)

    def list_tracks(self) -> List[MusicTrack]:
        return list(self._tracks.values())

    def list_sfx(self) -> List[SoundEffect]:
        return list(self._sfx.values())

    def list_scenes(self) -> List[AudioScene]:
        return list(self._scenes.values())

    def list_sessions(self) -> List[CompositionSession]:
        return list(self._sessions.values())

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        tracks_by_genre: Dict[str, int] = {}
        for t in self._tracks.values():
            genre = t.genre
            tracks_by_genre[genre] = tracks_by_genre.get(genre, 0) + 1

        tracks_by_mood: Dict[str, int] = {}
        for t in self._tracks.values():
            mood = t.mood
            tracks_by_mood[mood] = tracks_by_mood.get(mood, 0) + 1

        total_duration = sum(t.duration_seconds for t in self._tracks.values())
        average_track_duration = round(
            total_duration / max(1, len(self._tracks)), 2
        )

        total_instrument_layers = sum(
            len(t.instrument_arrangement) for t in self._tracks.values()
        )

        sfx_by_category: Dict[str, int] = {}
        for s in self._sfx.values():
            cat = s.category
            sfx_by_category[cat] = sfx_by_category.get(cat, 0) + 1

        return {
            "total_tracks": len(self._tracks),
            "total_sfx": len(self._sfx),
            "total_scenes": len(self._scenes),
            "total_sessions": len(self._sessions),
            "tracks_by_genre": tracks_by_genre,
            "tracks_by_mood": tracks_by_mood,
            "average_track_duration": average_track_duration,
            "total_instrument_layers": total_instrument_layers,
            "sfx_by_category": sfx_by_category,
        }


def get_audio_composer() -> AudioComposer:
    return AudioComposer.get_instance()