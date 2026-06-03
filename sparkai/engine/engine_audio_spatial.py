"""
SparkLabs Engine - AI-Driven Spatial Audio System

Runtime spatial audio engine providing 3D sound source management,
listener tracking, reverb zone simulation, occlusion calculation,
Doppler effect processing, room acoustics simulation, and procedural
audio synthesis. Manages audio sources through spatial positioning,
distance-based attenuation curves, and real-time parameter modulation.

Architecture:
  EngineAudioSpatial
    |-- SourceManager (audio source lifecycle and state management)
    |-- ListenerTracker (listener position, orientation, and velocity)
    |-- ReverbZoneSimulator (environmental reverb zone queries)
    |-- OcclusionModel (ray-based obstruction between source and listener)
    |-- DopplerProcessor (pitch shifting from relative velocity)
    |-- ProceduralSynthesizer (runtime waveform generation)
    |-- QualityController (sample rate and processing fidelity)

Spatial Audio Features:
  - SOURCES: point, ambient, music, voice, and UI sound emitters
  - LISTENERS: 3D position, forward/up orientation, velocity
  - REVERB: preset-based environmental reverb zones
  - OCCLUSION: ray-based obstruction modeling between sources and listeners
  - DOPPLER: frequency shift from relative source-listener velocity
  - ROOM ACOUSTICS: wall material reflection and room dimension modeling
  - PROCEDURAL: runtime waveform synthesis with ADSR envelopes and filtering
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Quality preset constants
# ---------------------------------------------------------------------------

_QUALITY_PRESETS: Dict[str, Dict[str, Any]] = {
    "low": {
        "sample_rate": 22050,
        "max_rays": 4,
        "max_harmonics": 8,
        "reverb_resolution": 0.1,
    },
    "medium": {
        "sample_rate": 44100,
        "max_rays": 16,
        "max_harmonics": 16,
        "reverb_resolution": 0.05,
    },
    "high": {
        "sample_rate": 96000,
        "max_rays": 64,
        "max_harmonics": 32,
        "reverb_resolution": 0.01,
    },
}

_WALL_MATERIAL_ABSORPTION: Dict[str, float] = {
    "concrete": 0.02,
    "brick": 0.04,
    "wood": 0.10,
    "glass": 0.03,
    "carpet": 0.30,
    "curtain": 0.40,
    "acoustic_foam": 0.70,
    "drywall": 0.05,
    "stone": 0.01,
    "metal": 0.01,
    "water": 0.50,
    "open_air": 1.0,
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AudioSourceType(Enum):
    """Classification of audio sources by spatial behavior and mixing category."""
    POINT = "point"
    AMBIENT = "ambient"
    MUSIC = "music"
    VOICE = "voice"
    UI = "ui"


class RolloffMode(Enum):
    """Distance-based attenuation curve shape."""
    LOGARITHMIC = "logarithmic"
    LINEAR = "linear"
    CUSTOM = "custom"


class WaveformType(Enum):
    """Oscillator waveform shapes for procedural sound generation."""
    SINE = "sine"
    SQUARE = "square"
    SAWTOOTH = "sawtooth"
    TRIANGLE = "triangle"
    NOISE = "noise"
    CUSTOM = "custom"


class ReverbPreset(Enum):
    """Environmental reverb presets with predefined acoustic characteristics."""
    GENERIC = "generic"
    PADDED_CELL = "padded_cell"
    ROOM = "room"
    BATHROOM = "bathroom"
    LIVING_ROOM = "living_room"
    STONE_ROOM = "stone_room"
    AUDITORIUM = "auditorium"
    CONCERT_HALL = "concert_hall"
    CAVE = "cave"
    ARENA = "arena"
    HANGAR = "hangar"
    CARPETED_HALLWAY = "carpeted_hallway"
    HALLWAY = "hallway"
    STONE_CORRIDOR = "stone_corridor"
    ALLEY = "alley"
    FOREST = "forest"
    CITY = "city"
    MOUNTAINS = "mountains"
    QUARRY = "quarry"
    PLAIN = "plain"
    PARKING_LOT = "parking_lot"
    SEWER_PIPE = "sewer_pipe"
    UNDERWATER = "underwater"

    @property
    def default_decay_time(self) -> float:
        """Returns the typical RT60 decay time in seconds for this preset."""
        return {
            ReverbPreset.GENERIC: 1.5,
            ReverbPreset.PADDED_CELL: 0.1,
            ReverbPreset.ROOM: 0.5,
            ReverbPreset.BATHROOM: 0.8,
            ReverbPreset.LIVING_ROOM: 0.6,
            ReverbPreset.STONE_ROOM: 1.2,
            ReverbPreset.AUDITORIUM: 2.5,
            ReverbPreset.CONCERT_HALL: 3.0,
            ReverbPreset.CAVE: 4.0,
            ReverbPreset.ARENA: 3.5,
            ReverbPreset.HANGAR: 5.0,
            ReverbPreset.CARPETED_HALLWAY: 0.3,
            ReverbPreset.HALLWAY: 1.0,
            ReverbPreset.STONE_CORRIDOR: 1.8,
            ReverbPreset.ALLEY: 1.3,
            ReverbPreset.FOREST: 1.0,
            ReverbPreset.CITY: 1.2,
            ReverbPreset.MOUNTAINS: 2.0,
            ReverbPreset.QUARRY: 2.3,
            ReverbPreset.PLAIN: 0.2,
            ReverbPreset.PARKING_LOT: 0.8,
            ReverbPreset.SEWER_PIPE: 1.6,
            ReverbPreset.UNDERWATER: 3.5,
        }[self]

    @property
    def default_density(self) -> float:
        """Returns the default echo density factor for this preset (0-1)."""
        return {
            ReverbPreset.GENERIC: 0.5,
            ReverbPreset.PADDED_CELL: 0.1,
            ReverbPreset.ROOM: 0.3,
            ReverbPreset.BATHROOM: 0.6,
            ReverbPreset.LIVING_ROOM: 0.4,
            ReverbPreset.STONE_ROOM: 0.7,
            ReverbPreset.AUDITORIUM: 0.8,
            ReverbPreset.CONCERT_HALL: 0.9,
            ReverbPreset.CAVE: 0.7,
            ReverbPreset.ARENA: 0.8,
            ReverbPreset.HANGAR: 0.6,
            ReverbPreset.CARPETED_HALLWAY: 0.2,
            ReverbPreset.HALLWAY: 0.5,
            ReverbPreset.STONE_CORRIDOR: 0.6,
            ReverbPreset.ALLEY: 0.4,
            ReverbPreset.FOREST: 0.3,
            ReverbPreset.CITY: 0.5,
            ReverbPreset.MOUNTAINS: 0.4,
            ReverbPreset.QUARRY: 0.5,
            ReverbPreset.PLAIN: 0.1,
            ReverbPreset.PARKING_LOT: 0.3,
            ReverbPreset.SEWER_PIPE: 0.7,
            ReverbPreset.UNDERWATER: 0.9,
        }[self]


class FilterType(Enum):
    """Audio filter types for procedural sound shaping."""
    LOW_PASS = "low_pass"
    HIGH_PASS = "high_pass"
    BAND_PASS = "band_pass"
    NOTCH = "notch"
    ALL_PASS = "all_pass"


class PlaybackState(Enum):
    """Playback state of an audio source instance."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    FADING_IN = "fading_in"
    FADING_OUT = "fading_out"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AudioSource:
    """Spatial audio source with 3D positioning and distance-based attenuation.

    Represents a sound emitter in the game world. Supports looping, pitch
    variation, Doppler effect level, 3D spread angle, and per-source
    rolloff. Tracks playback state and current playback time.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    source_type: AudioSourceType = AudioSourceType.POINT
    audio_clip: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    is_looping: bool = False
    volume: float = 1.0
    pitch: float = 1.0
    min_distance: float = 1.0
    max_distance: float = 100.0
    spatial_blend: float = 1.0
    doppler_level: float = 1.0
    spread: float = 0.0
    rolloff_mode: RolloffMode = RolloffMode.LOGARITHMIC
    priority: int = 128
    is_playing: bool = False
    current_time: float = 0.0
    attenuation_curve: Dict[float, float] = field(default_factory=dict)
    state: PlaybackState = PlaybackState.IDLE
    fade_timer: float = 0.0
    fade_duration: float = 0.0
    fade_start_volume: float = 1.0
    fade_target_volume: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type.value,
            "audio_clip": self.audio_clip,
            "position": list(self.position),
            "is_looping": self.is_looping,
            "volume": round(self.volume, 2),
            "pitch": round(self.pitch, 2),
            "min_distance": round(self.min_distance, 1),
            "max_distance": round(self.max_distance, 1),
            "spatial_blend": round(self.spatial_blend, 2),
            "doppler_level": round(self.doppler_level, 2),
            "spread": round(self.spread, 2),
            "rolloff_mode": self.rolloff_mode.value,
            "priority": self.priority,
            "is_playing": self.is_playing,
            "current_time": round(self.current_time, 3),
            "state": self.state.value,
            "fade_timer": round(self.fade_timer, 3),
            "fade_duration": round(self.fade_duration, 3),
            "created_at": self.created_at,
        }


@dataclass
class AudioListener:
    """Audio listener representing the player's ears in 3D space.

    Tracks position, orientation (forward and up vectors), velocity
    for Doppler calculations, and a per-listener volume multiplier.
    """

    listener_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    forward: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    up: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    volume_multiplier: float = 1.0
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "listener_id": self.listener_id,
            "position": list(self.position),
            "forward": list(self.forward),
            "up": list(self.up),
            "velocity": list(self.velocity),
            "volume_multiplier": round(self.volume_multiplier, 2),
            "updated_at": self.updated_at,
        }


@dataclass
class AudioReverbZone:
    """Spherical or box-shaped environmental reverb zone.

    When a sound source or listener is inside this zone, the reverb
    parameters are applied to the audio mix. Supports industry-standard
    reverb presets and fine-grained acoustic parameter control.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 10.0
    preset: ReverbPreset = ReverbPreset.GENERIC
    room_effect: float = 0.5
    room_hf: float = 0.5
    decay_time: float = 1.5
    decay_hf_ratio: float = 0.5
    reflections: float = 0.3
    reverb_level: float = 0.0
    diffusion: float = 1.0
    density: float = 1.0
    hf_reference: float = 5000.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "position": list(self.position),
            "radius": round(self.radius, 1),
            "preset": self.preset.value,
            "room_effect": round(self.room_effect, 2),
            "room_hf": round(self.room_hf, 2),
            "decay_time": round(self.decay_time, 2),
            "decay_hf_ratio": round(self.decay_hf_ratio, 2),
            "reflections": round(self.reflections, 2),
            "reverb_level": round(self.reverb_level, 2),
            "diffusion": round(self.diffusion, 2),
            "density": round(self.density, 2),
            "hf_reference": round(self.hf_reference, 0),
            "created_at": self.created_at,
        }


@dataclass
class AudioOcclusion:
    """Result of an occlusion raycast between a source and listener.

    Stores the number of rays cast, how many were blocked, and a
    computed occlusion level from 0.0 (fully open) to 1.0 (fully
    blocked).
    """

    source_id: str = ""
    occluded: bool = False
    occlusion_level: float = 0.0
    rays_cast: int = 0
    rays_hit: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "occluded": self.occluded,
            "occlusion_level": round(self.occlusion_level, 3),
            "rays_cast": self.rays_cast,
            "rays_hit": self.rays_hit,
            "timestamp": self.timestamp,
        }


@dataclass
class ProceduralSound:
    """Configurable procedural sound definition for runtime synthesis.

    Supports waveform selection, harmonic series, ADSR envelope shaping,
    noise modulation, and real-time filtering. Can be synthesized on
    demand without pre-recorded audio assets.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    waveform_type: WaveformType = WaveformType.SINE
    frequency: float = 440.0
    amplitude: float = 1.0
    phase: float = 0.0
    duration: float = 1.0
    harmonic_count: int = 1
    noise_amount: float = 0.0
    envelope_attack: float = 0.01
    envelope_decay: float = 0.1
    envelope_sustain: float = 0.7
    envelope_release: float = 0.3
    filter_type: FilterType = FilterType.LOW_PASS
    filter_cutoff: float = 20000.0
    filter_resonance: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "waveform_type": self.waveform_type.value,
            "frequency": round(self.frequency, 1),
            "amplitude": round(self.amplitude, 3),
            "phase": round(self.phase, 3),
            "duration": round(self.duration, 3),
            "harmonic_count": self.harmonic_count,
            "noise_amount": round(self.noise_amount, 3),
            "envelope_attack": round(self.envelope_attack, 4),
            "envelope_decay": round(self.envelope_decay, 4),
            "envelope_sustain": round(self.envelope_sustain, 3),
            "envelope_release": round(self.envelope_release, 4),
            "filter_type": self.filter_type.value,
            "filter_cutoff": round(self.filter_cutoff, 1),
            "filter_resonance": round(self.filter_resonance, 3),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Singleton Engine
# ---------------------------------------------------------------------------


class EngineAudioSpatial:
    """AI-driven spatial audio system for 3D sound management.

    Manages audio sources, listeners, reverb zones, occlusion queries,
    Doppler effect processing, room acoustics simulation, and procedural
    sound synthesis. Provides master and per-category volume control
    with configurable quality presets.

    Thread-safe via a reentrant lock. Use get_audio_spatial() or
    EngineAudioSpatial.get_instance() to obtain the singleton.
    """

    _instance: Optional["EngineAudioSpatial"] = None
    _lock = threading.RLock()

    _SPEED_OF_SOUND: float = 343.0
    _MIN_FREQUENCY: float = 20.0
    _MAX_FREQUENCY: float = 20000.0
    _MAX_ATTENUATION_DISTANCE: float = 10000.0

    def __new__(cls) -> "EngineAudioSpatial":
        """Thread-safe singleton construction with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initializes internal state on first construction only."""
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._sources: Dict[str, AudioSource] = {}
        self._listeners: Dict[str, AudioListener] = {}
        self._reverb_zones: Dict[str, AudioReverbZone] = {}
        self._procedural_sounds: Dict[str, ProceduralSound] = {}
        self._occlusion_cache: Dict[str, AudioOcclusion] = {}
        self._active_source_ids: List[str] = []

        self._master_volume: float = 1.0
        self._category_volumes: Dict[AudioSourceType, float] = {
            at: 1.0 for at in AudioSourceType
        }

        self._quality: str = "medium"
        self._sample_rate: int = _QUALITY_PRESETS["medium"]["sample_rate"]
        self._max_rays: int = _QUALITY_PRESETS["medium"]["max_rays"]
        self._max_harmonics: int = _QUALITY_PRESETS["medium"]["max_harmonics"]
        self._reverb_resolution: float = _QUALITY_PRESETS["medium"]["reverb_resolution"]

        self._cpu_load: float = 0.0
        self._memory_usage: int = 0
        self._total_wave_memory: int = 0
        self._tick_count: int = 0
        self._total_sources_created: int = 0

        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EngineAudioSpatial":
        """Returns the singleton EngineAudioSpatial instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_uid_stub() -> str:
        """Returns a unique identifier as a hex string."""
        return uuid.uuid4().hex

    @staticmethod
    def _distance(
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
    ) -> float:
        """Computes Euclidean distance between two 3D points."""
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        dz = a[2] - b[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @staticmethod
    def _normalize(
        v: Tuple[float, float, float],
    ) -> Tuple[float, float, float]:
        """Returns a normalized copy of a 3D vector."""
        length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
        if length < 1e-10:
            return (0.0, 0.0, 0.0)
        return (v[0] / length, v[1] / length, v[2] / length)

    @staticmethod
    def _dot(
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
    ) -> float:
        """Returns the dot product of two 3D vectors."""
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def _compute_attenuation(
        self,
        distance: float,
        source: AudioSource,
    ) -> float:
        """Computes the volume attenuation factor based on distance and rolloff mode.

        Args:
            distance: Straight-line distance between source and listener.
            source: The audio source with rolloff parameters.

        Returns:
            A volume multiplier between 0.0 and 1.0.
        """
        if distance <= source.min_distance:
            return 1.0

        if distance >= source.max_distance:
            return 0.0

        if source.rolloff_mode == RolloffMode.LINEAR:
            normalized = (distance - source.min_distance) / (
                source.max_distance - source.min_distance
            )
            return 1.0 - normalized

        if source.rolloff_mode == RolloffMode.CUSTOM and source.attenuation_curve:
            sorted_keys = sorted(source.attenuation_curve.keys())
            if not sorted_keys:
                return 1.0
            if distance <= sorted_keys[0]:
                return source.attenuation_curve[sorted_keys[0]]
            if distance >= sorted_keys[-1]:
                return source.attenuation_curve[sorted_keys[-1]]
            for i in range(len(sorted_keys) - 1):
                if sorted_keys[i] <= distance <= sorted_keys[i + 1]:
                    t = (distance - sorted_keys[i]) / (
                        sorted_keys[i + 1] - sorted_keys[i]
                    )
                    v0 = source.attenuation_curve[sorted_keys[i]]
                    v1 = source.attenuation_curve[sorted_keys[i + 1]]
                    return v0 + (v1 - v0) * t
            return 1.0

        # Default: logarithmic rolloff
        normalized = (distance - source.min_distance) / (
            source.max_distance - source.min_distance
        )
        return 1.0 / (1.0 + normalized * 3.0)

    def _get_listener_view_angle(
        self,
        listener: AudioListener,
        source_position: Tuple[float, float, float],
    ) -> float:
        """Computes the angle in radians between the listener's forward
        direction and the direction to the source position.

        Returns:
            Angle in radians between 0 and pi.
        """
        to_source = (
            source_position[0] - listener.position[0],
            source_position[1] - listener.position[1],
            source_position[2] - listener.position[2],
        )
        to_source_norm = self._normalize(to_source)
        forward_norm = self._normalize(listener.forward)
        dot_val = self._dot(forward_norm, to_source_norm)
        dot_val = max(-1.0, min(1.0, dot_val))
        return math.acos(dot_val)

    def _estimate_memory(self) -> None:
        """Updates the internal memory usage estimate based on active sources."""
        source_mem = len(self._sources) * 2048
        reverb_mem = len(self._reverb_zones) * 512
        procedural_mem = len(self._procedural_sounds) * 1024
        listener_mem = len(self._listeners) * 256
        self._memory_usage = source_mem + reverb_mem + procedural_mem + listener_mem
        self._total_wave_memory = len(self._procedural_sounds) * self._sample_rate * 2

    # ------------------------------------------------------------------
    # Public API: Audio Source Management
    # ------------------------------------------------------------------

    def create_audio_source(
        self,
        name: str,
        source_type: str = "point",
        audio_clip: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        is_looping: bool = False,
        volume: float = 1.0,
        pitch: float = 1.0,
        min_distance: float = 1.0,
        max_distance: float = 100.0,
        spatial_blend: float = 1.0,
        rolloff_mode: str = "logarithmic",
    ) -> AudioSource:
        """Creates and registers a spatial audio source.

        Args:
            name: Human-readable name for the source.
            source_type: Category of the audio source ('point', 'ambient',
                'music', 'voice', 'ui').
            audio_clip: Identifier of the audio clip to play.
            position: 3D world position as (x, y, z).
            is_looping: Whether the source loops after finishing.
            volume: Playback volume between 0.0 and 1.0.
            pitch: Playback pitch multiplier (0.1 to 3.0).
            min_distance: Distance below which volume is at maximum.
            max_distance: Distance above which volume is silent.
            spatial_blend: 2D/3D blend factor (0.0 = 2D, 1.0 = 3D).
            rolloff_mode: Attenuation curve type ('logarithmic', 'linear', 'custom').

        Returns:
            The newly created AudioSource instance.
        """
        try:
            st = AudioSourceType(source_type.lower())
        except ValueError:
            st = AudioSourceType.POINT

        try:
            rm = RolloffMode(rolloff_mode.lower())
        except ValueError:
            rm = RolloffMode.LOGARITHMIC

        source = AudioSource(
            name=name,
            source_type=st,
            audio_clip=audio_clip,
            position=position,
            is_looping=is_looping,
            volume=max(0.0, min(1.0, volume)),
            pitch=max(0.1, min(3.0, pitch)),
            min_distance=max(0.1, min_distance),
            max_distance=max(min_distance + 0.1, max_distance),
            spatial_blend=max(0.0, min(1.0, spatial_blend)),
            rolloff_mode=rm,
            priority=128,
        )

        with self._lock:
            self._sources[source.id] = source
            self._total_sources_created += 1
            self._estimate_memory()

        return source

    def play_source(
        self,
        source_id: str,
        fade_in_time: float = 0.0,
    ) -> bool:
        """Starts playback of an audio source.

        Args:
            source_id: The unique identifier of the source to play.
            fade_in_time: Duration in seconds for volume fade-in. 0 means
                instant.

        Returns:
            True if the source was found and started, False otherwise.
        """
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False

            if fade_in_time > 0.0:
                source.state = PlaybackState.FADING_IN
                source.fade_duration = max(0.001, fade_in_time)
                source.fade_timer = 0.0
                source.fade_start_volume = 0.0
                source.fade_target_volume = source.volume
                source.volume = 0.0
            else:
                source.state = PlaybackState.PLAYING

            source.is_playing = True
            source.current_time = 0.0

            if source_id not in self._active_source_ids:
                self._active_source_ids.append(source_id)

            return True

    def stop_source(
        self,
        source_id: str,
        fade_out_time: float = 0.0,
    ) -> bool:
        """Stops playback of an audio source.

        Args:
            source_id: The unique identifier of the source to stop.
            fade_out_time: Duration in seconds for volume fade-out. 0 means
                instant.

        Returns:
            True if the source was found and stopped, False otherwise.
        """
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False

            if fade_out_time > 0.0:
                source.state = PlaybackState.FADING_OUT
                source.fade_duration = max(0.001, fade_out_time)
                source.fade_timer = 0.0
                source.fade_start_volume = source.volume
                source.fade_target_volume = 0.0
            else:
                source.state = PlaybackState.IDLE
                source.is_playing = False
                source.current_time = 0.0
                if source_id in self._active_source_ids:
                    self._active_source_ids.remove(source_id)

            return True

    def pause_source(self, source_id: str) -> bool:
        """Pauses playback of an audio source.

        Args:
            source_id: The unique identifier of the source to pause.

        Returns:
            True if the source was found and paused, False otherwise.
        """
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False
            if source.state not in (PlaybackState.PLAYING, PlaybackState.FADING_IN):
                return False
            source.state = PlaybackState.PAUSED
            source.is_playing = False
            return True

    def resume_source(self, source_id: str) -> bool:
        """Resumes playback of a paused audio source.

        Args:
            source_id: The unique identifier of the source to resume.

        Returns:
            True if the source was found and resumed, False otherwise.
        """
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False
            if source.state != PlaybackState.PAUSED:
                return False
            source.state = PlaybackState.PLAYING
            source.is_playing = True
            if source_id not in self._active_source_ids:
                self._active_source_ids.append(source_id)
            return True

    def set_source_position(
        self,
        source_id: str,
        position: Tuple[float, float, float],
    ) -> bool:
        """Updates the 3D position of an audio source.

        Args:
            source_id: The unique identifier of the source.
            position: New 3D position as (x, y, z).

        Returns:
            True if the source was found and updated, False otherwise.
        """
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False
            source.position = (float(position[0]), float(position[1]), float(position[2]))
            return True

    def get_active_sources(self) -> List[str]:
        """Returns the list of source IDs currently in a playing or paused state.

        Returns:
            A list of active source ID strings.
        """
        with self._lock:
            return list(self._active_source_ids)

    def remove_source(self, source_id: str) -> bool:
        """Removes an audio source from the system.

        Args:
            source_id: The unique identifier of the source to remove.

        Returns:
            True if the source was found and removed, False otherwise.
        """
        with self._lock:
            source = self._sources.pop(source_id, None)
            if source is None:
                return False
            if source_id in self._active_source_ids:
                self._active_source_ids.remove(source_id)
            keys_to_remove = [
                k for k, v in self._occlusion_cache.items() if v.source_id == source_id
            ]
            for k in keys_to_remove:
                del self._occlusion_cache[k]
            self._estimate_memory()
            return True

    # ------------------------------------------------------------------
    # Public API: Listener Management
    # ------------------------------------------------------------------

    def create_listener(
        self,
        listener_id: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        forward: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        up: Tuple[float, float, float] = (0.0, 1.0, 0.0),
    ) -> AudioListener:
        """Creates and registers an audio listener.

        Args:
            listener_id: Custom identifier for the listener. Auto-generated
                if empty.
            position: 3D world position as (x, y, z).
            forward: Forward direction vector.
            up: Up direction vector.

        Returns:
            The newly created AudioListener instance.
        """
        lid = listener_id if listener_id else self._generate_uid_stub()

        forward_norm = self._normalize(forward)
        up_norm = self._normalize(up)

        listener = AudioListener(
            listener_id=lid,
            position=position,
            forward=forward_norm,
            up=up_norm,
        )

        with self._lock:
            self._listeners[lid] = listener
            self._estimate_memory()

        return listener

    def set_listener_position(
        self,
        listener_id: str,
        position: Tuple[float, float, float],
        forward: Optional[Tuple[float, float, float]] = None,
        up: Optional[Tuple[float, float, float]] = None,
        velocity: Optional[Tuple[float, float, float]] = None,
    ) -> bool:
        """Updates the position, orientation, and velocity of a listener.

        Args:
            listener_id: The unique identifier of the listener.
            position: New 3D position as (x, y, z).
            forward: Optional new forward direction vector.
            up: Optional new up direction vector.
            velocity: Optional new velocity vector for Doppler calculations.

        Returns:
            True if the listener was found and updated, False otherwise.
        """
        with self._lock:
            listener = self._listeners.get(listener_id)
            if listener is None:
                return False

            listener.position = (
                float(position[0]),
                float(position[1]),
                float(position[2]),
            )

            if forward is not None:
                listener.forward = self._normalize(forward)

            if up is not None:
                listener.up = self._normalize(up)

            if velocity is not None:
                listener.velocity = (
                    float(velocity[0]),
                    float(velocity[1]),
                    float(velocity[2]),
                )

            listener.updated_at = _time_module.time

            return True

    def remove_listener(self, listener_id: str) -> bool:
        """Removes an audio listener from the system.

        Args:
            listener_id: The unique identifier of the listener to remove.

        Returns:
            True if the listener was found and removed, False otherwise.
        """
        with self._lock:
            if listener_id not in self._listeners:
                return False
            del self._listeners[listener_id]
            self._estimate_memory()
            return True

    # ------------------------------------------------------------------
    # Public API: Reverb Zone Management
    # ------------------------------------------------------------------

    def create_reverb_zone(
        self,
        name: str,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        radius: float = 10.0,
        preset: str = "generic",
        room_effect: float = 0.5,
        decay_time: float = 1.5,
    ) -> AudioReverbZone:
        """Creates a reverb zone at a 3D position.

        Args:
            name: Human-readable name for the zone.
            position: 3D world position as (x, y, z).
            radius: Radius of the spherical zone.
            preset: Reverb preset name (see ReverbPreset enum).
            room_effect: Room effect level from 0.0 to 1.0.
            decay_time: RT60 decay time in seconds.

        Returns:
            The newly created AudioReverbZone instance.
        """
        try:
            rp = ReverbPreset(preset.lower())
        except ValueError:
            rp = ReverbPreset.GENERIC

        used_decay = decay_time if decay_time > 0.0 else rp.default_decay_time

        zone = AudioReverbZone(
            name=name,
            position=position,
            radius=max(0.1, radius),
            preset=rp,
            room_effect=max(0.0, min(1.0, room_effect)),
            decay_time=used_decay,
            density=rp.default_density,
        )

        with self._lock:
            self._reverb_zones[zone.id] = zone
            self._estimate_memory()

        return zone

    def remove_reverb_zone(self, zone_id: str) -> bool:
        """Removes a reverb zone from the system.

        Args:
            zone_id: The unique identifier of the zone to remove.

        Returns:
            True if the zone was found and removed, False otherwise.
        """
        with self._lock:
            if zone_id not in self._reverb_zones:
                return False
            del self._reverb_zones[zone_id]
            self._estimate_memory()
            return True

    def get_reverb_zones_at_position(
        self,
        position: Tuple[float, float, float],
    ) -> List[AudioReverbZone]:
        """Returns all reverb zones that contain the given position.

        Args:
            position: 3D world position as (x, y, z).

        Returns:
            A list of AudioReverbZone instances containing the position.
        """
        result: List[AudioReverbZone] = []
        with self._lock:
            for zone in self._reverb_zones.values():
                if self._distance(position, zone.position) <= zone.radius:
                    result.append(zone)
        return result

    # ------------------------------------------------------------------
    # Public API: Procedural Sound Management
    # ------------------------------------------------------------------

    def create_procedural_sound(
        self,
        name: str,
        waveform_type: str = "sine",
        frequency: float = 440.0,
        amplitude: float = 1.0,
        duration: float = 1.0,
        harmonic_count: int = 1,
    ) -> ProceduralSound:
        """Creates a procedural sound definition for runtime synthesis.

        Args:
            name: Human-readable name for the sound.
            waveform_type: Oscillator waveform ('sine', 'square', 'sawtooth',
                'triangle', 'noise', 'custom').
            frequency: Base frequency in Hz.
            amplitude: Peak amplitude from 0.0 to 1.0.
            duration: Duration in seconds.
            harmonic_count: Number of harmonic partials above the fundamental.

        Returns:
            The newly created ProceduralSound instance.
        """
        try:
            wt = WaveformType(waveform_type.lower())
        except ValueError:
            wt = WaveformType.SINE

        freq = max(self._MIN_FREQUENCY, min(self._MAX_FREQUENCY, frequency))
        actual_harmonic_count = min(harmonic_count, self._max_harmonics)

        sound = ProceduralSound(
            name=name,
            waveform_type=wt,
            frequency=freq,
            amplitude=max(0.0, min(1.0, amplitude)),
            duration=max(0.001, duration),
            harmonic_count=actual_harmonic_count,
        )

        with self._lock:
            self._procedural_sounds[sound.id] = sound
            self._estimate_memory()

        return sound

    def synthesize_procedural(
        self,
        sound_id: str,
        duration_override: Optional[float] = None,
    ) -> bytes:
        """Synthesizes a procedural sound into a raw PCM byte buffer.

        Generates a waveform based on the sound's parameters using additive
        synthesis for harmonic content, an ADSR amplitude envelope, and
        optional white noise blending. The result is a 16-bit signed integer
        mono PCM buffer at the current quality sample rate.

        Args:
            sound_id: The unique identifier of the procedural sound.
            duration_override: Optional duration in seconds to override the
                sound's duration.

        Returns:
            A bytes object containing raw 16-bit PCM audio data.
        """
        with self._lock:
            sound = self._procedural_sounds.get(sound_id)
            if sound is None:
                return b""

            duration = duration_override if duration_override is not None else sound.duration
            duration = max(0.001, duration)
            total_frames = int(self._sample_rate * duration)

            # Build the harmonic profile.
            harmonic_multipliers: List[Tuple[float, float]] = []
            if sound.waveform_type == WaveformType.SINE:
                harmonic_multipliers = [(1.0, 1.0)]
                for h in range(1, sound.harmonic_count):
                    harmonic_multipliers.append((float(h + 1), 1.0 / (h + 1)))
            elif sound.waveform_type == WaveformType.SQUARE:
                n = 1
                for _ in range(max(1, sound.harmonic_count)):
                    if n % 2 == 1:
                        multiplier = float(n)
                        amplitude = 1.0 / multiplier
                        harmonic_multipliers.append((multiplier, amplitude))
                    n += 1
            elif sound.waveform_type == WaveformType.SAWTOOTH:
                for h in range(max(1, sound.harmonic_count)):
                    multiplier = float(h + 1)
                    amplitude = 1.0 / multiplier
                    harmonic_multipliers.append((multiplier, amplitude))
            elif sound.waveform_type == WaveformType.TRIANGLE:
                n = 1
                sign = 1
                for _ in range(max(1, sound.harmonic_count)):
                    if n % 2 == 1:
                        multiplier = float(n)
                        amplitude = sign / (multiplier * multiplier)
                        harmonic_multipliers.append((multiplier, amplitude))
                        sign *= -1
                    n += 1
            elif sound.waveform_type == WaveformType.NOISE:
                pass
            else:
                harmonic_multipliers = [(1.0, 1.0)]

            samples: List[int] = []
            attack_end = sound.envelope_attack * duration
            decay_end = attack_end + sound.envelope_decay * duration
            sustain_end = duration - sound.envelope_release * duration
            total_end = duration

            for frame in range(total_frames):
                t = frame / self._sample_rate

                # ADSR envelope
                if t < attack_end:
                    env = t / max(0.0001, attack_end) if attack_end > 0 else 1.0
                elif t < decay_end:
                    phase_t = (t - attack_end) / max(0.0001, sound.envelope_decay * duration)
                    env = 1.0 - (1.0 - sound.envelope_sustain) * phase_t
                elif t < sustain_end:
                    env = sound.envelope_sustain
                elif t < total_end:
                    phase_t = (t - sustain_end) / max(0.0001, sound.envelope_release * duration)
                    env = sound.envelope_sustain * (1.0 - phase_t)
                else:
                    env = 0.0

                # Additive synthesis
                sample_val = 0.0
                if sound.waveform_type == WaveformType.NOISE:
                    sample_val = (random.random() * 2.0 - 1.0) * sound.amplitude * env
                else:
                    for multiplier, amp in harmonic_multipliers:
                        freq = sound.frequency * multiplier
                        sample_val += amp * math.sin(
                            2.0 * math.pi * freq * t + sound.phase
                        )

                # Noise blend
                if sound.noise_amount > 0.0:
                    noise_sample = (random.random() * 2.0 - 1.0) * sound.noise_amount
                    sample_val = sample_val * (1.0 - sound.noise_amount) + noise_sample

                sample_val *= sound.amplitude * env

                # Clamp to 16-bit range
                sample_val = max(-1.0, min(1.0, sample_val))
                int_sample = int(sample_val * 32767)
                samples.append(int_sample)

            # Pack into bytes (little-endian 16-bit signed)
            result = bytearray()
            for s in samples:
                result.extend(s.to_bytes(2, byteorder="little", signed=True))

            return bytes(result)

    # ------------------------------------------------------------------
    # Public API: Volume Control
    # ------------------------------------------------------------------

    def set_master_volume(self, volume: float) -> None:
        """Sets the global master volume.

        Args:
            volume: Master volume between 0.0 and 1.0.
        """
        with self._lock:
            self._master_volume = max(0.0, min(1.0, volume))

    def set_category_volume(
        self,
        category: str,
        volume: float,
    ) -> None:
        """Sets the volume multiplier for a specific source category.

        Args:
            category: Source type name ('point', 'ambient', 'music', 'voice', 'ui').
            volume: Volume between 0.0 and 1.0.
        """
        try:
            cat = AudioSourceType(category.lower())
        except ValueError:
            return

        with self._lock:
            self._category_volumes[cat] = max(0.0, min(1.0, volume))

    # ------------------------------------------------------------------
    # Public API: Spatial Processing
    # ------------------------------------------------------------------

    def calculate_occlusion(
        self,
        source_id: str,
        listener_id: str,
    ) -> AudioOcclusion:
        """Computes occlusion between a source and listener using ray casting.

        Simulates projecting multiple rays in a cone from the listener
        toward the source. The occlusion level is the fraction of rays
        that hit an obstruction.

        Args:
            source_id: The unique identifier of the audio source.
            listener_id: The unique identifier of the listener.

        Returns:
            An AudioOcclusion result with the computed occlusion level.
        """
        with self._lock:
            source = self._sources.get(source_id)
            listener = self._listeners.get(listener_id)

            cache_key = f"{source_id}:{listener_id}"
            if cache_key in self._occlusion_cache:
                cached = self._occlusion_cache[cache_key]
                if _time_module.time() - cached.timestamp < 0.1:
                    return cached

            if source is None or listener is None:
                return AudioOcclusion(
                    source_id=source_id,
                    occluded=False,
                    occlusion_level=0.0,
                    rays_cast=0,
                    rays_hit=0,
                )

            dist = self._distance(source.position, listener.position)
            if dist < 0.01:
                return AudioOcclusion(
                    source_id=source_id,
                    occluded=False,
                    occlusion_level=0.0,
                    rays_cast=0,
                    rays_hit=0,
                )

            # Simulate ray casting by generating random perturbation rays
            # in a cone around the direct line to the source.
            direct = (
                source.position[0] - listener.position[0],
                source.position[1] - listener.position[1],
                source.position[2] - listener.position[2],
            )
            direct_norm = self._normalize(direct)

            rays_hit = 0
            rays_cast = self._max_rays

            # Simulated obstruction: sources behind walls or at grazing
            # angles have a higher chance of being occluded.
            angle = self._get_listener_view_angle(listener, source.position)
            direct_factor = math.cos(angle)

            # The simulation perturbs the ray and checks random collision.
            # This is a deterministic-probabilistic model that varies with
            # distance and angle for plausible results.
            base_occlusion_prob = 0.0
            if dist > 50.0:
                base_occlusion_prob += 0.1
            if dist > 200.0:
                base_occlusion_prob += 0.15

            if direct_factor < 0.0:
                base_occlusion_prob += 0.4
            elif direct_factor < 0.3:
                base_occlusion_prob += 0.2

            for i in range(rays_cast):
                perturb_x = (random.random() - 0.5) * 0.3
                perturb_y = (random.random() - 0.5) * 0.3
                perturb_z = (random.random() - 0.5) * 0.3

                ray_dir = self._normalize((
                    direct_norm[0] + perturb_x,
                    direct_norm[1] + perturb_y,
                    direct_norm[2] + perturb_z,
                ))

                ray_angle = math.acos(
                    max(-1.0, min(1.0, self._dot(direct_norm, ray_dir)))
                )
                ray_prob = base_occlusion_prob + ray_angle * 0.5
                ray_prob = max(0.0, min(1.0, ray_prob))

                if random.random() < ray_prob:
                    rays_hit += 1

            occlusion_level = rays_hit / max(1, rays_cast)
            is_occluded = occlusion_level > 0.3

            result = AudioOcclusion(
                source_id=source_id,
                occluded=is_occluded,
                occlusion_level=occlusion_level,
                rays_cast=rays_cast,
                rays_hit=rays_hit,
            )

            self._occlusion_cache[cache_key] = result
            return result

    def apply_doppler_effect(
        self,
        source_id: str,
        source_velocity: Tuple[float, float, float],
        listener_id: str,
        listener_velocity: Tuple[float, float, float],
    ) -> Dict[str, Any]:
        """Calculates the Doppler shift for a moving source relative to a listener.

        Computes the perceived frequency change based on the relative
        velocity along the source-listener axis and the speed of sound.

        Args:
            source_id: The unique identifier of the audio source.
            source_velocity: Velocity vector of the source in world units/s.
            listener_id: The unique identifier of the listener.
            listener_velocity: Velocity vector of the listener in world units/s.

        Returns:
            A dictionary with 'pitch_shift', 'frequency_shift_hz',
            'relative_velocity_ms', 'is_approaching', and 'doppler_factor'.
        """
        with self._lock:
            source = self._sources.get(source_id)
            listener = self._listeners.get(listener_id)

            if source is None or listener is None:
                return {
                    "pitch_shift": 1.0,
                    "frequency_shift_hz": 0.0,
                    "relative_velocity_ms": 0.0,
                    "is_approaching": False,
                    "doppler_factor": 0.0,
                }

            to_listener = (
                listener.position[0] - source.position[0],
                listener.position[1] - source.position[1],
                listener.position[2] - source.position[2],
            )
            to_listener_norm = self._normalize(to_listener)

            rel_vel = (
                source_velocity[0] - listener_velocity[0],
                source_velocity[1] - listener_velocity[1],
                source_velocity[2] - listener_velocity[2],
            )

            radial_velocity = self._dot(rel_vel, to_listener_norm)
            is_approaching = radial_velocity < 0.0

            doppler_factor = 1.0
            if abs(self._SPEED_OF_SOUND - radial_velocity) > 0.001:
                doppler_factor = self._SPEED_OF_SOUND / (
                    self._SPEED_OF_SOUND - radial_velocity
                )
            doppler_factor = max(0.25, min(4.0, doppler_factor))

            effective_doppler = 1.0 + (doppler_factor - 1.0) * source.doppler_level
            base_freq = 440.0  # Reference frequency

            return {
                "pitch_shift": round(effective_doppler, 4),
                "frequency_shift_hz": round(base_freq * (effective_doppler - 1.0), 2),
                "relative_velocity_ms": round(radial_velocity, 2),
                "is_approaching": is_approaching,
                "doppler_factor": round(doppler_factor, 4),
            }

    def simulate_room_acoustics(
        self,
        source_id: str,
        room_dimensions: Tuple[float, float, float],
        wall_material: str = "drywall",
    ) -> Dict[str, Any]:
        """Simulates room acoustic response for a source in a rectangular room.

        Computes early reflection times, reverberation time (RT60), room
        modes, Schroeder frequency, and absorption coefficients based on
        room dimensions and wall material.

        Args:
            source_id: The unique identifier of the audio source.
            room_dimensions: Room size in meters as (width, height, depth).
            wall_material: Surface material name affecting absorption.

        Returns:
            A dictionary with acoustic simulation parameters.
        """
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return {}

        width, height, depth = room_dimensions
        volume = width * height * depth
        surface_area = 2.0 * (width * height + width * depth + height * depth)

        absorption = _WALL_MATERIAL_ABSORPTION.get(
            wall_material.lower(), 0.05
        )

        # Sabine RT60 formula
        if absorption > 0.0001 and surface_area > 0.0001:
            rt60 = 0.161 * volume / (surface_area * absorption)
        else:
            rt60 = 5.0

        # Schroeder frequency (transition between modal and diffuse behavior)
        schroeder_freq = 2000.0 * math.sqrt(rt60 / max(0.01, volume))

        # Early reflection times for first-order reflections
        half_w = width / 2.0
        half_h = height / 2.0
        half_d = depth / 2.0

        # Approximate first reflections from nearest walls
        early_reflections = []
        walls = [
            ("left", half_w + source.position[0]),
            ("right", half_w - source.position[0]),
            ("floor", half_h + source.position[1]),
            ("ceiling", half_h - source.position[1]),
            ("front", half_d + source.position[2]),
            ("back", half_d - source.position[2]),
        ]
        for name, dist in walls:
            dist = max(0.01, abs(dist))
            delay = (2.0 * dist) / self._SPEED_OF_SOUND
            amp = 1.0 - absorption
            early_reflections.append({
                "surface": name,
                "delay_seconds": round(delay, 4),
                "amplitude": round(amp, 3),
            })

        # Room mode frequencies (first three axial modes)
        room_modes = []
        for mode in range(1, 4):
            fx = (self._SPEED_OF_SOUND * mode) / (2.0 * width)
            fy = (self._SPEED_OF_SOUND * mode) / (2.0 * height)
            fz = (self._SPEED_OF_SOUND * mode) / (2.0 * depth)
            room_modes.append({
                "mode": mode,
                "fx_hz": round(fx, 1),
                "fy_hz": round(fy, 1),
                "fz_hz": round(fz, 1),
            })

        return {
            "rt60_seconds": round(rt60, 3),
            "schroeder_frequency_hz": round(schroeder_freq, 1),
            "room_volume_m3": round(volume, 1),
            "surface_area_m2": round(surface_area, 1),
            "absorption_coefficient": round(absorption, 3),
            "wall_material": wall_material,
            "early_reflections": early_reflections,
            "room_modes": room_modes,
            "is_diffuse_field": rt60 > 0.3,
        }

    # ------------------------------------------------------------------
    # Public API: Quality Control
    # ------------------------------------------------------------------

    def set_audio_quality(self, quality: str) -> None:
        """Sets the audio processing quality preset.

        Adjusts sample rate, occlusion ray count, harmonic detail, and
        reverb simulation resolution. Affects all subsequent synthesis
        and spatial processing operations.

        Args:
            quality: One of 'low', 'medium', or 'high'.
        """
        q = quality.lower()
        if q not in _QUALITY_PRESETS:
            return

        with self._lock:
            self._quality = q
            preset = _QUALITY_PRESETS[q]
            self._sample_rate = preset["sample_rate"]
            self._max_rays = preset["max_rays"]
            self._max_harmonics = preset["max_harmonics"]
            self._reverb_resolution = preset["reverb_resolution"]
            self._estimate_memory()

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_audio_stats(self) -> Dict[str, Any]:
        """Returns runtime statistics for the spatial audio system.

        Returns:
            A dictionary with source counts, zone counts, playback states,
            CPU load estimate, memory usage, and waveform memory total.
        """
        with self._lock:
            playing_count = sum(
                1 for s in self._sources.values()
                if s.state in (PlaybackState.PLAYING, PlaybackState.FADING_IN)
            )
            paused_count = sum(
                1 for s in self._sources.values()
                if s.state == PlaybackState.PAUSED
            )
            active_count = playing_count + paused_count

            source_type_counts: Dict[str, int] = {}
            for s in self._sources.values():
                st = s.source_type.value
                source_type_counts[st] = source_type_counts.get(st, 0) + 1

            return {
                "source_count": len(self._sources),
                "reverb_zone_count": len(self._reverb_zones),
                "active_sources": active_count,
                "playing_sources": playing_count,
                "paused_sources": paused_count,
                "cpu_load": round(self._cpu_load, 3),
                "memory_usage": self._memory_usage,
                "total_wave_memory": self._total_wave_memory,
                "listener_count": len(self._listeners),
                "procedural_sound_count": len(self._procedural_sounds),
                "quality_preset": self._quality,
                "sample_rate": self._sample_rate,
                "source_type_counts": source_type_counts,
                "master_volume": round(self._master_volume, 2),
                "total_sources_created": self._total_sources_created,
                "tick_count": self._tick_count,
            }

    # ------------------------------------------------------------------
    # Public API: Update Loop
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016) -> None:
        """Advances the spatial audio simulation by one frame.

        Processes fade transitions, updates source playback time, and
        handles loop restart for looping sources.

        Args:
            delta_time: Time elapsed since the last tick in seconds.
        """
        with self._lock:
            self._tick_count += 1

            finished_ids: List[str] = []
            for source_id, source in list(self._sources.items()):
                if source.state == PlaybackState.FADING_IN:
                    source.fade_timer += delta_time
                    t = min(1.0, source.fade_timer / max(0.001, source.fade_duration))
                    source.volume = source.fade_start_volume + (
                        source.fade_target_volume - source.fade_start_volume
                    ) * t
                    if t >= 1.0:
                        source.state = PlaybackState.PLAYING
                        source.volume = source.fade_target_volume

                elif source.state == PlaybackState.FADING_OUT:
                    source.fade_timer += delta_time
                    t = min(1.0, source.fade_timer / max(0.001, source.fade_duration))
                    source.volume = source.fade_start_volume + (
                        source.fade_target_volume - source.fade_start_volume
                    ) * t
                    if t >= 1.0:
                        source.state = PlaybackState.IDLE
                        source.is_playing = False
                        source.current_time = 0.0
                        source.volume = source.fade_target_volume
                        finished_ids.append(source_id)

                elif source.state == PlaybackState.PLAYING:
                    source.current_time += delta_time

                    # Simulate loop wrap-around (duration unknown without clip,
                    # so this is a placeholder for engine integration)
                    max_duration = 300.0  # Safe upper bound
                    if source.current_time >= max_duration:
                        if source.is_looping:
                            source.current_time = 0.0
                        else:
                            source.state = PlaybackState.IDLE
                            source.is_playing = False
                            finished_ids.append(source_id)

            for fid in finished_ids:
                if fid in self._active_source_ids:
                    self._active_source_ids.remove(fid)

            # CPU load simulation (lightweight estimate)
            self._cpu_load = min(
                1.0,
                (
                    len(self._active_source_ids) * 0.001
                    + len(self._reverb_zones) * 0.0005
                    + len(self._procedural_sounds) * 0.0002
                ),
            )

            self._estimate_memory()

    # ------------------------------------------------------------------
    # Public API: Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Performs a complete reset of all spatial audio state.

        Clears all sources, listeners, reverb zones, procedural sounds,
        occlusion cache, active sources, and volume settings. Quality
        preset is reset to 'medium'.
        """
        with self._lock:
            self._sources.clear()
            self._listeners.clear()
            self._reverb_zones.clear()
            self._procedural_sounds.clear()
            self._occlusion_cache.clear()
            self._active_source_ids.clear()

            self._master_volume = 1.0
            self._category_volumes = {
                at: 1.0 for at in AudioSourceType
            }

            self._quality = "medium"
            preset = _QUALITY_PRESETS["medium"]
            self._sample_rate = preset["sample_rate"]
            self._max_rays = preset["max_rays"]
            self._max_harmonics = preset["max_harmonics"]
            self._reverb_resolution = preset["reverb_resolution"]

            self._cpu_load = 0.0
            self._memory_usage = 0
            self._total_wave_memory = 0
            self._tick_count = 0
            self._total_sources_created = 0

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"EngineAudioSpatial(sources={len(self._sources)}, "
                f"listeners={len(self._listeners)}, "
                f"zones={len(self._reverb_zones)}, "
                f"procedural={len(self._procedural_sounds)}, "
                f"quality={self._quality})"
            )


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_audio_spatial() -> EngineAudioSpatial:
    """Module-level accessor for the EngineAudioSpatial singleton.

    Convenience function that returns the singleton instance without
    needing to reference EngineAudioSpatial.get_instance() directly.

    Returns:
        The singleton EngineAudioSpatial instance.
    """
    return EngineAudioSpatial.get_instance()