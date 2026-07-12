"""Audio & SFX System for SparkLabs AI-native game engine.

Provides procedural audio generation, spatial 3D audio positioning,
dynamic music layering, audio bus routing, and AI-driven sound effect
synthesis for immersive game audio.

Architecture:
  AudioSfxSystem (singleton)
    |-- AudioBusChannel, AudioDistanceModel, AudioEventKind, AudioFormat,
       AudioLoopMode, AudioPriority, AudioStatus, AudioType, WaveformType
    |-- AudioBus, AudioEmitter, AudioListener, AudioClip, AudioSource,
       MusicLayer, MusicTrack, AudioEffect, AudioReverbZone, AudioConfig,
       AudioStats, AudioSnapshot, AudioEvent
    |-- get_audio_sfx_system

Core Capabilities:
  - register_bus / remove_bus / get_bus / list_buses / set_bus_volume /
    mute_bus / solo_bus: audio bus routing with per-channel volume, mute,
    and solo plus a chain of effects applied to each bus.
  - register_emitter / remove_emitter / get_emitter / list_emitters:
    positional sound emitters carrying 3D position, velocity, distance
    model, and spatial blend for immersive placement.
  - register_listener / remove_listener / get_listener / list_listeners /
    update_listener_position: listener tracking used by the spatializer
    to compute attenuation, panning, and doppler shift.
  - register_clip / remove_clip / get_clip / list_clips: audio clip
    catalog holding format, sample rate, channel count, duration, and
    raw sample data for procedural playback.
  - create_source / remove_source / get_source / list_sources /
    play_source / pause_source / stop_source / set_source_volume /
    set_source_pitch / set_source_pan: full source lifecycle with fade
    in/out, loop modes, priority, and live parameter control.
  - create_music_track / remove_music_track / get_music_track /
    list_music_tracks / add_music_layer / remove_music_layer /
    play_music_track / stop_music_track / set_music_layer_volume /
    transition_music_layer: dynamic music layering with smooth layer
    transitions driven by gameplay conditions.
  - register_effect / remove_effect / get_effect / list_effects /
    add_effect_to_bus / remove_effect_from_bus: insertable DSP effects
    (reverb, echo, distortion, filters) attached to bus effect chains.
  - register_reverb_zone / remove_reverb_zone / get_reverb_zone /
    list_reverb_zones: spatial reverb zones that apply room size,
    damping, wet/dry mix based on listener proximity.
  - auto_generate_sfx: AI-driven procedural sound effect synthesis from
    a natural-language description (explosion, laser, footstep, wind,
    magic, ui click, and combinations thereof).
  - generate_procedural_clip: deterministic waveform synthesis (sine,
    square, saw, triangle, noise, pulse) at a target frequency,
    duration, and sample rate.
  - suggest_music_layer: AI-driven music layer suggestion based on the
    current mood of the scene.
  - optimize_mix: AI-driven mix analysis that returns a list of concrete
    optimization suggestions for a given bus.
  - analyze_audio_spectrum: frequency-domain analysis of a clip that
    returns peak frequency, RMS level, spectral centroid, and band
    energies.
  - get_config / set_config / get_stats / get_snapshot / get_status /
    list_events / tick / reset: observability, tuning, and lifecycle.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`AudioSfxSystem.get_instance` or the module-level
:func:`get_audio_sfx_system` factory. All public methods are guarded by
the re-entrant lock so concurrent calls from gameplay, render, and
editor threads remain consistent.
"""

import hashlib
import math
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry
# is evicted in FIFO order to keep memory growth predictable under heavy
# dynamic use such as a battle spawning dozens of one-shot effects.
_MAX_BUSES: int = 128
_MAX_EMITTERS: int = 1024
_MAX_LISTENERS: int = 16
_MAX_CLIPS: int = 4096
_MAX_SOURCES: int = 2048
_MAX_TRACKS: int = 256
_MAX_LAYERS_PER_TRACK: int = 16
_MAX_EFFECTS: int = 512
_MAX_REVERB_ZONES: int = 128
_MAX_EVENTS: int = 10000

# Numeric bounds for common audio parameters.
_VOLUME_MIN: float = 0.0
_VOLUME_MAX: float = 2.0
_PITCH_MIN: float = 0.25
_PITCH_MAX: float = 4.0
_PAN_MIN: float = -1.0
_PAN_MAX: float = 1.0
_DISTANCE_MIN: float = 0.0
_DISTANCE_MAX: float = 100000.0
_SPATIAL_BLEND_MIN: float = 0.0
_SPATIAL_BLEND_MAX: float = 1.0
_FREQUENCY_MIN: float = 20.0
_FREQUENCY_MAX: float = 20000.0
_AMPLITUDE_MIN: float = 0.0
_AMPLITUDE_MAX: float = 1.0
_DURATION_MIN: float = 0.0
_DURATION_MAX: float = 3600.0
_SAMPLE_RATE_MIN: int = 4000
_SAMPLE_RATE_MAX: int = 192000
_BUFFER_SIZE_MIN: int = 64
_BUFFER_SIZE_MAX: int = 8192
_BPM_MIN: float = 20.0
_BPM_MAX: float = 400.0
_DOPPLER_MIN: float = 0.0
_DOPPLER_MAX: float = 5.0
_SPEED_OF_SOUND_MIN: float = 100.0
_SPEED_OF_SOUND_MAX: float = 1000.0
_ROOM_SIZE_MIN: float = 0.0
_ROOM_SIZE_MAX: float = 1.0
_DAMPING_MIN: float = 0.0
_DAMPING_MAX: float = 1.0
_WET_LEVEL_MIN: float = 0.0
_WET_LEVEL_MAX: float = 1.0
_DRY_LEVEL_MIN: float = 0.0
_DRY_LEVEL_MAX: float = 1.0

# List limits.
_DEFAULT_LIST_LIMIT: int = 100
_MAX_LIST_LIMIT: int = 500


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    """Return the current Unix timestamp in seconds."""
    return time.time()


def _new_id(seed_text: str = "", prefix: str = "id") -> str:
    """Generate a deterministic 12-character identifier from seed text.

    When ``seed_text`` is empty a random component is mixed in so that
    each call yields a distinct value. The md5 digest is truncated to
    12 hex characters for compact, collision-resistant identifiers.
    """
    if not seed_text:
        seed_text = f"{time.time_ns()}{random.random()}"
    digest = hashlib.md5(seed_text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}" if prefix else digest


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, returning ``default`` on failure."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce a value to int, returning ``default`` on failure."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp ``value`` to the inclusive range [lo, hi]."""
    if lo > hi:
        lo, hi = hi, lo
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Trim a list from the front until it fits within ``max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert arbitrary values into JSON-serializable primitives."""
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
    """Serialize a dataclass instance into a plain dict.

    Handles nested dataclasses, lists, tuples, dicts, and enums so that
    every field is reduced to a JSON-serializable primitive.
    """
    if instance is None:
        return {}
    if hasattr(instance, "__dataclass_fields__"):
        out: Dict[str, Any] = {}
        for name in getattr(instance, "__dataclass_fields__", {}).keys():
            try:
                raw = getattr(instance, name)
            except Exception:
                continue
            out[name] = _to_jsonable(raw)
        return out
    if isinstance(instance, dict):
        return {str(k): _to_jsonable(v) for k, v in instance.items()}
    if hasattr(instance, "to_dict") and callable(instance.to_dict):
        return instance.to_dict()
    return {}


def _distance3d(a: Tuple[float, float, float],
                b: Tuple[float, float, float]) -> float:
    """Euclidean distance between two 3D points."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _generate_waveform(waveform: str, frequency: float, duration: float,
                       sample_rate: int, amplitude: float) -> List[float]:
    """Synthesize a list of float samples for the given waveform.

    Supports sine, square, saw, triangle, noise, and pulse waveforms.
    The output is normalized to the [-amplitude, +amplitude] range.
    """
    if duration <= 0 or sample_rate <= 0 or frequency <= 0:
        return []
    total_samples = int(duration * sample_rate)
    if total_samples <= 0:
        return []
    if total_samples > sample_rate * 60:
        # Cap at 60 seconds of audio to avoid runaway memory use.
        total_samples = sample_rate * 60
    amp = _clamp(amplitude, _AMPLITUDE_MIN, _AMPLITUDE_MAX)
    samples: List[float] = []
    two_pi_f_over_sr = 2.0 * math.pi * frequency / float(sample_rate)
    wf = (waveform or "").lower()
    for i in range(total_samples):
        t = i / float(sample_rate)
        phase = two_pi_f_over_sr * i
        if wf == WaveformType.SINE.value:
            val = math.sin(phase)
        elif wf == WaveformType.SQUARE.value:
            val = 1.0 if math.sin(phase) >= 0.0 else -1.0
        elif wf == WaveformType.SAW.value:
            val = 2.0 * ((i * frequency / sample_rate) % 1.0) - 1.0
        elif wf == WaveformType.TRIANGLE.value:
            saw = 2.0 * ((i * frequency / sample_rate) % 1.0) - 1.0
            val = 2.0 * abs(saw) - 1.0
        elif wf == WaveformType.NOISE.value:
            val = random.uniform(-1.0, 1.0)
        elif wf == WaveformType.PULSE.value:
            # 25 percent duty cycle pulse wave.
            cycle = (i * frequency / sample_rate) % 1.0
            val = 1.0 if cycle < 0.25 else -1.0
        else:
            val = math.sin(phase)
        # Apply a short exponential attack/decay envelope so the clip
        # does not pop at the start and end.
        attack = min(int(0.01 * sample_rate), total_samples // 4)
        release = min(int(0.05 * sample_rate), total_samples // 4)
        env = 1.0
        if attack > 0 and i < attack:
            env = float(i) / float(attack)
        if release > 0 and i >= total_samples - release:
            env = float(total_samples - i) / float(release)
        samples.append(round(val * amp * env, 6))
    return samples


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AudioBusChannel(str, Enum):
    """Logical routing channel for an audio bus."""
    MASTER = "master"
    MUSIC = "music"
    SFX = "sfx"
    VOICE = "voice"
    AMBIENT = "ambient"
    UI = "ui"


class AudioDistanceModel(str, Enum):
    """Attenuation curve applied as an emitter moves away from a listener."""
    LINEAR = "linear"
    INVERSE = "inverse"
    EXPONENTIAL = "exponential"


class AudioEventKind(str, Enum):
    """Audit event types emitted by the audio and SFX system."""
    CREATED = "created"
    PLAYED = "played"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESUMED = "resumed"
    VOLUME_CHANGED = "volume_changed"
    BUS_ROUTED = "bus_routed"
    EFFECT_GENERATED = "effect_generated"


class AudioFormat(str, Enum):
    """Channel layout of an audio clip."""
    MONO = "mono"
    STEREO = "stereo"
    SURROUND_51 = "surround_51"
    SURROUND_71 = "surround_71"


class AudioLoopMode(str, Enum):
    """Loop behavior of an audio source when playback reaches the end."""
    ONE_SHOT = "one_shot"
    LOOP = "loop"
    LOOP_WITH_FADE = "loop_with_fade"


class AudioPriority(str, Enum):
    """Playback priority used for voice stealing when channels are full."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AudioStatus(str, Enum):
    """Runtime state of an audio source."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class AudioType(str, Enum):
    """Semantic category of an audio clip."""
    SFX = "sfx"
    MUSIC = "music"
    VOICE = "voice"
    AMBIENT = "ambient"
    UI = "ui"
    FOLEY = "Foley"


class WaveformType(str, Enum):
    """Procedural waveform used by the synthesis engine."""
    SINE = "sine"
    SQUARE = "square"
    SAW = "saw"
    TRIANGLE = "triangle"
    NOISE = "noise"
    PULSE = "pulse"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class AudioBus:
    """An audio bus that routes sources through a volume and effect chain."""
    bus_id: str
    name: str = ""
    channel: str = AudioBusChannel.MASTER.value
    volume: float = 1.0
    muted: bool = False
    solo: bool = False
    effects_chain: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioEmitter:
    """A positional sound emitter in 3D space."""
    emitter_id: str
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    min_distance: float = 1.0
    max_distance: float = 100.0
    distance_model: str = AudioDistanceModel.INVERSE.value
    spatial_blend: float = 1.0
    priority: str = AudioPriority.NORMAL.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioListener:
    """The listener that hears spatialized audio in the 3D world."""
    listener_id: str
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    forward: Tuple[float, float, float] = (0.0, 0.0, -1.0)
    up: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    gain: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioClip:
    """An audio clip holding format info and raw sample data."""
    clip_id: str
    name: str = ""
    audio_type: str = AudioType.SFX.value
    format: str = AudioFormat.MONO.value
    sample_rate: int = 44100
    channels: int = 1
    duration: float = 1.0
    sample_data: List[float] = field(default_factory=list)
    loop_mode: str = AudioLoopMode.ONE_SHOT.value
    priority: str = AudioPriority.NORMAL.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioSource:
    """A runtime playback instance bound to a clip, emitter, and bus."""
    source_id: str
    clip_id: str = ""
    emitter_id: str = ""
    bus_id: str = ""
    volume: float = 1.0
    pitch: float = 1.0
    pan: float = 0.0
    loop_mode: str = AudioLoopMode.ONE_SHOT.value
    status: str = AudioStatus.IDLE.value
    play_position: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicLayer:
    """A single layer within a music track that can be mixed in or out."""
    layer_id: str
    name: str = ""
    clip_id: str = ""
    bus_id: str = ""
    volume: float = 1.0
    active: bool = False
    condition: str = ""
    priority: str = AudioPriority.NORMAL.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MusicTrack:
    """A music track composed of multiple layers that fade in and out."""
    track_id: str
    name: str = ""
    layers: List[MusicLayer] = field(default_factory=list)
    bpm: float = 120.0
    time_signature: str = "4/4"
    key: str = "C_major"
    current_layer: str = ""
    playing: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioEffect:
    """A DSP effect that can be inserted into a bus effect chain."""
    effect_id: str
    name: str = ""
    effect_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioReverbZone:
    """A spatial zone that applies reverb based on listener proximity."""
    zone_id: str
    name: str = ""
    min_distance: float = 1.0
    max_distance: float = 50.0
    reverb_preset: str = "generic"
    room_size: float = 0.5
    damping: float = 0.5
    wet_level: float = 0.5
    dry_level: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioConfig:
    """Global configuration for the audio and SFX system."""
    max_buses: int = 128
    max_emitters: int = 1024
    max_sources: int = 2048
    max_clips: int = 4096
    max_tracks: int = 256
    max_effects: int = 512
    master_volume: float = 1.0
    sample_rate: int = 44100
    buffer_size: int = 1024
    spatial_audio_enabled: bool = True
    doppler_factor: float = 1.0
    speed_of_sound: float = 343.3

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioStats:
    """Live statistics snapshot for the audio and SFX system."""
    total_buses: int = 0
    total_emitters: int = 0
    total_listeners: int = 0
    total_clips: int = 0
    total_sources: int = 0
    total_tracks: int = 0
    total_layers: int = 0
    total_effects: int = 0
    total_reverb_zones: int = 0
    active_sources: int = 0
    active_tracks: int = 0
    total_played: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioSnapshot:
    """A lightweight point-in-time snapshot of system state."""
    initialized: bool = False
    tick_count: int = 0
    active_sources: int = 0
    active_tracks: int = 0
    master_volume: float = 1.0
    bus_count: int = 0
    emitter_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioEvent:
    """An audit event recorded by the audio and SFX system."""
    event_id: str
    kind: str = AudioEventKind.CREATED.value
    timestamp: float = field(default_factory=_now)
    source_id: str = ""
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# System Class
# ---------------------------------------------------------------------------

class AudioSfxSystem:
    """Manages buses, emitters, listeners, clips, sources, music tracks,
    effects, reverb zones, and the AI procedural audio pipeline.

    The system is a thread-safe singleton. All public methods take the
    instance lock before mutating shared state so that concurrent calls
    from render, gameplay, and editor threads remain consistent.
    """

    __instance: Optional["AudioSfxSystem"] = None
    __lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._initialize()

    @classmethod
    def get_instance(cls) -> "AudioSfxSystem":
        """Return the singleton AudioSfxSystem instance.

        Uses double-checked locking so the instance is created exactly
        once even when multiple threads call this concurrently on first
        use.
        """
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None:
                    cls.__instance = cls()
        return cls.__instance

    def _initialize(self) -> None:
        """Initialize the system stores and seed default data (idempotent).

        Guarded by the init lock so repeated calls are no-ops after the
        first successful seed. Invoked from ``__init__`` and from
        ``reset`` to repopulate the default data set.
        """
        with self._init_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._config = AudioConfig()
            # Primary stores.
            self._buses: Dict[str, AudioBus] = {}
            self._emitters: Dict[str, AudioEmitter] = {}
            self._listeners: Dict[str, AudioListener] = {}
            self._clips: Dict[str, AudioClip] = {}
            self._sources: Dict[str, AudioSource] = {}
            self._tracks: Dict[str, MusicTrack] = {}
            self._layers: Dict[str, MusicLayer] = {}
            self._effects: Dict[str, AudioEffect] = {}
            self._reverb_zones: Dict[str, AudioReverbZone] = {}
            self._events: List[AudioEvent] = []
            # Counters and stats.
            self._stats = AudioStats()
            self._tick_count: int = 0
            self._event_counter: int = 0
            self._source_counter: int = 0
            self._total_played: int = 0
            self._soloed_buses: List[str] = []
            self._initialized = True
            self._seed()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with realistic default game audio data.

        Creates six audio buses (master, music, sfx, voice, ambient, ui),
        eight audio clips (footsteps, explosion, laser, sword swing, ui
        click, ambient wind, music theme, voice narration), five audio
        emitters (player, enemy, npc, ambient source, vehicle), one
        listener, four music tracks with multiple layers, five audio
        effects, four reverb zones, and six audit events.
        """
        # --- Audio Buses (6) ---
        bus_seeds = [
            ("bus_master", "Master Bus", AudioBusChannel.MASTER.value, 1.0, False, False, []),
            ("bus_music", "Music Bus", AudioBusChannel.MUSIC.value, 0.8, False, False, []),
            ("bus_sfx", "SFX Bus", AudioBusChannel.SFX.value, 1.0, False, False, []),
            ("bus_voice", "Voice Bus", AudioBusChannel.VOICE.value, 1.0, False, False, []),
            ("bus_ambient", "Ambient Bus", AudioBusChannel.AMBIENT.value, 0.7, False, False, []),
            ("bus_ui", "UI Bus", AudioBusChannel.UI.value, 0.9, False, False, []),
        ]
        for bid, bname, bchan, bvol, bmute, bsolo, bfx in bus_seeds:
            self._buses[bid] = AudioBus(
                bus_id=bid, name=bname, channel=bchan, volume=bvol,
                muted=bmute, solo=bsolo, effects_chain=bfx,
                metadata={"seed": True},
            )

        # --- Audio Clips (8) ---
        clip_seeds = [
            ("clip_footstep_01", "Gravel Footstep", AudioType.FOLEY.value,
             AudioFormat.MONO.value, 44100, 1, 0.35, [],
             AudioLoopMode.ONE_SHOT.value, AudioPriority.LOW.value,
             {"material": "gravel", "velocity": "walk"}),
            ("clip_explosion_01", "Large Explosion", AudioType.SFX.value,
             AudioFormat.STEREO.value, 44100, 2, 2.5, [],
             AudioLoopMode.ONE_SHOT.value, AudioPriority.CRITICAL.value,
             {"size": "large", "element": "fire"}),
            ("clip_laser_01", "Laser Blast", AudioType.SFX.value,
             AudioFormat.MONO.value, 44100, 1, 0.6, [],
             AudioLoopMode.ONE_SHOT.value, AudioPriority.HIGH.value,
             {"pitch_shift": 1.0}),
            ("clip_sword_swing_01", "Sword Swing", AudioType.FOLEY.value,
             AudioFormat.MONO.value, 44100, 1, 0.45, [],
             AudioLoopMode.ONE_SHOT.value, AudioPriority.NORMAL.value,
             {"weapon": "longsword"}),
            ("clip_ui_click_01", "UI Click", AudioType.UI.value,
             AudioFormat.MONO.value, 44100, 1, 0.1, [],
             AudioLoopMode.ONE_SHOT.value, AudioPriority.NORMAL.value,
             {"interface": "button"}),
            ("clip_ambient_wind_01", "Wind Ambience", AudioType.AMBIENT.value,
             AudioFormat.STEREO.value, 44100, 2, 30.0, [],
             AudioLoopMode.LOOP.value, AudioPriority.LOW.value,
             {"environment": "plains", "intensity": "light"}),
            ("clip_music_theme_01", "Main Theme", AudioType.MUSIC.value,
             AudioFormat.STEREO.value, 44100, 2, 120.0, [],
             AudioLoopMode.LOOP_WITH_FADE.value, AudioPriority.HIGH.value,
             {"composer": "procedural", "mood": "heroic"}),
            ("clip_voice_narration_01", "Narration Voice", AudioType.VOICE.value,
             AudioFormat.MONO.value, 44100, 1, 8.0, [],
             AudioLoopMode.ONE_SHOT.value, AudioPriority.CRITICAL.value,
             {"speaker": "narrator", "language": "en"}),
        ]
        for cid, cname, ctype, cfmt, csr, cch, cdur, cdata, cloop, cprio, cmeta in clip_seeds:
            self._clips[cid] = AudioClip(
                clip_id=cid, name=cname, audio_type=ctype, format=cfmt,
                sample_rate=csr, channels=cch, duration=cdur,
                sample_data=cdata, loop_mode=cloop, priority=cprio,
                metadata=cmeta,
            )

        # --- Audio Emitters (5) ---
        emitter_seeds = [
            ("emit_player", "Player Emitter", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
             1.0, 100.0, AudioDistanceModel.INVERSE.value, 1.0,
             AudioPriority.HIGH.value),
            ("emit_enemy", "Enemy Emitter", (10.0, 0.0, 5.0), (-1.0, 0.0, 0.0),
             1.0, 80.0, AudioDistanceModel.INVERSE.value, 1.0,
             AudioPriority.NORMAL.value),
            ("emit_npc", "NPC Emitter", (-5.0, 0.0, 3.0), (0.0, 0.0, 0.0),
             1.0, 60.0, AudioDistanceModel.LINEAR.value, 0.8,
             AudioPriority.NORMAL.value),
            ("emit_ambient", "Ambient Emitter", (0.0, 5.0, -20.0), (0.0, 0.0, 0.0),
             5.0, 200.0, AudioDistanceModel.EXPONENTIAL.value, 0.5,
             AudioPriority.LOW.value),
            ("emit_vehicle", "Vehicle Emitter", (30.0, 0.0, 0.0), (5.0, 0.0, 0.0),
             2.0, 150.0, AudioDistanceModel.INVERSE.value, 1.0,
             AudioPriority.HIGH.value),
        ]
        for eid, ename, epos, evel, emin, emax, edmodel, eblend, eprio in emitter_seeds:
            self._emitters[eid] = AudioEmitter(
                emitter_id=eid, name=ename, position=epos, velocity=evel,
                min_distance=emin, max_distance=emax,
                distance_model=edmodel, spatial_blend=eblend,
                priority=eprio, metadata={"seed": True},
            )

        # --- Audio Listener (1) ---
        self._listeners["listener_main"] = AudioListener(
            listener_id="listener_main",
            name="Main Listener",
            position=(0.0, 0.0, 0.0),
            forward=(0.0, 0.0, -1.0),
            up=(0.0, 1.0, 0.0),
            velocity=(0.0, 0.0, 0.0),
            gain=1.0,
        )

        # --- Audio Effects (5) ---
        effect_seeds = [
            ("fx_reverb_cave", "Cave Reverb", "reverb",
             {"decay": 2.5, "predelay": 0.03, "diffusion": 0.9}, True, 0),
            ("fx_echo_01", "Slap Echo", "echo",
             {"delay": 0.15, "feedback": 0.3, "mix": 0.4}, True, 1),
            ("fx_distortion_01", "Grit Distortion", "distortion",
             {"drive": 0.6, "tone": 0.5, "mix": 0.3}, True, 2),
            ("fx_lowpass_01", "Warm Lowpass", "lowpass",
             {"cutoff": 800.0, "resonance": 0.7}, True, 3),
            ("fx_highpass_01", "Air Highpass", "highpass",
             {"cutoff": 120.0, "resonance": 0.5}, True, 4),
        ]
        for fxid, fxname, fxtype, fxparams, fxenabled, fxorder in effect_seeds:
            self._effects[fxid] = AudioEffect(
                effect_id=fxid, name=fxname, effect_type=fxtype,
                parameters=fxparams, enabled=fxenabled, order=fxorder,
                metadata={"seed": True},
            )

        # Attach some effects to buses.
        self._buses["bus_sfx"].effects_chain = ["fx_reverb_cave", "fx_lowpass_01"]
        self._buses["bus_music"].effects_chain = ["fx_echo_01"]
        self._buses["bus_voice"].effects_chain = ["fx_highpass_01"]

        # --- Music Tracks (4) with layers ---
        # Track 1: Battle Theme with three layers.
        battle_layers = [
            MusicLayer(layer_id="layer_battle_drums", name="Battle Drums",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.9, active=True, condition="combat",
                       priority=AudioPriority.HIGH.value,
                       metadata={"instrument": "drums"}),
            MusicLayer(layer_id="layer_battle_strings", name="Battle Strings",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.7, active=False, condition="combat_intense",
                       priority=AudioPriority.NORMAL.value,
                       metadata={"instrument": "strings"}),
            MusicLayer(layer_id="layer_battle_brass", name="Battle Brass",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.6, active=False, condition="boss",
                       priority=AudioPriority.NORMAL.value,
                       metadata={"instrument": "brass"}),
        ]
        self._tracks["track_battle"] = MusicTrack(
            track_id="track_battle", name="Battle Theme",
            layers=battle_layers, bpm=140.0, time_signature="4/4",
            key="D_minor", current_layer="layer_battle_drums",
            playing=False, metadata={"seed": True, "mood": "tense"},
        )
        for lyr in battle_layers:
            self._layers[lyr.layer_id] = lyr

        # Track 2: Exploration Theme with two layers.
        explore_layers = [
            MusicLayer(layer_id="layer_explore_melody", name="Explore Melody",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.8, active=True, condition="exploring",
                       priority=AudioPriority.NORMAL.value,
                       metadata={"instrument": "flute"}),
            MusicLayer(layer_id="layer_explore_pad", name="Explore Pad",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.5, active=True, condition="exploring",
                       priority=AudioPriority.LOW.value,
                       metadata={"instrument": "pad"}),
        ]
        self._tracks["track_explore"] = MusicTrack(
            track_id="track_explore", name="Exploration Theme",
            layers=explore_layers, bpm=90.0, time_signature="4/4",
            key="C_major", current_layer="layer_explore_melody",
            playing=False, metadata={"seed": True, "mood": "calm"},
        )
        for lyr in explore_layers:
            self._layers[lyr.layer_id] = lyr

        # Track 3: Menu Theme with two layers.
        menu_layers = [
            MusicLayer(layer_id="layer_menu_main", name="Menu Main",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.7, active=True, condition="menu",
                       priority=AudioPriority.NORMAL.value,
                       metadata={"instrument": "piano"}),
            MusicLayer(layer_id="layer_menu_ambient", name="Menu Ambient",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.4, active=True, condition="menu",
                       priority=AudioPriority.LOW.value,
                       metadata={"instrument": "synth"}),
        ]
        self._tracks["track_menu"] = MusicTrack(
            track_id="track_menu", name="Menu Theme",
            layers=menu_layers, bpm=75.0, time_signature="3/4",
            key="F_major", current_layer="layer_menu_main",
            playing=False, metadata={"seed": True, "mood": "relaxed"},
        )
        for lyr in menu_layers:
            self._layers[lyr.layer_id] = lyr

        # Track 4: Boss Theme with three layers.
        boss_layers = [
            MusicLayer(layer_id="layer_boss_drums", name="Boss Drums",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=1.0, active=True, condition="boss",
                       priority=AudioPriority.CRITICAL.value,
                       metadata={"instrument": "taiko"}),
            MusicLayer(layer_id="layer_boss_choir", name="Boss Choir",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.8, active=False, condition="boss_phase_2",
                       priority=AudioPriority.HIGH.value,
                       metadata={"instrument": "choir"}),
            MusicLayer(layer_id="layer_boss_orchestra", name="Boss Orchestra",
                       clip_id="clip_music_theme_01", bus_id="bus_music",
                       volume=0.9, active=False, condition="boss_phase_3",
                       priority=AudioPriority.HIGH.value,
                       metadata={"instrument": "orchestra"}),
        ]
        self._tracks["track_boss"] = MusicTrack(
            track_id="track_boss", name="Boss Theme",
            layers=boss_layers, bpm=160.0, time_signature="4/4",
            key="E_minor", current_layer="layer_boss_drums",
            playing=False, metadata={"seed": True, "mood": "epic"},
        )
        for lyr in boss_layers:
            self._layers[lyr.layer_id] = lyr

        # --- Reverb Zones (4) ---
        zone_seeds = [
            ("zone_cave", "Cave Reverb Zone", 1.0, 50.0, "cave", 0.8, 0.7, 0.6, 0.4),
            ("zone_hall", "Concert Hall Zone", 2.0, 80.0, "hall", 0.9, 0.4, 0.5, 0.5),
            ("zone_room", "Small Room Zone", 0.5, 15.0, "room", 0.3, 0.5, 0.3, 0.7),
            ("zone_outdoor", "Outdoor Valley Zone", 5.0, 200.0, "outdoor", 0.1, 0.2, 0.2, 0.8),
        ]
        for zid, zname, zmin, zmax, zpreset, zroom, zdamp, zwet, zdry in zone_seeds:
            self._reverb_zones[zid] = AudioReverbZone(
                zone_id=zid, name=zname, min_distance=zmin, max_distance=zmax,
                reverb_preset=zpreset, room_size=zroom, damping=zdamp,
                wet_level=zwet, dry_level=zdry, metadata={"seed": True},
            )

        # --- Events (6) ---
        self._emit(AudioEventKind.CREATED.value,
                   "Master bus created during seed",
                   data={"bus_id": "bus_master"})
        self._emit(AudioEventKind.CREATED.value,
                   "Default audio clips seeded",
                   data={"clip_count": 8})
        self._emit(AudioEventKind.CREATED.value,
                   "Default audio emitters seeded",
                   data={"emitter_count": 5})
        self._emit(AudioEventKind.CREATED.value,
                   "Music tracks with layers seeded",
                   data={"track_count": 4})
        self._emit(AudioEventKind.CREATED.value,
                   "Default audio effects seeded",
                   data={"effect_count": 5})
        self._emit(AudioEventKind.CREATED.value,
                   "Reverb zones seeded",
                   data={"zone_count": 4})

        self._update_stats()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: str, description: str = "",
              source_id: str = "",
              data: Optional[Dict[str, Any]] = None) -> AudioEvent:
        """Append an audit event to the in-memory event log."""
        self._event_counter += 1
        event = AudioEvent(
            event_id=f"aevt_{self._event_counter:06d}",
            kind=kind,
            timestamp=_now(),
            source_id=source_id,
            description=description,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    def _update_stats(self) -> None:
        """Recompute the live statistics object from current stores."""
        self._stats.total_buses = len(self._buses)
        self._stats.total_emitters = len(self._emitters)
        self._stats.total_listeners = len(self._listeners)
        self._stats.total_clips = len(self._clips)
        self._stats.total_sources = len(self._sources)
        self._stats.total_tracks = len(self._tracks)
        self._stats.total_layers = len(self._layers)
        self._stats.total_effects = len(self._effects)
        self._stats.total_reverb_zones = len(self._reverb_zones)
        self._stats.active_sources = sum(
            1 for s in self._sources.values()
            if s.status == AudioStatus.PLAYING.value
        )
        self._stats.active_tracks = sum(
            1 for t in self._tracks.values() if t.playing
        )
        self._stats.total_played = self._total_played
        self._stats.tick_count = self._tick_count

    def _validate_channel(self, channel: str) -> str:
        """Return a valid AudioBusChannel value or the master default."""
        try:
            return AudioBusChannel(channel).value
        except (ValueError, TypeError):
            return AudioBusChannel.MASTER.value

    def _validate_audio_type(self, audio_type: str) -> str:
        """Return a valid AudioType value or the sfx default."""
        try:
            return AudioType(audio_type).value
        except (ValueError, TypeError):
            return AudioType.SFX.value

    def _validate_format(self, fmt: str) -> str:
        """Return a valid AudioFormat value or the mono default."""
        try:
            return AudioFormat(fmt).value
        except (ValueError, TypeError):
            return AudioFormat.MONO.value

    def _validate_loop_mode(self, mode: str) -> str:
        """Return a valid AudioLoopMode value or the one_shot default."""
        try:
            return AudioLoopMode(mode).value
        except (ValueError, TypeError):
            return AudioLoopMode.ONE_SHOT.value

    def _validate_priority(self, priority: str) -> str:
        """Return a valid AudioPriority value or the normal default."""
        try:
            return AudioPriority(priority).value
        except (ValueError, TypeError):
            return AudioPriority.NORMAL.value

    def _validate_distance_model(self, model: str) -> str:
        """Return a valid AudioDistanceModel value or the inverse default."""
        try:
            return AudioDistanceModel(model).value
        except (ValueError, TypeError):
            return AudioDistanceModel.INVERSE.value

    def _validate_status(self, status: str) -> str:
        """Return a valid AudioStatus value or the idle default."""
        try:
            return AudioStatus(status).value
        except (ValueError, TypeError):
            return AudioStatus.IDLE.value

    def _validate_waveform(self, waveform: str) -> str:
        """Return a valid WaveformType value or the sine default."""
        try:
            return WaveformType(waveform).value
        except (ValueError, TypeError):
            return WaveformType.SINE.value

    # ------------------------------------------------------------------
    # Bus Management
    # ------------------------------------------------------------------

    def register_bus(self, bus_id: str = "", name: str = "",
                     channel: str = AudioBusChannel.MASTER.value,
                     volume: float = 1.0, muted: bool = False,
                     solo: bool = False,
                     effects_chain: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None
                     ) -> Tuple[bool, str, Optional[AudioBus]]:
        """Register a new audio bus with volume, mute, solo, and effects."""
        with self._lock:
            if not bus_id:
                bus_id = _new_id(name or "bus", "bus")
            if bus_id in self._buses:
                return False, f"Bus already exists: {bus_id}", None
            if len(self._buses) >= self._config.max_buses:
                return False, "Maximum bus capacity reached", None
            bus = AudioBus(
                bus_id=bus_id,
                name=name or bus_id,
                channel=self._validate_channel(channel),
                volume=_clamp(_safe_float(volume, 1.0), _VOLUME_MIN, _VOLUME_MAX),
                muted=bool(muted),
                solo=bool(solo),
                effects_chain=list(effects_chain) if effects_chain else [],
                metadata=dict(metadata) if metadata else {},
                created_at=_now(),
            )
            self._buses[bus_id] = bus
            if bus.solo and bus_id not in self._soloed_buses:
                self._soloed_buses.append(bus_id)
            self._emit(AudioEventKind.CREATED.value,
                       f"Bus registered: {bus.name}",
                       data={"bus_id": bus_id})
            self._update_stats()
            return True, f"Bus registered: {bus_id}", bus

    def remove_bus(self, bus_id: str = "") -> Tuple[bool, str]:
        """Remove an audio bus by its identifier."""
        with self._lock:
            if not bus_id:
                return False, "bus_id is required"
            bus = self._buses.pop(bus_id, None)
            if bus is None:
                return False, f"Bus not found: {bus_id}"
            if bus_id in self._soloed_buses:
                self._soloed_buses.remove(bus_id)
            # Detach the bus from any sources that were routed to it.
            for src in self._sources.values():
                if src.bus_id == bus_id:
                    src.bus_id = ""
            self._emit(AudioEventKind.CREATED.value,
                       f"Bus removed: {bus.name}",
                       data={"bus_id": bus_id})
            self._update_stats()
            return True, f"Bus removed: {bus_id}"

    def get_bus(self, bus_id: str = "") -> Optional[AudioBus]:
        """Return the audio bus with the given identifier, or None."""
        with self._lock:
            return self._buses.get(bus_id)

    def list_buses(self, channel: str = "",
                   active_only: bool = False,
                   limit: int = _DEFAULT_LIST_LIMIT
                   ) -> List[AudioBus]:
        """List audio buses, optionally filtered by channel or active state."""
        with self._lock:
            results = list(self._buses.values())
            if channel:
                chan_val = self._validate_channel(channel)
                results = [b for b in results if b.channel == chan_val]
            if active_only:
                # A bus is considered active when not muted and either no bus
                # is soloed or this bus is soloed.
                if self._soloed_buses:
                    results = [b for b in results
                               if b.solo and not b.muted]
                else:
                    results = [b for b in results if not b.muted]
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT), 1, _MAX_LIST_LIMIT)
            return results[:cap]

    def set_bus_volume(self, bus_id: str = "",
                       volume: float = 1.0
                       ) -> Tuple[bool, str, AudioBus]:
        """Set the volume of an audio bus."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False, f"Bus not found: {bus_id}", AudioBus(bus_id=bus_id)
            old_vol = bus.volume
            bus.volume = _clamp(_safe_float(volume, 1.0),
                                _VOLUME_MIN, _VOLUME_MAX)
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Bus volume set: {bus.name} "
                       f"{old_vol:.3f}->{bus.volume:.3f}",
                       source_id=bus_id,
                       data={"bus_id": bus_id, "old": old_vol,
                             "new": bus.volume})
            return True, f"Bus volume set to {bus.volume:.3f}", bus

    def mute_bus(self, bus_id: str = "") -> Tuple[bool, str, AudioBus]:
        """Toggle the mute state of an audio bus."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False, f"Bus not found: {bus_id}", AudioBus(bus_id=bus_id)
            bus.muted = not bus.muted
            state = "muted" if bus.muted else "unmuted"
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Bus {state}: {bus.name}",
                       source_id=bus_id,
                       data={"bus_id": bus_id, "muted": bus.muted})
            return True, f"Bus {state}", bus

    def solo_bus(self, bus_id: str = "") -> Tuple[bool, str, AudioBus]:
        """Toggle the solo state of an audio bus."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False, f"Bus not found: {bus_id}", AudioBus(bus_id=bus_id)
            bus.solo = not bus.solo
            if bus.solo:
                if bus_id not in self._soloed_buses:
                    self._soloed_buses.append(bus_id)
            else:
                if bus_id in self._soloed_buses:
                    self._soloed_buses.remove(bus_id)
            state = "soloed" if bus.solo else "unsoloed"
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Bus {state}: {bus.name}",
                       source_id=bus_id,
                       data={"bus_id": bus_id, "solo": bus.solo})
            return True, f"Bus {state}", bus

    # ------------------------------------------------------------------
    # Emitter Management
    # ------------------------------------------------------------------

    def register_emitter(self, emitter_id: str = "", name: str = "",
                         position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                         velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                         min_distance: float = 1.0,
                         max_distance: float = 100.0,
                         distance_model: str = AudioDistanceModel.INVERSE.value,
                         spatial_blend: float = 1.0,
                         priority: str = AudioPriority.NORMAL.value,
                         metadata: Optional[Dict[str, Any]] = None
                         ) -> Tuple[bool, str, Optional[AudioEmitter]]:
        """Register a positional audio emitter in 3D space."""
        with self._lock:
            if not emitter_id:
                emitter_id = _new_id(name or "emit", "emit")
            if emitter_id in self._emitters:
                return False, f"Emitter already exists: {emitter_id}", None
            if len(self._emitters) >= self._config.max_emitters:
                return False, "Maximum emitter capacity reached", None
            min_d = _clamp(_safe_float(min_distance, 1.0),
                           _DISTANCE_MIN, _DISTANCE_MAX)
            max_d = _clamp(_safe_float(max_distance, 100.0),
                           min_d, _DISTANCE_MAX)
            emitter = AudioEmitter(
                emitter_id=emitter_id,
                name=name or emitter_id,
                position=tuple(_safe_float(p, 0.0) for p in position),
                velocity=tuple(_safe_float(v, 0.0) for v in velocity),
                min_distance=min_d,
                max_distance=max_d,
                distance_model=self._validate_distance_model(distance_model),
                spatial_blend=_clamp(_safe_float(spatial_blend, 1.0),
                                     _SPATIAL_BLEND_MIN, _SPATIAL_BLEND_MAX),
                priority=self._validate_priority(priority),
                metadata=dict(metadata) if metadata else {},
            )
            self._emitters[emitter_id] = emitter
            self._emit(AudioEventKind.CREATED.value,
                       f"Emitter registered: {emitter.name}",
                       data={"emitter_id": emitter_id})
            self._update_stats()
            return True, f"Emitter registered: {emitter_id}", emitter

    def remove_emitter(self, emitter_id: str = "") -> Tuple[bool, str]:
        """Remove an audio emitter by its identifier."""
        with self._lock:
            if not emitter_id:
                return False, "emitter_id is required"
            emitter = self._emitters.pop(emitter_id, None)
            if emitter is None:
                return False, f"Emitter not found: {emitter_id}"
            # Detach the emitter from any sources bound to it.
            for src in self._sources.values():
                if src.emitter_id == emitter_id:
                    src.emitter_id = ""
            self._emit(AudioEventKind.CREATED.value,
                       f"Emitter removed: {emitter.name}",
                       data={"emitter_id": emitter_id})
            self._update_stats()
            return True, f"Emitter removed: {emitter_id}"

    def get_emitter(self, emitter_id: str = "") -> Optional[AudioEmitter]:
        """Return the audio emitter with the given identifier, or None."""
        with self._lock:
            return self._emitters.get(emitter_id)

    def list_emitters(self, limit: int = _DEFAULT_LIST_LIMIT
                      ) -> List[AudioEmitter]:
        """List audio emitters up to the given limit."""
        with self._lock:
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT),
                         1, _MAX_LIST_LIMIT)
            return list(self._emitters.values())[:cap]

    # ------------------------------------------------------------------
    # Listener Management
    # ------------------------------------------------------------------

    def register_listener(self, listener_id: str = "", name: str = "",
                          position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                          forward: Tuple[float, float, float] = (0.0, 0.0, -1.0),
                          up: Tuple[float, float, float] = (0.0, 1.0, 0.0),
                          velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                          gain: float = 1.0
                          ) -> Tuple[bool, str, Optional[AudioListener]]:
        """Register an audio listener with position and orientation."""
        with self._lock:
            if not listener_id:
                listener_id = _new_id(name or "listener", "listener")
            if listener_id in self._listeners:
                return False, f"Listener already exists: {listener_id}", None
            if len(self._listeners) >= _MAX_LISTENERS:
                return False, "Maximum listener capacity reached", None
            listener = AudioListener(
                listener_id=listener_id,
                name=name or listener_id,
                position=tuple(_safe_float(p, 0.0) for p in position),
                forward=tuple(_safe_float(f, 0.0) for f in forward),
                up=tuple(_safe_float(u, 0.0) for u in up),
                velocity=tuple(_safe_float(v, 0.0) for v in velocity),
                gain=_clamp(_safe_float(gain, 1.0),
                            _VOLUME_MIN, _VOLUME_MAX),
            )
            self._listeners[listener_id] = listener
            self._emit(AudioEventKind.CREATED.value,
                       f"Listener registered: {listener.name}",
                       data={"listener_id": listener_id})
            self._update_stats()
            return True, f"Listener registered: {listener_id}", listener

    def remove_listener(self, listener_id: str = "") -> Tuple[bool, str]:
        """Remove an audio listener by its identifier."""
        with self._lock:
            if not listener_id:
                return False, "listener_id is required"
            listener = self._listeners.pop(listener_id, None)
            if listener is None:
                return False, f"Listener not found: {listener_id}"
            self._emit(AudioEventKind.CREATED.value,
                       f"Listener removed: {listener.name}",
                       data={"listener_id": listener_id})
            self._update_stats()
            return True, f"Listener removed: {listener_id}"

    def get_listener(self, listener_id: str = "") -> Optional[AudioListener]:
        """Return the audio listener with the given identifier, or None."""
        with self._lock:
            return self._listeners.get(listener_id)

    def list_listeners(self, limit: int = _DEFAULT_LIST_LIMIT
                       ) -> List[AudioListener]:
        """List audio listeners up to the given limit."""
        with self._lock:
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT),
                         1, _MAX_LIST_LIMIT)
            return list(self._listeners.values())[:cap]

    def update_listener_position(self, listener_id: str = "",
                                 position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                                 forward: Tuple[float, float, float] = (0.0, 0.0, -1.0),
                                 up: Tuple[float, float, float] = (0.0, 1.0, 0.0),
                                 velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
                                 ) -> Tuple[bool, str, AudioListener]:
        """Update the position, orientation, and velocity of a listener."""
        with self._lock:
            listener = self._listeners.get(listener_id)
            if listener is None:
                return False, f"Listener not found: {listener_id}", \
                    AudioListener(listener_id=listener_id)
            listener.position = tuple(_safe_float(p, 0.0) for p in position)
            listener.forward = tuple(_safe_float(f, 0.0) for f in forward)
            listener.up = tuple(_safe_float(u, 0.0) for u in up)
            listener.velocity = tuple(_safe_float(v, 0.0) for v in velocity)
            self._emit(AudioEventKind.CREATED.value,
                       f"Listener position updated: {listener.name}",
                       source_id=listener_id,
                       data={"listener_id": listener_id,
                             "position": list(listener.position)})
            return True, f"Listener position updated: {listener_id}", listener

    # ------------------------------------------------------------------
    # Clip Management
    # ------------------------------------------------------------------

    def register_clip(self, clip_id: str = "", name: str = "",
                      audio_type: str = AudioType.SFX.value,
                      format: str = AudioFormat.MONO.value,
                      sample_rate: int = 44100, channels: int = 1,
                      duration: float = 1.0,
                      loop_mode: str = AudioLoopMode.ONE_SHOT.value,
                      priority: str = AudioPriority.NORMAL.value,
                      metadata: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[AudioClip]]:
        """Register a new audio clip in the clip catalog."""
        with self._lock:
            if not clip_id:
                clip_id = _new_id(name or "clip", "clip")
            if clip_id in self._clips:
                return False, f"Clip already exists: {clip_id}", None
            if len(self._clips) >= self._config.max_clips:
                return False, "Maximum clip capacity reached", None
            sr = int(_clamp(_safe_int(sample_rate, 44100),
                            _SAMPLE_RATE_MIN, _SAMPLE_RATE_MAX))
            ch = max(1, _safe_int(channels, 1))
            dur = _clamp(_safe_float(duration, 1.0),
                         _DURATION_MIN, _DURATION_MAX)
            clip = AudioClip(
                clip_id=clip_id,
                name=name or clip_id,
                audio_type=self._validate_audio_type(audio_type),
                format=self._validate_format(format),
                sample_rate=sr,
                channels=ch,
                duration=dur,
                sample_data=[],
                loop_mode=self._validate_loop_mode(loop_mode),
                priority=self._validate_priority(priority),
                metadata=dict(metadata) if metadata else {},
            )
            self._clips[clip_id] = clip
            self._emit(AudioEventKind.CREATED.value,
                       f"Clip registered: {clip.name}",
                       data={"clip_id": clip_id})
            self._update_stats()
            return True, f"Clip registered: {clip_id}", clip

    def remove_clip(self, clip_id: str = "") -> Tuple[bool, str]:
        """Remove an audio clip by its identifier."""
        with self._lock:
            if not clip_id:
                return False, "clip_id is required"
            clip = self._clips.pop(clip_id, None)
            if clip is None:
                return False, f"Clip not found: {clip_id}"
            # Stop any sources that were using this clip.
            for src in self._sources.values():
                if src.clip_id == clip_id:
                    src.status = AudioStatus.STOPPED.value
                    src.clip_id = ""
            self._emit(AudioEventKind.CREATED.value,
                       f"Clip removed: {clip.name}",
                       data={"clip_id": clip_id})
            self._update_stats()
            return True, f"Clip removed: {clip_id}"

    def get_clip(self, clip_id: str = "") -> Optional[AudioClip]:
        """Return the audio clip with the given identifier, or None."""
        with self._lock:
            return self._clips.get(clip_id)

    def list_clips(self, audio_type: str = "",
                   limit: int = _DEFAULT_LIST_LIMIT
                   ) -> List[AudioClip]:
        """List audio clips, optionally filtered by audio type."""
        with self._lock:
            results = list(self._clips.values())
            if audio_type:
                type_val = self._validate_audio_type(audio_type)
                results = [c for c in results if c.audio_type == type_val]
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT),
                         1, _MAX_LIST_LIMIT)
            return results[:cap]

    # ------------------------------------------------------------------
    # Source Management
    # ------------------------------------------------------------------

    def create_source(self, source_id: str = "", clip_id: str = "",
                      emitter_id: str = "", bus_id: str = "",
                      volume: float = 1.0, pitch: float = 1.0,
                      pan: float = 0.0,
                      loop_mode: str = AudioLoopMode.ONE_SHOT.value,
                      fade_in: float = 0.0, fade_out: float = 0.0,
                      metadata: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[AudioSource]]:
        """Create a new audio source bound to a clip, emitter, and bus."""
        with self._lock:
            if not source_id:
                self._source_counter += 1
                source_id = _new_id(f"src{self._source_counter}", "src")
            if source_id in self._sources:
                return False, f"Source already exists: {source_id}", None
            if len(self._sources) >= self._config.max_sources:
                return False, "Maximum source capacity reached", None
            # Validate that the clip exists when one is provided.
            if clip_id and clip_id not in self._clips:
                return False, f"Clip not found: {clip_id}", None
            # If a loop mode is not given, adopt the clip's loop mode.
            effective_loop = self._validate_loop_mode(loop_mode)
            if clip_id and not loop_mode:
                clip = self._clips.get(clip_id)
                if clip:
                    effective_loop = clip.loop_mode
            source = AudioSource(
                source_id=source_id,
                clip_id=clip_id,
                emitter_id=emitter_id,
                bus_id=bus_id,
                volume=_clamp(_safe_float(volume, 1.0),
                              _VOLUME_MIN, _VOLUME_MAX),
                pitch=_clamp(_safe_float(pitch, 1.0),
                             _PITCH_MIN, _PITCH_MAX),
                pan=_clamp(_safe_float(pan, 0.0),
                           _PAN_MIN, _PAN_MAX),
                loop_mode=effective_loop,
                status=AudioStatus.IDLE.value,
                play_position=0.0,
                fade_in=max(0.0, _safe_float(fade_in, 0.0)),
                fade_out=max(0.0, _safe_float(fade_out, 0.0)),
                metadata=dict(metadata) if metadata else {},
            )
            self._sources[source_id] = source
            self._emit(AudioEventKind.CREATED.value,
                       f"Source created: {source_id}",
                       source_id=source_id,
                       data={"source_id": source_id, "clip_id": clip_id,
                             "bus_id": bus_id})
            self._update_stats()
            return True, f"Source created: {source_id}", source

    def remove_source(self, source_id: str = "") -> Tuple[bool, str]:
        """Remove an audio source by its identifier."""
        with self._lock:
            if not source_id:
                return False, "source_id is required"
            source = self._sources.pop(source_id, None)
            if source is None:
                return False, f"Source not found: {source_id}"
            self._emit(AudioEventKind.STOPPED.value,
                       f"Source removed: {source_id}",
                       source_id=source_id,
                       data={"source_id": source_id})
            self._update_stats()
            return True, f"Source removed: {source_id}"

    def get_source(self, source_id: str = "") -> Optional[AudioSource]:
        """Return the audio source with the given identifier, or None."""
        with self._lock:
            return self._sources.get(source_id)

    def list_sources(self, status: str = "",
                     limit: int = _DEFAULT_LIST_LIMIT
                     ) -> List[AudioSource]:
        """List audio sources, optionally filtered by status."""
        with self._lock:
            results = list(self._sources.values())
            if status:
                status_val = self._validate_status(status)
                results = [s for s in results if s.status == status_val]
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT),
                         1, _MAX_LIST_LIMIT)
            return results[:cap]

    def play_source(self, source_id: str = ""
                    ) -> Tuple[bool, str, AudioSource]:
        """Start playback of an audio source."""
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", \
                    AudioSource(source_id=source_id)
            if source.clip_id and source.clip_id not in self._clips:
                source.status = AudioStatus.ERROR.value
                return False, f"Clip not found for source: {source_id}", source
            source.status = AudioStatus.PLAYING.value
            self._total_played += 1
            self._emit(AudioEventKind.PLAYED.value,
                       f"Source played: {source_id}",
                       source_id=source_id,
                       data={"source_id": source_id,
                             "clip_id": source.clip_id})
            self._update_stats()
            return True, f"Source played: {source_id}", source

    def pause_source(self, source_id: str = ""
                     ) -> Tuple[bool, str, AudioSource]:
        """Pause playback of an audio source."""
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", \
                    AudioSource(source_id=source_id)
            if source.status != AudioStatus.PLAYING.value:
                return False, f"Source is not playing: {source_id}", source
            source.status = AudioStatus.PAUSED.value
            self._emit(AudioEventKind.PAUSED.value,
                       f"Source paused: {source_id}",
                       source_id=source_id,
                       data={"source_id": source_id})
            self._update_stats()
            return True, f"Source paused: {source_id}", source

    def stop_source(self, source_id: str = ""
                    ) -> Tuple[bool, str, AudioSource]:
        """Stop playback of an audio source and reset its position."""
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", \
                    AudioSource(source_id=source_id)
            source.status = AudioStatus.STOPPED.value
            source.play_position = 0.0
            self._emit(AudioEventKind.STOPPED.value,
                       f"Source stopped: {source_id}",
                       source_id=source_id,
                       data={"source_id": source_id})
            self._update_stats()
            return True, f"Source stopped: {source_id}", source

    def set_source_volume(self, source_id: str = "",
                          volume: float = 1.0
                          ) -> Tuple[bool, str, AudioSource]:
        """Set the volume of an audio source."""
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", \
                    AudioSource(source_id=source_id)
            old_vol = source.volume
            source.volume = _clamp(_safe_float(volume, 1.0),
                                   _VOLUME_MIN, _VOLUME_MAX)
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Source volume set: {source_id} "
                       f"{old_vol:.3f}->{source.volume:.3f}",
                       source_id=source_id,
                       data={"source_id": source_id, "old": old_vol,
                             "new": source.volume})
            return True, f"Source volume set to {source.volume:.3f}", source

    def set_source_pitch(self, source_id: str = "",
                         pitch: float = 1.0
                         ) -> Tuple[bool, str, AudioSource]:
        """Set the pitch of an audio source."""
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", \
                    AudioSource(source_id=source_id)
            old_pitch = source.pitch
            source.pitch = _clamp(_safe_float(pitch, 1.0),
                                  _PITCH_MIN, _PITCH_MAX)
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Source pitch set: {source_id} "
                       f"{old_pitch:.3f}->{source.pitch:.3f}",
                       source_id=source_id,
                       data={"source_id": source_id, "old": old_pitch,
                             "new": source.pitch})
            return True, f"Source pitch set to {source.pitch:.3f}", source

    def set_source_pan(self, source_id: str = "",
                       pan: float = 0.0
                       ) -> Tuple[bool, str, AudioSource]:
        """Set the stereo pan of an audio source."""
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", \
                    AudioSource(source_id=source_id)
            old_pan = source.pan
            source.pan = _clamp(_safe_float(pan, 0.0),
                                _PAN_MIN, _PAN_MAX)
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Source pan set: {source_id} "
                       f"{old_pan:.3f}->{source.pan:.3f}",
                       source_id=source_id,
                       data={"source_id": source_id, "old": old_pan,
                             "new": source.pan})
            return True, f"Source pan set to {source.pan:.3f}", source

    # ------------------------------------------------------------------
    # Music System
    # ------------------------------------------------------------------

    def create_music_track(self, track_id: str = "", name: str = "",
                           bpm: float = 120.0,
                           time_signature: str = "4/4",
                           key: str = "C_major",
                           metadata: Optional[Dict[str, Any]] = None
                           ) -> Tuple[bool, str, Optional[MusicTrack]]:
        """Create a new music track that can hold multiple layers."""
        with self._lock:
            if not track_id:
                track_id = _new_id(name or "track", "track")
            if track_id in self._tracks:
                return False, f"Track already exists: {track_id}", None
            if len(self._tracks) >= self._config.max_tracks:
                return False, "Maximum track capacity reached", None
            track = MusicTrack(
                track_id=track_id,
                name=name or track_id,
                layers=[],
                bpm=_clamp(_safe_float(bpm, 120.0), _BPM_MIN, _BPM_MAX),
                time_signature=time_signature or "4/4",
                key=key or "C_major",
                current_layer="",
                playing=False,
                metadata=dict(metadata) if metadata else {},
            )
            self._tracks[track_id] = track
            self._emit(AudioEventKind.CREATED.value,
                       f"Music track created: {track.name}",
                       data={"track_id": track_id})
            self._update_stats()
            return True, f"Music track created: {track_id}", track

    def remove_music_track(self, track_id: str = "") -> Tuple[bool, str]:
        """Remove a music track and all of its layers."""
        with self._lock:
            if not track_id:
                return False, "track_id is required"
            track = self._tracks.pop(track_id, None)
            if track is None:
                return False, f"Track not found: {track_id}"
            # Remove all layers belonging to this track from the global
            # layer store so they do not linger as orphans.
            for layer in track.layers:
                self._layers.pop(layer.layer_id, None)
            self._emit(AudioEventKind.STOPPED.value,
                       f"Music track removed: {track.name}",
                       data={"track_id": track_id})
            self._update_stats()
            return True, f"Music track removed: {track_id}"

    def get_music_track(self, track_id: str = "") -> Optional[MusicTrack]:
        """Return the music track with the given identifier, or None."""
        with self._lock:
            return self._tracks.get(track_id)

    def list_music_tracks(self, limit: int = _DEFAULT_LIST_LIMIT
                          ) -> List[MusicTrack]:
        """List music tracks up to the given limit."""
        with self._lock:
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT),
                         1, _MAX_LIST_LIMIT)
            return list(self._tracks.values())[:cap]

    def add_music_layer(self, track_id: str = "", layer_id: str = "",
                        name: str = "", clip_id: str = "",
                        bus_id: str = "", volume: float = 1.0,
                        condition: str = "",
                        priority: str = AudioPriority.NORMAL.value,
                        metadata: Optional[Dict[str, Any]] = None
                        ) -> Tuple[bool, str, MusicTrack]:
        """Add a new layer to an existing music track."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, f"Track not found: {track_id}", \
                    MusicTrack(track_id=track_id)
            if not layer_id:
                layer_id = _new_id(name or "layer", "layer")
            # Check for duplicate layer id within the track.
            existing_ids = [l.layer_id for l in track.layers]
            if layer_id in existing_ids:
                return False, f"Layer already exists in track: {layer_id}", track
            if len(track.layers) >= _MAX_LAYERS_PER_TRACK:
                return False, "Maximum layers per track reached", track
            # Validate that the clip exists when one is provided.
            if clip_id and clip_id not in self._clips:
                return False, f"Clip not found: {clip_id}", track
            layer = MusicLayer(
                layer_id=layer_id,
                name=name or layer_id,
                clip_id=clip_id,
                bus_id=bus_id,
                volume=_clamp(_safe_float(volume, 1.0),
                              _VOLUME_MIN, _VOLUME_MAX),
                active=False,
                condition=condition or "",
                priority=self._validate_priority(priority),
                metadata=dict(metadata) if metadata else {},
            )
            track.layers.append(layer)
            self._layers[layer_id] = layer
            if not track.current_layer:
                track.current_layer = layer_id
            self._emit(AudioEventKind.CREATED.value,
                       f"Music layer added: {layer.name} to {track.name}",
                       data={"track_id": track_id, "layer_id": layer_id})
            self._update_stats()
            return True, f"Music layer added: {layer_id}", track

    def remove_music_layer(self, track_id: str = "",
                           layer_id: str = ""
                           ) -> Tuple[bool, str, MusicTrack]:
        """Remove a layer from a music track."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, f"Track not found: {track_id}", \
                    MusicTrack(track_id=track_id)
            found = None
            for i, layer in enumerate(track.layers):
                if layer.layer_id == layer_id:
                    found = track.layers.pop(i)
                    break
            if found is None:
                return False, f"Layer not found in track: {layer_id}", track
            self._layers.pop(layer_id, None)
            if track.current_layer == layer_id:
                track.current_layer = track.layers[0].layer_id if track.layers else ""
            self._emit(AudioEventKind.STOPPED.value,
                       f"Music layer removed: {found.name} from {track.name}",
                       data={"track_id": track_id, "layer_id": layer_id})
            self._update_stats()
            return True, f"Music layer removed: {layer_id}", track

    def play_music_track(self, track_id: str = ""
                         ) -> Tuple[bool, str, MusicTrack]:
        """Start playback of a music track, activating its current layer."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, f"Track not found: {track_id}", \
                    MusicTrack(track_id=track_id)
            track.playing = True
            # Activate the current layer if one is set.
            if track.current_layer:
                for layer in track.layers:
                    if layer.layer_id == track.current_layer:
                        layer.active = True
                        break
            self._emit(AudioEventKind.PLAYED.value,
                       f"Music track played: {track.name}",
                       data={"track_id": track_id,
                             "current_layer": track.current_layer})
            self._update_stats()
            return True, f"Music track played: {track_id}", track

    def stop_music_track(self, track_id: str = ""
                         ) -> Tuple[bool, str, MusicTrack]:
        """Stop playback of a music track and deactivate all layers."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, f"Track not found: {track_id}", \
                    MusicTrack(track_id=track_id)
            track.playing = False
            for layer in track.layers:
                layer.active = False
            self._emit(AudioEventKind.STOPPED.value,
                       f"Music track stopped: {track.name}",
                       data={"track_id": track_id})
            self._update_stats()
            return True, f"Music track stopped: {track_id}", track

    def set_music_layer_volume(self, track_id: str = "",
                               layer_id: str = "",
                               volume: float = 1.0
                               ) -> Tuple[bool, str, MusicTrack]:
        """Set the volume of a specific layer within a music track."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, f"Track not found: {track_id}", \
                    MusicTrack(track_id=track_id)
            found = None
            for layer in track.layers:
                if layer.layer_id == layer_id:
                    found = layer
                    break
            if found is None:
                return False, f"Layer not found in track: {layer_id}", track
            old_vol = found.volume
            found.volume = _clamp(_safe_float(volume, 1.0),
                                  _VOLUME_MIN, _VOLUME_MAX)
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Music layer volume set: {found.name} "
                       f"{old_vol:.3f}->{found.volume:.3f}",
                       data={"track_id": track_id, "layer_id": layer_id,
                             "old": old_vol, "new": found.volume})
            return True, f"Music layer volume set to {found.volume:.3f}", track

    def transition_music_layer(self, track_id: str = "",
                               target_layer_id: str = "",
                               fade_time: float = 1.0
                               ) -> Tuple[bool, str, MusicTrack]:
        """Transition a music track to a new layer with a fade."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, f"Track not found: {track_id}", \
                    MusicTrack(track_id=track_id)
            target = None
            for layer in track.layers:
                if layer.layer_id == target_layer_id:
                    target = layer
                    break
            if target is None:
                return False, f"Target layer not found: {target_layer_id}", track
            old_layer_id = track.current_layer
            # Deactivate the old layer and activate the new one.
            for layer in track.layers:
                if layer.layer_id == old_layer_id:
                    layer.active = False
            target.active = True
            track.current_layer = target_layer_id
            # Record the fade time in the target layer metadata so the
            # tick loop can apply a gradual volume ramp if desired.
            target.metadata["transition_fade_time"] = _safe_float(fade_time, 1.0)
            target.metadata["transition_started_at"] = _now()
            self._emit(AudioEventKind.BUS_ROUTED.value,
                       f"Music layer transition: {track.name} "
                       f"{old_layer_id}->{target_layer_id}",
                       data={"track_id": track_id,
                             "old_layer": old_layer_id,
                             "new_layer": target_layer_id,
                             "fade_time": _safe_float(fade_time, 1.0)})
            return True, f"Music layer transition: {target_layer_id}", track

    # ------------------------------------------------------------------
    # Effects Management
    # ------------------------------------------------------------------

    def register_effect(self, effect_id: str = "", name: str = "",
                        effect_type: str = "",
                        parameters: Optional[Dict[str, Any]] = None,
                        enabled: bool = True, order: int = 0,
                        metadata: Optional[Dict[str, Any]] = None
                        ) -> Tuple[bool, str, Optional[AudioEffect]]:
        """Register a new DSP effect in the effect catalog."""
        with self._lock:
            if not effect_id:
                effect_id = _new_id(name or "fx", "fx")
            if effect_id in self._effects:
                return False, f"Effect already exists: {effect_id}", None
            if len(self._effects) >= self._config.max_effects:
                return False, "Maximum effect capacity reached", None
            effect = AudioEffect(
                effect_id=effect_id,
                name=name or effect_id,
                effect_type=effect_type or "generic",
                parameters=dict(parameters) if parameters else {},
                enabled=bool(enabled),
                order=_safe_int(order, 0),
                metadata=dict(metadata) if metadata else {},
            )
            self._effects[effect_id] = effect
            self._emit(AudioEventKind.CREATED.value,
                       f"Effect registered: {effect.name}",
                       data={"effect_id": effect_id})
            self._update_stats()
            return True, f"Effect registered: {effect_id}", effect

    def remove_effect(self, effect_id: str = "") -> Tuple[bool, str]:
        """Remove a DSP effect from the catalog and all bus chains."""
        with self._lock:
            if not effect_id:
                return False, "effect_id is required"
            effect = self._effects.pop(effect_id, None)
            if effect is None:
                return False, f"Effect not found: {effect_id}"
            # Remove the effect id from every bus effect chain.
            for bus in self._buses.values():
                while effect_id in bus.effects_chain:
                    bus.effects_chain.remove(effect_id)
            self._emit(AudioEventKind.CREATED.value,
                       f"Effect removed: {effect.name}",
                       data={"effect_id": effect_id})
            self._update_stats()
            return True, f"Effect removed: {effect_id}"

    def get_effect(self, effect_id: str = "") -> Optional[AudioEffect]:
        """Return the DSP effect with the given identifier, or None."""
        with self._lock:
            return self._effects.get(effect_id)

    def list_effects(self, enabled_only: bool = False,
                     limit: int = _DEFAULT_LIST_LIMIT
                     ) -> List[AudioEffect]:
        """List DSP effects, optionally filtered to enabled ones only."""
        with self._lock:
            results = list(self._effects.values())
            if enabled_only:
                results = [e for e in results if e.enabled]
            results.sort(key=lambda e: e.order)
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT),
                         1, _MAX_LIST_LIMIT)
            return results[:cap]

    def add_effect_to_bus(self, bus_id: str = "",
                          effect_id: str = ""
                          ) -> Tuple[bool, str, AudioBus]:
        """Append a DSP effect to the end of a bus effect chain."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False, f"Bus not found: {bus_id}", AudioBus(bus_id=bus_id)
            if effect_id not in self._effects:
                return False, f"Effect not found: {effect_id}", bus
            if effect_id in bus.effects_chain:
                return False, f"Effect already on bus: {effect_id}", bus
            bus.effects_chain.append(effect_id)
            self._emit(AudioEventKind.BUS_ROUTED.value,
                       f"Effect added to bus: {effect_id} -> {bus.name}",
                       data={"bus_id": bus_id, "effect_id": effect_id})
            return True, f"Effect {effect_id} added to bus {bus_id}", bus

    def remove_effect_from_bus(self, bus_id: str = "",
                               effect_id: str = ""
                               ) -> Tuple[bool, str, AudioBus]:
        """Remove a DSP effect from a bus effect chain."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False, f"Bus not found: {bus_id}", AudioBus(bus_id=bus_id)
            if effect_id not in bus.effects_chain:
                return False, f"Effect not on bus: {effect_id}", bus
            bus.effects_chain.remove(effect_id)
            self._emit(AudioEventKind.BUS_ROUTED.value,
                       f"Effect removed from bus: {effect_id} <- {bus.name}",
                       data={"bus_id": bus_id, "effect_id": effect_id})
            return True, f"Effect {effect_id} removed from bus {bus_id}", bus

    # ------------------------------------------------------------------
    # Reverb Zone Management
    # ------------------------------------------------------------------

    def register_reverb_zone(self, zone_id: str = "", name: str = "",
                             min_distance: float = 1.0,
                             max_distance: float = 50.0,
                             reverb_preset: str = "generic",
                             room_size: float = 0.5,
                             damping: float = 0.5,
                             wet_level: float = 0.5,
                             dry_level: float = 0.5,
                             metadata: Optional[Dict[str, Any]] = None
                             ) -> Tuple[bool, str, Optional[AudioReverbZone]]:
        """Register a spatial reverb zone."""
        with self._lock:
            if not zone_id:
                zone_id = _new_id(name or "zone", "zone")
            if zone_id in self._reverb_zones:
                return False, f"Reverb zone already exists: {zone_id}", None
            if len(self._reverb_zones) >= _MAX_REVERB_ZONES:
                return False, "Maximum reverb zone capacity reached", None
            min_d = _clamp(_safe_float(min_distance, 1.0),
                           _DISTANCE_MIN, _DISTANCE_MAX)
            max_d = _clamp(_safe_float(max_distance, 50.0),
                           min_d, _DISTANCE_MAX)
            zone = AudioReverbZone(
                zone_id=zone_id,
                name=name or zone_id,
                min_distance=min_d,
                max_distance=max_d,
                reverb_preset=reverb_preset or "generic",
                room_size=_clamp(_safe_float(room_size, 0.5),
                                 _ROOM_SIZE_MIN, _ROOM_SIZE_MAX),
                damping=_clamp(_safe_float(damping, 0.5),
                               _DAMPING_MIN, _DAMPING_MAX),
                wet_level=_clamp(_safe_float(wet_level, 0.5),
                                 _WET_LEVEL_MIN, _WET_LEVEL_MAX),
                dry_level=_clamp(_safe_float(dry_level, 0.5),
                                 _DRY_LEVEL_MIN, _DRY_LEVEL_MAX),
                metadata=dict(metadata) if metadata else {},
            )
            self._reverb_zones[zone_id] = zone
            self._emit(AudioEventKind.CREATED.value,
                       f"Reverb zone registered: {zone.name}",
                       data={"zone_id": zone_id})
            self._update_stats()
            return True, f"Reverb zone registered: {zone_id}", zone

    def remove_reverb_zone(self, zone_id: str = "") -> Tuple[bool, str]:
        """Remove a reverb zone by its identifier."""
        with self._lock:
            if not zone_id:
                return False, "zone_id is required"
            zone = self._reverb_zones.pop(zone_id, None)
            if zone is None:
                return False, f"Reverb zone not found: {zone_id}"
            self._emit(AudioEventKind.CREATED.value,
                       f"Reverb zone removed: {zone.name}",
                       data={"zone_id": zone_id})
            self._update_stats()
            return True, f"Reverb zone removed: {zone_id}"

    def get_reverb_zone(self, zone_id: str = "") -> Optional[AudioReverbZone]:
        """Return the reverb zone with the given identifier, or None."""
        with self._lock:
            return self._reverb_zones.get(zone_id)

    def list_reverb_zones(self, limit: int = _DEFAULT_LIST_LIMIT
                          ) -> List[AudioReverbZone]:
        """List reverb zones up to the given limit."""
        with self._lock:
            cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT),
                         1, _MAX_LIST_LIMIT)
            return list(self._reverb_zones.values())[:cap]

    # ------------------------------------------------------------------
    # Spatial Audio & Utilities
    # ------------------------------------------------------------------

    def set_emitter_position(self, emitter_id: str = "",
                             position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                             velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
                             ) -> Tuple[bool, str, AudioEmitter]:
        """Update the position and velocity of an audio emitter."""
        with self._lock:
            emitter = self._emitters.get(emitter_id)
            if emitter is None:
                return False, f"Emitter not found: {emitter_id}", \
                    AudioEmitter(emitter_id=emitter_id)
            emitter.position = tuple(_safe_float(p, 0.0) for p in position)
            emitter.velocity = tuple(_safe_float(v, 0.0) for v in velocity)
            self._emit(AudioEventKind.CREATED.value,
                       f"Emitter position updated: {emitter.name}",
                       source_id=emitter_id,
                       data={"emitter_id": emitter_id,
                             "position": list(emitter.position),
                             "velocity": list(emitter.velocity)})
            return True, f"Emitter position updated: {emitter_id}", emitter

    def calculate_spatial_attenuation(self, emitter_id: str = "",
                                      listener_id: str = ""
                                      ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute distance-based volume attenuation for an emitter.

        Applies the emitter's distance model (linear, inverse, or
        exponential) to determine how loud the emitter should be at the
        listener's position. Returns a dictionary with distance, raw
        attenuation, clamped volume factor, and pan estimate.
        """
        with self._lock:
            emitter = self._emitters.get(emitter_id)
            if emitter is None:
                return False, f"Emitter not found: {emitter_id}", {}
            listener = self._listeners.get(listener_id)
            if listener is None:
                # Fall back to the first registered listener.
                if self._listeners:
                    listener = next(iter(self._listeners.values()))
                else:
                    return False, f"Listener not found: {listener_id}", {}

            distance = _distance3d(emitter.position, listener.position)
            min_d = emitter.min_distance
            max_d = emitter.max_distance

            # Compute raw attenuation based on the distance model.
            model = emitter.distance_model
            if distance <= min_d:
                attenuation = 1.0
            elif distance >= max_d:
                attenuation = 0.0
            elif model == AudioDistanceModel.LINEAR.value:
                # Linear falloff from 1.0 at min_distance to 0.0 at max_distance.
                span = max_d - min_d
                if span <= 0:
                    attenuation = 0.0
                else:
                    attenuation = 1.0 - (distance - min_d) / span
            elif model == AudioDistanceModel.EXPONENTIAL.value:
                # Exponential falloff.
                span = max_d - min_d
                if span <= 0:
                    attenuation = 0.0
                else:
                    ratio = (distance - min_d) / span
                    attenuation = max(0.0, 1.0 - ratio ** 2)
            else:
                # Inverse distance model (default).
                # attenuation = min_d / (min_d + rolloff * (distance - min_d))
                rolloff = 1.0
                if distance <= min_d:
                    attenuation = 1.0
                else:
                    attenuation = min_d / (min_d + rolloff * (distance - min_d))
                    # Clamp so it reaches zero at max_distance.
                    if distance >= max_d:
                        attenuation = 0.0

            attenuation = _clamp(attenuation, 0.0, 1.0)

            # Estimate stereo pan from the relative position of the emitter
            # to the listener's forward vector. The right vector is the
            # cross product of forward and up.
            dx = emitter.position[0] - listener.position[0]
            dz = emitter.position[2] - listener.position[2]
            fwd_x = listener.forward[0]
            fwd_y = listener.forward[1]
            fwd_z = listener.forward[2]
            up_x = listener.up[0]
            up_y = listener.up[1]
            up_z = listener.up[2]
            # right = forward x up (cross product).
            right_x = fwd_y * up_z - fwd_z * up_y
            right_y = fwd_z * up_x - fwd_x * up_z
            right_z = fwd_x * up_y - fwd_y * up_x
            # Project delta onto the right vector for pan.
            right_len = math.sqrt(right_x ** 2 + right_y ** 2 + right_z ** 2)
            if right_len > 0.0001:
                pan = (dx * right_x + dz * right_z) / right_len
                pan = _clamp(pan / max(max_d, 1.0), _PAN_MIN, _PAN_MAX)
            else:
                pan = 0.0

            spatial_blend = emitter.spatial_blend
            effective_volume = attenuation * spatial_blend + (1.0 - spatial_blend)

            result = {
                "emitter_id": emitter_id,
                "listener_id": listener.listener_id,
                "distance": round(distance, 4),
                "min_distance": min_d,
                "max_distance": max_d,
                "distance_model": model,
                "attenuation": round(attenuation, 6),
                "spatial_blend": spatial_blend,
                "effective_volume": round(effective_volume, 6),
                "pan": round(pan, 4),
                "within_range": distance <= max_d,
            }
            return True, f"Attenuation computed for {emitter_id}", result

    def calculate_doppler_shift(self, emitter_id: str = "",
                                listener_id: str = ""
                                ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the doppler pitch shift for a moving emitter.

        Uses the relative velocity between the emitter and listener
        along the line of sight, scaled by the configured doppler factor
        and speed of sound. Returns the pitch multiplier that should be
        applied to sources bound to this emitter.
        """
        with self._lock:
            emitter = self._emitters.get(emitter_id)
            if emitter is None:
                return False, f"Emitter not found: {emitter_id}", {}
            listener = self._listeners.get(listener_id)
            if listener is None:
                if self._listeners:
                    listener = next(iter(self._listeners.values()))
                else:
                    return False, f"Listener not found: {listener_id}", {}

            # Relative velocity vector.
            rel_vx = emitter.velocity[0] - listener.velocity[0]
            rel_vy = emitter.velocity[1] - listener.velocity[1]
            rel_vz = emitter.velocity[2] - listener.velocity[2]

            # Direction from listener to emitter (line of sight).
            dx = emitter.position[0] - listener.position[0]
            dy = emitter.position[1] - listener.position[1]
            dz = emitter.position[2] - listener.position[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)

            if dist < 0.0001:
                radial_velocity = 0.0
            else:
                # Project relative velocity onto the line of sight.
                radial_velocity = (rel_vx * dx + rel_vy * dy + rel_vz * dz) / dist

            speed_of_sound = self._config.speed_of_sound
            if speed_of_sound <= 0:
                speed_of_sound = 343.3
            doppler_factor = self._config.doppler_factor

            # Doppler formula: pitch = speed_of_sound /
            # (speed_of_sound - doppler_factor * radial_velocity)
            denominator = speed_of_sound - doppler_factor * radial_velocity
            if abs(denominator) < 0.001:
                pitch_shift = 1.0
            else:
                pitch_shift = speed_of_sound / denominator
            # Clamp to a reasonable range to avoid extreme shifts.
            pitch_shift = _clamp(pitch_shift, _PITCH_MIN, _PITCH_MAX)

            result = {
                "emitter_id": emitter_id,
                "listener_id": listener.listener_id,
                "radial_velocity": round(radial_velocity, 4),
                "doppler_factor": doppler_factor,
                "speed_of_sound": speed_of_sound,
                "pitch_shift": round(pitch_shift, 6),
                "approaching": radial_velocity > 0,
            }
            return True, f"Doppler shift computed for {emitter_id}", result

    def get_active_reverb_zone(self, listener_id: str = ""
                               ) -> Tuple[bool, str, Optional[AudioReverbZone]]:
        """Find the closest active reverb zone for a given listener.

        Returns the reverb zone whose range contains the listener, or
        the nearest zone if the listener is outside all zones. When no
        zones are registered, returns None.
        """
        with self._lock:
            listener = self._listeners.get(listener_id)
            if listener is None:
                if self._listeners:
                    listener = next(iter(self._listeners.values()))
                else:
                    return False, f"Listener not found: {listener_id}", None
            if not self._reverb_zones:
                return True, "No reverb zones registered", None

            # Find a zone that contains the listener.
            best_zone = None
            best_distance = float("inf")
            for zone in self._reverb_zones.values():
                # Use the zone center (assumed at origin of the zone).
                # Distance from listener to zone origin.
                dist = math.sqrt(
                    listener.position[0] ** 2 +
                    listener.position[1] ** 2 +
                    listener.position[2] ** 2
                )
                if zone.min_distance <= dist <= zone.max_distance:
                    # Listener is inside this zone; pick the one with the
                    # smallest range for the tightest fit.
                    range_span = zone.max_distance - zone.min_distance
                    if range_span < best_distance:
                        best_distance = range_span
                        best_zone = zone
                elif dist < best_distance:
                    best_distance = dist
                    if best_zone is None:
                        best_zone = zone

            if best_zone is None:
                best_zone = next(iter(self._reverb_zones.values()))
            return True, f"Active reverb zone: {best_zone.zone_id}", best_zone

    def stop_all_sources(self) -> Tuple[bool, str, int]:
        """Stop every playing or paused audio source."""
        with self._lock:
            count = 0
            for source in self._sources.values():
                if source.status in (AudioStatus.PLAYING.value,
                                     AudioStatus.PAUSED.value):
                    source.status = AudioStatus.STOPPED.value
                    source.play_position = 0.0
                    count += 1
            self._emit(AudioEventKind.STOPPED.value,
                       f"Stopped all sources ({count})",
                       data={"count": count})
            self._update_stats()
            return True, f"Stopped {count} sources", count

    def pause_all_sources(self) -> Tuple[bool, str, int]:
        """Pause every currently playing audio source."""
        with self._lock:
            count = 0
            for source in self._sources.values():
                if source.status == AudioStatus.PLAYING.value:
                    source.status = AudioStatus.PAUSED.value
                    count += 1
            self._emit(AudioEventKind.PAUSED.value,
                       f"Paused all sources ({count})",
                       data={"count": count})
            self._update_stats()
            return True, f"Paused {count} sources", count

    def resume_all_sources(self) -> Tuple[bool, str, int]:
        """Resume every paused audio source."""
        with self._lock:
            count = 0
            for source in self._sources.values():
                if source.status == AudioStatus.PAUSED.value:
                    source.status = AudioStatus.PLAYING.value
                    count += 1
            self._emit(AudioEventKind.RESUMED.value,
                       f"Resumed all sources ({count})",
                       data={"count": count})
            self._update_stats()
            return True, f"Resumed {count} sources", count

    def set_master_volume(self, volume: float = 1.0
                          ) -> Tuple[bool, str, float]:
        """Set the master volume on the audio configuration."""
        with self._lock:
            old_vol = self._config.master_volume
            self._config.master_volume = _clamp(_safe_float(volume, 1.0),
                                                _VOLUME_MIN, _VOLUME_MAX)
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Master volume set: {old_vol:.3f}->"
                       f"{self._config.master_volume:.3f}",
                       data={"old": old_vol,
                             "new": self._config.master_volume})
            return True, f"Master volume set to {self._config.master_volume:.3f}", \
                self._config.master_volume

    def get_bus_levels(self) -> Dict[str, Any]:
        """Return the current volume and mute/solo state for every bus."""
        with self._lock:
            levels: Dict[str, Any] = {}
            for bus in self._buses.values():
                # Determine if the bus is audible given solo state.
                audible = True
                if bus.muted:
                    audible = False
                elif self._soloed_buses and bus.bus_id not in self._soloed_buses:
                    audible = False
                levels[bus.bus_id] = {
                    "name": bus.name,
                    "channel": bus.channel,
                    "volume": round(bus.volume, 6),
                    "muted": bus.muted,
                    "solo": bus.solo,
                    "audible": audible,
                    "effect_count": len(bus.effects_chain),
                    "source_count": sum(
                        1 for s in self._sources.values()
                        if s.bus_id == bus.bus_id
                    ),
                    "active_source_count": sum(
                        1 for s in self._sources.values()
                        if s.bus_id == bus.bus_id
                        and s.status == AudioStatus.PLAYING.value
                    ),
                }
            return levels

    def count_sources_by_status(self) -> Dict[str, int]:
        """Return a count of sources grouped by their status."""
        with self._lock:
            counts: Dict[str, int] = {}
            for status in AudioStatus:
                counts[status.value] = 0
            for source in self._sources.values():
                counts[source.status] = counts.get(source.status, 0) + 1
            return counts

    def get_source_spatial_info(self, source_id: str = ""
                                ) -> Tuple[bool, str, Dict[str, Any]]:
        """Return spatial audio information for a source.

        Combines the source's emitter and the first listener to compute
        distance, attenuation, pan, and doppler pitch shift in one call.
        """
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", {}
            info: Dict[str, Any] = {
                "source_id": source_id,
                "clip_id": source.clip_id,
                "emitter_id": source.emitter_id,
                "bus_id": source.bus_id,
                "volume": round(source.volume, 6),
                "pitch": round(source.pitch, 6),
                "pan": round(source.pan, 6),
                "status": source.status,
                "play_position": round(source.play_position, 6),
                "spatial": False,
            }
            if not source.emitter_id:
                return True, "Source has no emitter (non-spatial)", info
            emitter = self._emitters.get(source.emitter_id)
            if emitter is None:
                return True, "Emitter not found (non-spatial)", info
            # Use the first listener if one exists.
            if not self._listeners:
                return True, "No listener registered", info
            listener = next(iter(self._listeners.values()))

            # Compute attenuation.
            ok_att, msg_att, att_data = self.calculate_spatial_attenuation(
                source.emitter_id, listener.listener_id)
            if ok_att:
                info["spatial"] = True
                info["attenuation"] = att_data.get("attenuation", 1.0)
                info["distance"] = att_data.get("distance", 0.0)
                info["spatial_pan"] = att_data.get("pan", 0.0)
                info["effective_volume"] = att_data.get("effective_volume", 1.0)

            # Compute doppler shift.
            ok_dop, msg_dop, dop_data = self.calculate_doppler_shift(
                source.emitter_id, listener.listener_id)
            if ok_dop:
                info["doppler_pitch_shift"] = dop_data.get("pitch_shift", 1.0)
                info["radial_velocity"] = dop_data.get("radial_velocity", 0.0)
                info["approaching"] = dop_data.get("approaching", False)

            return True, f"Spatial info for {source_id}", info

    def export_clip(self, clip_id: str = ""
                    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Export an audio clip as a JSON-serializable dictionary.

        The exported dictionary includes all clip metadata, format info,
        and a truncated view of the sample data (first 256 samples) to
        keep the payload manageable for network transfer.
        """
        with self._lock:
            clip = self._clips.get(clip_id)
            if clip is None:
                return False, f"Clip not found: {clip_id}", {}
            exported = clip.to_dict()
            # Truncate sample data for export to avoid huge payloads.
            if len(clip.sample_data) > 256:
                exported["sample_data_preview"] = clip.sample_data[:256]
                exported["sample_data_truncated"] = True
            else:
                exported["sample_data_preview"] = list(clip.sample_data)
                exported["sample_data_truncated"] = False
            # Remove the full sample data from the export.
            exported["sample_data"] = []
            exported["sample_count"] = len(clip.sample_data)
            return True, f"Clip exported: {clip_id}", exported

    def set_source_loop_mode(self, source_id: str = "",
                             loop_mode: str = AudioLoopMode.ONE_SHOT.value
                             ) -> Tuple[bool, str, AudioSource]:
        """Change the loop mode of an existing audio source."""
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", \
                    AudioSource(source_id=source_id)
            old_mode = source.loop_mode
            source.loop_mode = self._validate_loop_mode(loop_mode)
            self._emit(AudioEventKind.CREATED.value,
                       f"Source loop mode set: {source_id} "
                       f"{old_mode}->{source.loop_mode}",
                       source_id=source_id,
                       data={"source_id": source_id, "old": old_mode,
                             "new": source.loop_mode})
            return True, f"Source loop mode set to {source.loop_mode}", source

    def get_bus_effect_chain(self, bus_id: str = ""
                             ) -> Tuple[bool, str, List[AudioEffect]]:
        """Return the full effect objects attached to a bus chain."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False, f"Bus not found: {bus_id}", []
            effects: List[AudioEffect] = []
            for fx_id in bus.effects_chain:
                fx = self._effects.get(fx_id)
                if fx is not None:
                    effects.append(fx)
            return True, f"Bus effect chain has {len(effects)} effects", effects

    def get_active_clips(self) -> List[AudioClip]:
        """Return clips that are currently used by at least one source."""
        with self._lock:
            active_ids = set()
            for source in self._sources.values():
                if source.clip_id:
                    active_ids.add(source.clip_id)
            return [self._clips[cid] for cid in active_ids
                    if cid in self._clips]

    def import_clip(self, clip_data: Optional[Dict[str, Any]] = None
                    ) -> Tuple[bool, str, Optional[AudioClip]]:
        """Import a clip from a dictionary previously produced by export.

        Creates a new clip from the provided dictionary. The clip id is
        taken from the dictionary or auto-generated. Sample data from
        the preview is imported when present.
        """
        with self._lock:
            if not clip_data or not isinstance(clip_data, dict):
                return False, "clip_data dictionary is required", None
            clip_id = clip_data.get("clip_id", "")
            if not clip_id:
                clip_id = _new_id(clip_data.get("name", "imported"), "clip")
            if clip_id in self._clips:
                return False, f"Clip already exists: {clip_id}", None
            if len(self._clips) >= self._config.max_clips:
                return False, "Maximum clip capacity reached", None
            # Build the sample data from the preview if available.
            sample_data = clip_data.get("sample_data_preview", [])
            if not isinstance(sample_data, list):
                sample_data = []
            clip = AudioClip(
                clip_id=clip_id,
                name=clip_data.get("name", clip_id),
                audio_type=self._validate_audio_type(
                    clip_data.get("audio_type", AudioType.SFX.value)),
                format=self._validate_format(
                    clip_data.get("format", AudioFormat.MONO.value)),
                sample_rate=_safe_int(clip_data.get("sample_rate", 44100),
                                      44100),
                channels=_safe_int(clip_data.get("channels", 1), 1),
                duration=_safe_float(clip_data.get("duration", 1.0), 1.0),
                sample_data=[_safe_float(s, 0.0) for s in sample_data],
                loop_mode=self._validate_loop_mode(
                    clip_data.get("loop_mode", AudioLoopMode.ONE_SHOT.value)),
                priority=self._validate_priority(
                    clip_data.get("priority", AudioPriority.NORMAL.value)),
                metadata=dict(clip_data.get("metadata", {})),
            )
            self._clips[clip_id] = clip
            self._emit(AudioEventKind.CREATED.value,
                       f"Clip imported: {clip.name}",
                       data={"clip_id": clip_id,
                             "sample_count": len(clip.sample_data)})
            self._update_stats()
            return True, f"Clip imported: {clip_id}", clip

    def fade_source(self, source_id: str = "",
                    fade_in: float = 0.0,
                    fade_out: float = 0.0
                    ) -> Tuple[bool, str, AudioSource]:
        """Set the fade-in and fade-out durations on an existing source."""
        with self._lock:
            source = self._sources.get(source_id)
            if source is None:
                return False, f"Source not found: {source_id}", \
                    AudioSource(source_id=source_id)
            old_fade_in = source.fade_in
            old_fade_out = source.fade_out
            source.fade_in = max(0.0, _safe_float(fade_in, 0.0))
            source.fade_out = max(0.0, _safe_float(fade_out, 0.0))
            self._emit(AudioEventKind.VOLUME_CHANGED.value,
                       f"Source fades set: {source_id} "
                       f"in={old_fade_in:.3f}->{source.fade_in:.3f} "
                       f"out={old_fade_out:.3f}->{source.fade_out:.3f}",
                       source_id=source_id,
                       data={"source_id": source_id,
                             "old_fade_in": old_fade_in,
                             "old_fade_out": old_fade_out,
                             "new_fade_in": source.fade_in,
                             "new_fade_out": source.fade_out})
            return True, f"Source fades set (in={source.fade_in}, out={source.fade_out})", source

    def get_music_track_layers(self, track_id: str = ""
                               ) -> Tuple[bool, str, List[MusicLayer]]:
        """Return all layers belonging to a music track."""
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, f"Track not found: {track_id}", []
            return True, f"Track has {len(track.layers)} layers", list(track.layers)

    def get_sources_on_bus(self, bus_id: str = "") -> List[AudioSource]:
        """Return all audio sources routed to the given bus."""
        with self._lock:
            return [s for s in self._sources.values() if s.bus_id == bus_id]

    def get_emitter_sources(self, emitter_id: str = "") -> List[AudioSource]:
        """Return all audio sources bound to the given emitter."""
        with self._lock:
            return [s for s in self._sources.values()
                    if s.emitter_id == emitter_id]

    def set_emitter_priority(self, emitter_id: str = "",
                             priority: str = AudioPriority.NORMAL.value
                             ) -> Tuple[bool, str, AudioEmitter]:
        """Change the playback priority of an audio emitter."""
        with self._lock:
            emitter = self._emitters.get(emitter_id)
            if emitter is None:
                return False, f"Emitter not found: {emitter_id}", \
                    AudioEmitter(emitter_id=emitter_id)
            old_prio = emitter.priority
            emitter.priority = self._validate_priority(priority)
            self._emit(AudioEventKind.CREATED.value,
                       f"Emitter priority set: {emitter.name} "
                       f"{old_prio}->{emitter.priority}",
                       source_id=emitter_id,
                       data={"emitter_id": emitter_id,
                             "old": old_prio, "new": emitter.priority})
            return True, f"Emitter priority set to {emitter.priority}", emitter

    def count_buses_by_channel(self) -> Dict[str, int]:
        """Return a count of buses grouped by their channel."""
        with self._lock:
            counts: Dict[str, int] = {}
            for ch in AudioBusChannel:
                counts[ch.value] = 0
            for bus in self._buses.values():
                counts[bus.channel] = counts.get(bus.channel, 0) + 1
            return counts

    def get_listener_reverb_mix(self, listener_id: str = ""
                                ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compute the reverb wet/dry mix for a listener position.

        Finds the active reverb zone for the listener and returns the
        interpolated wet and dry levels based on the listener's distance
        from the zone center.
        """
        with self._lock:
            listener = self._listeners.get(listener_id)
            if listener is None:
                if self._listeners:
                    listener = next(iter(self._listeners.values()))
                else:
                    return False, f"Listener not found: {listener_id}", {}
            if not self._reverb_zones:
                return True, "No reverb zones registered", {
                    "listener_id": listener_id,
                    "zone_id": "",
                    "wet_level": 0.0,
                    "dry_level": 1.0,
                    "room_size": 0.0,
                    "damping": 0.0,
                    "blend": 0.0,
                }

            # Find the zone that contains the listener.
            best_zone = None
            best_blend = 0.0
            for zone in self._reverb_zones.values():
                dist = math.sqrt(
                    listener.position[0] ** 2 +
                    listener.position[1] ** 2 +
                    listener.position[2] ** 2
                )
                if zone.min_distance <= dist <= zone.max_distance:
                    span = zone.max_distance - zone.min_distance
                    if span > 0:
                        # Blend increases as the listener moves toward the
                        # center of the zone.
                        center = (zone.min_distance + zone.max_distance) / 2.0
                        blend = 1.0 - abs(dist - center) / (span / 2.0)
                        blend = _clamp(blend, 0.0, 1.0)
                    else:
                        blend = 1.0
                    if blend > best_blend:
                        best_blend = blend
                        best_zone = zone

            if best_zone is None:
                best_zone = next(iter(self._reverb_zones.values()))
                best_blend = 0.0

            # Interpolate wet/dry levels based on the blend factor.
            wet = best_zone.wet_level * best_blend
            dry = best_zone.dry_level * (1.0 - best_blend) + \
                (1.0 - best_blend)

            result = {
                "listener_id": listener_id,
                "zone_id": best_zone.zone_id,
                "zone_name": best_zone.name,
                "reverb_preset": best_zone.reverb_preset,
                "wet_level": round(wet, 6),
                "dry_level": round(dry, 6),
                "room_size": best_zone.room_size,
                "damping": best_zone.damping,
                "blend": round(best_blend, 6),
            }
            return True, f"Reverb mix for listener {listener_id}", result

    # ------------------------------------------------------------------
    # AI / Procedural Audio
    # ------------------------------------------------------------------

    def auto_generate_sfx(self, description: str = "",
                          duration: float = 1.0,
                          audio_type: str = AudioType.SFX.value
                          ) -> Tuple[bool, str, Optional[AudioClip]]:
        """Generate a procedural sound effect from a text description.

        The description is parsed for keywords that map to a waveform
        type and a base frequency. For example, "explosion" maps to a
        noise waveform with a low frequency, "laser" maps to a saw
        waveform with a high frequency, and "ui click" maps to a short
        sine blip. The synthesized samples are stored in a new clip.
        """
        with self._lock:
            if not description:
                return False, "description is required", None
            desc_lower = (description or "").lower()
            dur = _clamp(_safe_float(duration, 1.0),
                         _DURATION_MIN, _DURATION_MAX)

            # Keyword to waveform and frequency mapping table.
            keyword_map = [
                ("explosion", WaveformType.NOISE.value, 80.0, 0.9),
                ("boom", WaveformType.NOISE.value, 60.0, 0.9),
                ("blast", WaveformType.NOISE.value, 100.0, 0.85),
                ("laser", WaveformType.SAW.value, 880.0, 0.6),
                ("beam", WaveformType.SAW.value, 660.0, 0.55),
                ("zap", WaveformType.SQUARE.value, 1200.0, 0.5),
                ("footstep", WaveformType.NOISE.value, 200.0, 0.4),
                ("step", WaveformType.NOISE.value, 220.0, 0.35),
                ("walk", WaveformType.NOISE.value, 200.0, 0.3),
                ("sword", WaveformType.TRIANGLE.value, 400.0, 0.5),
                ("swing", WaveformType.TRIANGLE.value, 350.0, 0.45),
                ("slash", WaveformType.SAW.value, 500.0, 0.5),
                ("click", WaveformType.SINE.value, 1000.0, 0.4),
                ("blip", WaveformType.SINE.value, 1200.0, 0.35),
                ("beep", WaveformType.SINE.value, 800.0, 0.4),
                ("wind", WaveformType.NOISE.value, 150.0, 0.3),
                ("rain", WaveformType.NOISE.value, 300.0, 0.25),
                ("thunder", WaveformType.NOISE.value, 50.0, 0.95),
                ("magic", WaveformType.PULSE.value, 440.0, 0.5),
                ("spell", WaveformType.PULSE.value, 520.0, 0.5),
                ("spark", WaveformType.SQUARE.value, 2000.0, 0.4),
                ("fire", WaveformType.NOISE.value, 180.0, 0.35),
                ("water", WaveformType.SINE.value, 250.0, 0.3),
                ("engine", WaveformType.SAW.value, 120.0, 0.6),
                ("motor", WaveformType.SAW.value, 100.0, 0.55),
                ("door", WaveformType.NOISE.value, 160.0, 0.4),
                ("glass", WaveformType.NOISE.value, 2500.0, 0.5),
                ("metal", WaveformType.SQUARE.value, 600.0, 0.45),
                ("wood", WaveformType.NOISE.value, 280.0, 0.4),
                ("stone", WaveformType.NOISE.value, 140.0, 0.45),
                ("coin", WaveformType.SINE.value, 1800.0, 0.4),
                ("pickup", WaveformType.SINE.value, 1500.0, 0.4),
                ("alarm", WaveformType.SQUARE.value, 700.0, 0.5),
                ("siren", WaveformType.SINE.value, 500.0, 0.5),
                ("voice", WaveformType.SINE.value, 200.0, 0.3),
                ("whisper", WaveformType.NOISE.value, 180.0, 0.2),
            ]

            waveform = WaveformType.SINE.value
            frequency = 440.0
            amplitude = 0.5
            matched = False
            for keyword, wf, freq, amp in keyword_map:
                if keyword in desc_lower:
                    waveform = wf
                    frequency = freq
                    amplitude = amp
                    matched = True
                    break

            # If no keyword matched, derive a frequency from the hash of
            # the description so each description yields a stable tone.
            if not matched:
                desc_hash = hashlib.md5(description.encode("utf-8")).hexdigest()
                freq_val = int(desc_hash[:4], 16) % 1760 + 80
                frequency = float(freq_val)
                amplitude = 0.4

            # Adjust duration based on keywords that imply short sounds.
            if any(kw in desc_lower for kw in ("click", "blip", "beep", "coin", "pickup")):
                dur = min(dur, 0.15)
            if any(kw in desc_lower for kw in ("explosion", "boom", "thunder")):
                dur = max(dur, 1.5)

            sample_rate = self._config.sample_rate
            samples = _generate_waveform(waveform, frequency, dur,
                                         sample_rate, amplitude)

            clip_id = _new_id(description, "clip")
            clip_name = description[:60] if description else "Generated SFX"
            clip = AudioClip(
                clip_id=clip_id,
                name=clip_name,
                audio_type=self._validate_audio_type(audio_type),
                format=AudioFormat.MONO.value,
                sample_rate=sample_rate,
                channels=1,
                duration=dur,
                sample_data=samples,
                loop_mode=AudioLoopMode.ONE_SHOT.value,
                priority=AudioPriority.NORMAL.value,
                metadata={
                    "generated": True,
                    "description": description,
                    "waveform": waveform,
                    "frequency": frequency,
                    "amplitude": amplitude,
                    "keyword_matched": matched,
                },
            )
            self._clips[clip_id] = clip
            self._emit(AudioEventKind.EFFECT_GENERATED.value,
                       f"Auto-generated SFX: {clip_name}",
                       data={"clip_id": clip_id, "waveform": waveform,
                             "frequency": frequency, "duration": dur})
            self._update_stats()
            return True, f"Auto-generated SFX: {clip_id}", clip

    def generate_procedural_clip(self, clip_id: str = "", name: str = "",
                                 waveform: str = WaveformType.SINE.value,
                                 frequency: float = 440.0,
                                 duration: float = 1.0,
                                 sample_rate: int = 44100,
                                 amplitude: float = 0.5,
                                 metadata: Optional[Dict[str, Any]] = None
                                 ) -> Tuple[bool, str, Optional[AudioClip]]:
        """Generate a clip from a deterministic waveform synthesis."""
        with self._lock:
            if not clip_id:
                clip_id = _new_id(name or "proc", "clip")
            if clip_id in self._clips:
                return False, f"Clip already exists: {clip_id}", None
            if len(self._clips) >= self._config.max_clips:
                return False, "Maximum clip capacity reached", None
            wf = self._validate_waveform(waveform)
            freq = _clamp(_safe_float(frequency, 440.0),
                          _FREQUENCY_MIN, _FREQUENCY_MAX)
            dur = _clamp(_safe_float(duration, 1.0),
                         _DURATION_MIN, _DURATION_MAX)
            sr = int(_clamp(_safe_int(sample_rate, 44100),
                            _SAMPLE_RATE_MIN, _SAMPLE_RATE_MAX))
            amp = _clamp(_safe_float(amplitude, 0.5),
                         _AMPLITUDE_MIN, _AMPLITUDE_MAX)
            samples = _generate_waveform(wf, freq, dur, sr, amp)
            clip = AudioClip(
                clip_id=clip_id,
                name=name or clip_id,
                audio_type=AudioType.SFX.value,
                format=AudioFormat.MONO.value,
                sample_rate=sr,
                channels=1,
                duration=dur,
                sample_data=samples,
                loop_mode=AudioLoopMode.ONE_SHOT.value,
                priority=AudioPriority.NORMAL.value,
                metadata={
                    "generated": True,
                    "waveform": wf,
                    "frequency": freq,
                    "amplitude": amp,
                    **(dict(metadata) if metadata else {}),
                },
            )
            self._clips[clip_id] = clip
            self._emit(AudioEventKind.EFFECT_GENERATED.value,
                       f"Procedural clip generated: {clip.name}",
                       data={"clip_id": clip_id, "waveform": wf,
                             "frequency": freq, "duration": dur})
            self._update_stats()
            return True, f"Procedural clip generated: {clip_id}", clip

    def suggest_music_layer(self, track_id: str = "",
                            mood: str = ""
                            ) -> Tuple[bool, str, Optional[MusicLayer]]:
        """Suggest which music layer to activate based on a mood string.

        The mood is matched against layer conditions and metadata to find
        the best fit. When no exact match is found, the layer whose
        condition or metadata is closest to the mood is returned.
        """
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False, f"Track not found: {track_id}", None
            if not track.layers:
                return False, f"Track has no layers: {track_id}", None
            mood_lower = (mood or "").lower().strip()
            if not mood_lower:
                # Return the current layer when no mood is given.
                for layer in track.layers:
                    if layer.layer_id == track.current_layer:
                        return True, "Suggested current layer", layer
                return True, "Suggested first layer", track.layers[0]

            # Score each layer by how well it matches the mood.
            best_layer = None
            best_score = -1
            mood_terms = set(mood_lower.replace(",", " ").split())
            for layer in track.layers:
                score = 0
                cond = (layer.condition or "").lower()
                layer_name = (layer.name or "").lower()
                meta_str = " ".join(
                    str(v).lower() for v in layer.metadata.values()
                )
                combined = f"{cond} {layer_name} {meta_str}"
                for term in mood_terms:
                    if term in cond:
                        score += 3
                    if term in layer_name:
                        score += 2
                    if term in combined:
                        score += 1
                # Bonus for layers that are already active.
                if layer.active:
                    score += 1
                if score > best_score:
                    best_score = score
                    best_layer = layer

            if best_layer is None:
                best_layer = track.layers[0]
            return True, f"Suggested layer for mood '{mood}': {best_layer.layer_id}", best_layer

    def optimize_mix(self, bus_id: str = ""
                     ) -> Tuple[bool, str, List[str]]:
        """Analyze a bus and return a list of mix optimization suggestions."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False, f"Bus not found: {bus_id}", []
            suggestions: List[str] = []

            # Volume checks.
            if bus.volume > 1.0:
                suggestions.append(
                    f"Bus '{bus.name}' volume ({bus.volume:.2f}) exceeds "
                    f"1.0; consider lowering to avoid clipping."
                )
            if bus.volume < 0.1:
                suggestions.append(
                    f"Bus '{bus.name}' volume ({bus.volume:.2f}) is very "
                    f"low; consider raising or muting to free a channel."
                )

            # Mute and solo checks.
            if bus.muted:
                suggestions.append(
                    f"Bus '{bus.name}' is muted; remove effects from its "
                    f"chain to save CPU."
                )
            if bus.solo:
                suggestions.append(
                    f"Bus '{bus.name}' is soloed; all other buses are "
                    f"silenced. Verify this is intended."
                )

            # Effect chain checks.
            chain = bus.effects_chain
            if len(chain) > 4:
                suggestions.append(
                    f"Bus '{bus.name}' has {len(chain)} effects in its "
                    f"chain; consider reducing to 4 or fewer for lower latency."
                )
            disabled_effects = []
            for fx_id in chain:
                fx = self._effects.get(fx_id)
                if fx is not None and not fx.enabled:
                    disabled_effects.append(fx_id)
            if disabled_effects:
                suggestions.append(
                    f"Bus '{bus.name}' has disabled effects "
                    f"({', '.join(disabled_effects)}); remove them from "
                    f"the chain to clean up the signal path."
                )
            # Check for duplicate effect types.
            type_counts: Dict[str, int] = {}
            for fx_id in chain:
                fx = self._effects.get(fx_id)
                if fx is not None:
                    type_counts[fx.effect_type] = type_counts.get(fx.effect_type, 0) + 1
            for etype, count in type_counts.items():
                if count > 1:
                    suggestions.append(
                        f"Bus '{bus.name}' has {count} '{etype}' effects; "
                        f"consider consolidating into one."
                    )

            # Source count checks.
            source_count = sum(
                1 for s in self._sources.values()
                if s.bus_id == bus_id
            )
            active_count = sum(
                1 for s in self._sources.values()
                if s.bus_id == bus_id
                and s.status == AudioStatus.PLAYING.value
            )
            if active_count > 32:
                suggestions.append(
                    f"Bus '{bus.name}' has {active_count} active sources; "
                    f"consider using priority-based voice stealing to "
                    f"reduce simultaneous playback."
                )
            if source_count > 0 and active_count == 0:
                suggestions.append(
                    f"Bus '{bus.name}' has {source_count} sources but none "
                    f"are playing; consider removing idle sources."
                )

            # Volume distribution across sources.
            if active_count > 0:
                volumes = [
                    s.volume for s in self._sources.values()
                    if s.bus_id == bus_id
                    and s.status == AudioStatus.PLAYING.value
                ]
                avg_vol = sum(volumes) / len(volumes) if volumes else 0.0
                max_vol = max(volumes) if volumes else 0.0
                if max_vol > 1.0:
                    suggestions.append(
                        f"Bus '{bus.name}' has a source peaking at "
                        f"{max_vol:.2f}; apply a limiter to prevent clipping."
                    )
                if avg_vol > 0.8 and active_count > 8:
                    suggestions.append(
                        f"Bus '{bus.name}' has {active_count} sources "
                        f"averaging {avg_vol:.2f} volume; the summed level "
                        f"may clip. Lower individual source volumes."
                    )

            if not suggestions:
                suggestions.append(
                    f"Bus '{bus.name}' mix looks balanced; no changes needed."
                )

            self._emit(AudioEventKind.CREATED.value,
                       f"Mix optimized for bus: {bus.name}",
                       data={"bus_id": bus_id,
                             "suggestion_count": len(suggestions)})
            return True, f"Generated {len(suggestions)} suggestions", suggestions

    def analyze_audio_spectrum(self, clip_id: str = ""
                               ) -> Tuple[bool, str, Dict[str, Any]]:
        """Perform a frequency-domain analysis of an audio clip.

        Returns a dictionary with peak frequency, RMS level, spectral
        centroid, zero-crossing rate, and band energies. When the clip
        has no sample data, the analysis is based on its declared
        duration and sample rate.
        """
        with self._lock:
            clip = self._clips.get(clip_id)
            if clip is None:
                return False, f"Clip not found: {clip_id}", {}
            samples = clip.sample_data
            n = len(samples)
            result: Dict[str, Any] = {
                "clip_id": clip.clip_id,
                "name": clip.name,
                "sample_rate": clip.sample_rate,
                "channels": clip.channels,
                "duration": clip.duration,
                "sample_count": n,
            }

            if n == 0:
                # No sample data available; return a minimal analysis.
                result.update({
                    "peak_frequency": 0.0,
                    "rms_level": 0.0,
                    "peak_level": 0.0,
                    "spectral_centroid": 0.0,
                    "zero_crossing_rate": 0.0,
                    "band_energies": {},
                    "note": "No sample data; clip is a catalog entry only.",
                })
                self._emit(AudioEventKind.CREATED.value,
                           f"Spectrum analyzed (no data): {clip.name}",
                           data={"clip_id": clip_id})
                return True, "Spectrum analyzed (no sample data)", result

            # Time-domain metrics.
            peak_level = max(abs(s) for s in samples)
            rms_level = math.sqrt(sum(s * s for s in samples) / float(n))

            # Zero-crossing rate.
            crossings = 0
            for i in range(1, n):
                if (samples[i - 1] >= 0.0) != (samples[i] >= 0.0):
                    crossings += 1
            zcr = float(crossings) / float(n) * float(clip.sample_rate)

            # Frequency-domain analysis via a simple DFT on a downsampled
            # window to keep computation bounded for large clips.
            window_size = min(n, 1024)
            # Take a window from the middle of the clip for a stable view.
            start = max(0, (n - window_size) // 2)
            window = samples[start:start + window_size]
            wlen = len(window)

            # Apply a Hann window to reduce spectral leakage.
            hann = [
                0.5 - 0.5 * math.cos(2.0 * math.pi * i / max(1, wlen - 1))
                for i in range(wlen)
            ]
            windowed = [window[i] * hann[i] for i in range(wlen)]

            # Compute magnitude spectrum for the first half of bins.
            half = wlen // 2
            magnitudes: List[float] = []
            for k in range(half):
                real = 0.0
                imag = 0.0
                for t in range(wlen):
                    angle = -2.0 * math.pi * k * t / float(wlen)
                    real += windowed[t] * math.cos(angle)
                    imag += windowed[t] * math.sin(angle)
                mag = math.sqrt(real * real + imag * imag) / float(wlen)
                magnitudes.append(mag)

            # Peak frequency.
            peak_bin = 0
            peak_mag = 0.0
            for k, mag in enumerate(magnitudes):
                if mag > peak_mag:
                    peak_mag = mag
                    peak_bin = k
            bin_freq = float(clip.sample_rate) / float(wlen)
            peak_frequency = peak_bin * bin_freq

            # Spectral centroid.
            weighted_sum = 0.0
            mag_sum = 0.0
            for k, mag in enumerate(magnitudes):
                freq = k * bin_freq
                weighted_sum += freq * mag
                mag_sum += mag
            spectral_centroid = weighted_sum / mag_sum if mag_sum > 0 else 0.0

            # Band energies (low, mid, high).
            band_defs = [
                ("sub_bass", 20.0, 60.0),
                ("bass", 60.0, 250.0),
                ("low_mid", 250.0, 500.0),
                ("mid", 500.0, 2000.0),
                ("high_mid", 2000.0, 4000.0),
                ("high", 4000.0, 8000.0),
                ("air", 8000.0, 20000.0),
            ]
            band_energies: Dict[str, float] = {}
            for bname, lo, hi in band_defs:
                energy = 0.0
                count = 0
                for k, mag in enumerate(magnitudes):
                    freq = k * bin_freq
                    if lo <= freq < hi:
                        energy += mag * mag
                        count += 1
                band_energies[bname] = round(energy / max(1, count), 6)

            result.update({
                "peak_frequency": round(peak_frequency, 2),
                "rms_level": round(rms_level, 6),
                "peak_level": round(peak_level, 6),
                "spectral_centroid": round(spectral_centroid, 2),
                "zero_crossing_rate": round(zcr, 2),
                "band_energies": band_energies,
                "window_size": wlen,
                "analysis_bins": half,
            })

            self._emit(AudioEventKind.CREATED.value,
                       f"Spectrum analyzed: {clip.name}",
                       data={"clip_id": clip_id,
                             "peak_frequency": peak_frequency,
                             "rms_level": rms_level})
            return True, f"Spectrum analyzed: {clip_id}", result

    # ------------------------------------------------------------------
    # System Lifecycle and Observability
    # ------------------------------------------------------------------

    def get_config(self) -> AudioConfig:
        """Return the current audio configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, AudioConfig]:
        """Update one or more audio configuration fields."""
        with self._lock:
            changed: List[str] = []
            for key, value in kwargs.items():
                if not hasattr(self._config, key):
                    continue
                if key == "max_buses":
                    value = max(1, _safe_int(value, self._config.max_buses))
                elif key == "max_emitters":
                    value = max(1, _safe_int(value, self._config.max_emitters))
                elif key == "max_sources":
                    value = max(1, _safe_int(value, self._config.max_sources))
                elif key == "max_clips":
                    value = max(1, _safe_int(value, self._config.max_clips))
                elif key == "max_tracks":
                    value = max(1, _safe_int(value, self._config.max_tracks))
                elif key == "max_effects":
                    value = max(1, _safe_int(value, self._config.max_effects))
                elif key == "master_volume":
                    value = _clamp(_safe_float(value, self._config.master_volume),
                                   _VOLUME_MIN, _VOLUME_MAX)
                elif key == "sample_rate":
                    value = int(_clamp(_safe_int(value, self._config.sample_rate),
                                       _SAMPLE_RATE_MIN, _SAMPLE_RATE_MAX))
                elif key == "buffer_size":
                    value = int(_clamp(_safe_int(value, self._config.buffer_size),
                                       _BUFFER_SIZE_MIN, _BUFFER_SIZE_MAX))
                elif key == "spatial_audio_enabled":
                    value = bool(value)
                elif key == "doppler_factor":
                    value = _clamp(_safe_float(value, self._config.doppler_factor),
                                   _DOPPLER_MIN, _DOPPLER_MAX)
                elif key == "speed_of_sound":
                    value = _clamp(_safe_float(value, self._config.speed_of_sound),
                                   _SPEED_OF_SOUND_MIN, _SPEED_OF_SOUND_MAX)
                old_val = getattr(self._config, key)
                setattr(self._config, key, value)
                changed.append(f"{key}: {old_val}->{value}")
            if changed:
                self._emit(AudioEventKind.VOLUME_CHANGED.value,
                           f"Config updated: {', '.join(changed)}",
                           data={"changes": changed})
            return True, f"Config updated ({len(changed)} fields)", self._config

    def get_stats(self) -> AudioStats:
        """Return the live statistics as an AudioStats dataclass."""
        with self._lock:
            self._update_stats()
            return self._stats

    def get_snapshot(self) -> AudioSnapshot:
        """Return a lightweight point-in-time snapshot of system state."""
        with self._lock:
            self._update_stats()
            return AudioSnapshot(
                initialized=self._initialized,
                tick_count=self._tick_count,
                active_sources=self._stats.active_sources,
                active_tracks=self._stats.active_tracks,
                master_volume=self._config.master_volume,
                bus_count=len(self._buses),
                emitter_count=len(self._emitters),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a dictionary describing the overall system status."""
        with self._lock:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "tick_count": self._tick_count,
                "total_buses": len(self._buses),
                "total_emitters": len(self._emitters),
                "total_listeners": len(self._listeners),
                "total_clips": len(self._clips),
                "total_sources": len(self._sources),
                "total_tracks": len(self._tracks),
                "total_layers": len(self._layers),
                "total_effects": len(self._effects),
                "total_reverb_zones": len(self._reverb_zones),
                "active_sources": self._stats.active_sources,
                "active_tracks": self._stats.active_tracks,
                "total_played": self._total_played,
                "master_volume": self._config.master_volume,
                "sample_rate": self._config.sample_rate,
                "spatial_audio_enabled": self._config.spatial_audio_enabled,
                "soloed_buses": list(self._soloed_buses),
                "event_count": len(self._events),
            }

    def list_events(self, limit: int = 100,
                    kind: str = ""
                    ) -> List[AudioEvent]:
        """List audit events, optionally filtered by event kind."""
        with self._lock:
            results = list(self._events)
            if kind:
                results = [e for e in results if e.kind == kind]
            if limit > 0:
                cap = _clamp(_safe_int(limit, _DEFAULT_LIST_LIMIT),
                             1, _MAX_LIST_LIMIT)
                results = results[-cap:]
            return results

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the audio simulation by ``dt`` seconds.

        For each playing source the play position advances by ``dt``,
        fade-in and fade-out envelopes are applied, and sources that
        reach the end of their clip are stopped (one-shot) or looped.
        Active source and track counts are refreshed at the end.
        """
        with self._lock:
            self._tick_count += 1
            dt_sec = _safe_float(dt, 1.0)
            if dt_sec < 0.0:
                dt_sec = 0.0

            sources_advanced = 0
            sources_stopped = 0
            sources_looped = 0
            fades_applied = 0

            for source in self._sources.values():
                if source.status != AudioStatus.PLAYING.value:
                    continue

                clip = self._clips.get(source.clip_id) if source.clip_id else None
                clip_duration = clip.duration if clip else 0.0

                # Advance the play position.
                pitch = source.pitch if source.pitch > 0 else 1.0
                source.play_position += dt_sec * pitch
                sources_advanced += 1

                # Apply fade-in envelope.
                if source.fade_in > 0.0 and source.play_position < source.fade_in:
                    fade_ratio = source.play_position / source.fade_in
                    # The effective volume is scaled by the fade ratio.
                    # We store the base volume in metadata to restore it.
                    if "base_volume" not in source.metadata:
                        source.metadata["base_volume"] = source.volume
                    base_vol = source.metadata.get("base_volume", source.volume)
                    source.volume = _clamp(base_vol * fade_ratio,
                                           _VOLUME_MIN, _VOLUME_MAX)
                    fades_applied += 1
                elif source.fade_in > 0.0 and source.play_position >= source.fade_in:
                    # Fade-in complete; restore base volume.
                    if "base_volume" in source.metadata:
                        source.volume = source.metadata["base_volume"]
                        source.metadata.pop("fade_in_active", None)

                # Apply fade-out envelope near the end of the clip.
                if (source.fade_out > 0.0 and clip_duration > 0.0
                        and source.play_position >= clip_duration - source.fade_out):
                    remaining = clip_duration - source.play_position
                    if remaining > 0:
                        fade_ratio = remaining / source.fade_out
                        if "base_volume" not in source.metadata:
                            source.metadata["base_volume"] = source.volume
                        base_vol = source.metadata.get("base_volume", source.volume)
                        source.volume = _clamp(base_vol * fade_ratio,
                                               _VOLUME_MIN, _VOLUME_MAX)
                        fades_applied += 1

                # Handle end-of-clip behavior.
                if clip_duration > 0.0 and source.play_position >= clip_duration:
                    mode = source.loop_mode
                    if mode == AudioLoopMode.LOOP.value:
                        source.play_position = source.play_position % clip_duration
                        sources_looped += 1
                    elif mode == AudioLoopMode.LOOP_WITH_FADE.value:
                        # Loop back and reset the fade-in.
                        source.play_position = source.play_position % clip_duration
                        if source.fade_in > 0.0:
                            source.metadata["base_volume"] = source.volume
                        sources_looped += 1
                    else:
                        # One-shot: stop the source.
                        source.status = AudioStatus.STOPPED.value
                        source.play_position = 0.0
                        sources_stopped += 1
                        # Restore base volume if it was modified by fades.
                        if "base_volume" in source.metadata:
                            source.volume = source.metadata["base_volume"]
                            del source.metadata["base_volume"]

            # Periodically emit a tick event for observability.
            if self._tick_count % 60 == 0:
                self._emit(AudioEventKind.CREATED.value,
                           f"Tick checkpoint: {self._tick_count}",
                           data={"tick_count": self._tick_count,
                                 "dt": dt_sec,
                                 "sources_advanced": sources_advanced,
                                 "sources_stopped": sources_stopped,
                                 "sources_looped": sources_looped,
                                 "fades_applied": fades_applied})

            self._update_stats()
            return {
                "tick_count": self._tick_count,
                "dt": dt_sec,
                "sources_advanced": sources_advanced,
                "sources_stopped": sources_stopped,
                "sources_looped": sources_looped,
                "fades_applied": fades_applied,
                "active_sources": self._stats.active_sources,
                "active_tracks": self._stats.active_tracks,
            }

    def reset(self) -> Tuple[bool, str]:
        """Clear all stores and re-seed the system with default data."""
        with self._lock:
            self._buses.clear()
            self._emitters.clear()
            self._listeners.clear()
            self._clips.clear()
            self._sources.clear()
            self._tracks.clear()
            self._layers.clear()
            self._effects.clear()
            self._reverb_zones.clear()
            self._events.clear()
            self._stats = AudioStats()
            self._config = AudioConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._source_counter = 0
            self._total_played = 0
            self._soloed_buses = []
            self._initialized = False
            self._initialize()
            self._emit(AudioEventKind.CREATED.value,
                       "System reset and re-seeded",
                       data={"tick_count": self._tick_count})
            self._update_stats()
            return True, "System reset complete"


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_audio_sfx_system() -> AudioSfxSystem:
    """Return the singleton AudioSfxSystem instance."""
    return AudioSfxSystem.get_instance()
