"""
ProceduralAudio - Runtime procedural audio synthesis system.

Generates sound effects algorithmically for footsteps, impacts, ambiance,
and UI sounds without requiring pre-recorded audio files. Provides sound
preset management, layer-based mixing, and environment-aware ambience
generation for the SparkLabs game engine.
"""

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


class SoundCategory(Enum):
    """Broad classification of procedurally generated sound types."""

    IMPACT = "impact"
    FOOTSTEP = "footstep"
    AMBIENCE = "ambience"
    UI_CLICK = "ui_click"
    COLLECTIBLE = "collectible"
    EXPLOSION = "explosion"
    WHOOSH = "whoosh"
    MAGIC = "magic"
    MECHANICAL = "mechanical"
    WATER = "water"

    @property
    def default_frequency(self) -> float:
        """Returns the default base frequency in Hz for this sound category."""
        return {
            SoundCategory.IMPACT: 120.0,
            SoundCategory.FOOTSTEP: 200.0,
            SoundCategory.AMBIENCE: 80.0,
            SoundCategory.UI_CLICK: 800.0,
            SoundCategory.COLLECTIBLE: 600.0,
            SoundCategory.EXPLOSION: 60.0,
            SoundCategory.WHOOSH: 300.0,
            SoundCategory.MAGIC: 440.0,
            SoundCategory.MECHANICAL: 250.0,
            SoundCategory.WATER: 150.0,
        }[self]

    @property
    def default_duration(self) -> float:
        """Returns the default duration in seconds for this sound category."""
        return {
            SoundCategory.IMPACT: 0.3,
            SoundCategory.FOOTSTEP: 0.15,
            SoundCategory.AMBIENCE: 5.0,
            SoundCategory.UI_CLICK: 0.05,
            SoundCategory.COLLECTIBLE: 0.4,
            SoundCategory.EXPLOSION: 2.0,
            SoundCategory.WHOOSH: 0.5,
            SoundCategory.MAGIC: 1.0,
            SoundCategory.MECHANICAL: 0.6,
            SoundCategory.WATER: 2.0,
        }[self]


class WaveformType(Enum):
    """Oscillator waveform shapes used for procedural sound generation."""

    SINE = "sine"
    SQUARE = "square"
    TRIANGLE = "triangle"
    SAWTOOTH = "sawtooth"
    NOISE = "noise"
    PULSE = "pulse"
    CUSTOM = "custom"

    @property
    def harmonic_profile(self) -> List[Tuple[float, float]]:
        """Returns default harmonic multipliers and amplitudes for this waveform.

        Each entry is a (frequency_multiplier, amplitude) pair. Sine has
        no harmonics, while square and sawtooth have rich harmonic series.
        """
        profiles = {
            WaveformType.SINE: [(1.0, 1.0)],
            WaveformType.SQUARE: [
                (1.0, 1.0), (3.0, 0.333), (5.0, 0.2), (7.0, 0.143)
            ],
            WaveformType.TRIANGLE: [
                (1.0, 1.0), (3.0, 0.111), (5.0, 0.04)
            ],
            WaveformType.SAWTOOTH: [
                (1.0, 1.0), (2.0, 0.5), (3.0, 0.333), (4.0, 0.25),
                (5.0, 0.2), (6.0, 0.167)
            ],
            WaveformType.NOISE: [(1.0, 1.0)],
            WaveformType.PULSE: [
                (1.0, 1.0), (2.0, 0.5), (3.0, 0.333)
            ],
            WaveformType.CUSTOM: [(1.0, 1.0)],
        }
        return profiles[self]


class SynthesisMethod(Enum):
    """Algorithmic approaches for generating procedural audio samples."""

    ADDITIVE = "additive"
    SUBTRACTIVE = "subtractive"
    FM = "fm"
    GRANULAR = "granular"
    PHYSICAL_MODEL = "physical_model"
    SAMPLE_BASED = "sample_based"

    @property
    def description(self) -> str:
        """Returns a human-readable summary of the synthesis technique."""
        return {
            SynthesisMethod.ADDITIVE: "Combines multiple sine waves at harmonic frequencies.",
            SynthesisMethod.SUBTRACTIVE: "Filters a harmonically rich source through a time-varying filter.",
            SynthesisMethod.FM: "Modulates one oscillator's frequency with another for complex timbres.",
            SynthesisMethod.GRANULAR: "Rearranges tiny audio grains for evolving textures.",
            SynthesisMethod.PHYSICAL_MODEL: "Simulates physical vibration using waveguide or modal synthesis.",
            SynthesisMethod.SAMPLE_BASED: "Applies procedural transformations to a base sample buffer.",
        }[self]


class AudioChannel(Enum):
    """Output channel configurations for synthesized audio."""

    MONO = "mono"
    STEREO = "stereo"
    SPATIAL_3D = "spatial_3d"
    AMBISONIC = "ambisonic"

    @property
    def channel_count(self) -> int:
        """Returns the number of audio channels for this configuration."""
        return {
            AudioChannel.MONO: 1,
            AudioChannel.STEREO: 2,
            AudioChannel.SPATIAL_3D: 2,
            AudioChannel.AMBISONIC: 4,
        }[self]


@dataclass
class SoundPreset:
    """Configurable template for generating a specific procedural sound.

    Stores all parameters needed to reproduce a sound: waveform selection,
    base frequency, harmonic series, ADSR envelope, and duration. Presets
    serve as the building blocks for the procedural audio pipeline.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: SoundCategory = SoundCategory.IMPACT
    base_frequency: float = 440.0
    harmonics: List[Tuple[float, float]] = field(default_factory=list)
    envelope: Dict[str, float] = field(default_factory=dict)
    waveform: WaveformType = WaveformType.SINE
    duration: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Initializes defaults for envelope and harmonics if not provided."""
        if not self.envelope:
            self.envelope = {
                "attack": 0.01,
                "decay": max(0.001, self.duration * 0.2),
                "sustain": 0.7,
                "release": max(0.01, self.duration * 0.3),
            }
        if not self.harmonics:
            self.harmonics = list(self.waveform.harmonic_profile)

    @property
    def env_attack(self) -> float:
        """Attack time in seconds."""
        return self.envelope.get("attack", 0.01)

    @property
    def env_decay(self) -> float:
        """Decay time in seconds."""
        return self.envelope.get("decay", 0.1)

    @property
    def env_sustain(self) -> float:
        """Sustain level as a ratio of peak amplitude."""
        return self.envelope.get("sustain", 0.7)

    @property
    def env_release(self) -> float:
        """Release time in seconds."""
        return self.envelope.get("release", 0.1)

    @property
    def harmonic_count(self) -> int:
        """Number of harmonic partials in this preset."""
        return len(self.harmonics)

    def to_dict(self) -> dict:
        """Serializes the sound preset to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "base_frequency": round(self.base_frequency, 1),
            "harmonic_count": self.harmonic_count,
            "harmonics": [
                [round(m, 2), round(a, 3)] for m, a in self.harmonics
            ],
            "envelope": {
                k: round(v, 4) for k, v in self.envelope.items()
            },
            "waveform": self.waveform.value,
            "duration": round(self.duration, 3),
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"SoundPreset(id={self.id[:8]}..., name={self.name}, "
            f"cat={self.category.value}, freq={self.base_frequency:.0f}Hz)"
        )


@dataclass
class SynthesisResult:
    """Describes the result of a procedural audio synthesis operation.

    Contains metadata about the synthesized audio: the originating preset,
    a textual description of the sample data, duration, sample rate, channel
    layout, and an estimated file size if the sample were serialized.
    """

    preset_id: str = ""
    sample_data: str = ""
    duration_seconds: float = 0.0
    sample_rate: int = 44100
    channel_count: int = 2
    file_size_estimate: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Computes file size estimate and validates output parameters."""
        if self.file_size_estimate <= 0 and self.duration_seconds > 0:
            bytes_per_sample = 2
            total_samples = (
                int(self.sample_rate * self.duration_seconds)
                * self.channel_count
            )
            self.file_size_estimate = total_samples * bytes_per_sample
        if self.channel_count < 1:
            self.channel_count = 2

    @property
    def total_samples(self) -> int:
        """Total number of sample frames across all channels."""
        return int(self.sample_rate * self.duration_seconds)

    @property
    def total_sample_frames(self) -> int:
        """Total sample count including all channels."""
        return self.total_samples * self.channel_count

    def to_dict(self) -> dict:
        """Serializes the synthesis result to a dictionary."""
        return {
            "preset_id": self.preset_id,
            "sample_data": self.sample_data[:200],
            "duration_seconds": round(self.duration_seconds, 3),
            "sample_rate": self.sample_rate,
            "channel_count": self.channel_count,
            "file_size_estimate": self.file_size_estimate,
            "total_samples": self.total_samples,
            "total_sample_frames": self.total_sample_frames,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"SynthesisResult(preset={self.preset_id[:8]}..., "
            f"dur={self.duration_seconds:.2f}s, "
            f"rate={self.sample_rate}Hz, "
            f"size={self.file_size_estimate}B)"
        )


@dataclass
class AudioLayer:
    """A mixable audio layer grouping multiple sound presets.

    Layers provide volume control, pitch shifting, spatial positioning,
    and looping behavior for a collection of presets. Multiple layers
    can be combined to create complex soundscapes.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    presets: List[str] = field(default_factory=list)
    volume: float = 1.0
    pitch_shift: float = 0.0
    spatial_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    is_looping: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Clamps volume and pitch shift to valid ranges."""
        self.volume = max(0.0, min(1.0, self.volume))
        self.pitch_shift = max(-24.0, min(24.0, self.pitch_shift))

    @property
    def preset_count(self) -> int:
        """Number of sound presets assigned to this layer."""
        return len(self.presets)

    def to_dict(self) -> dict:
        """Serializes the audio layer to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "preset_count": self.preset_count,
            "presets": list(self.presets),
            "volume": round(self.volume, 3),
            "pitch_shift": round(self.pitch_shift, 1),
            "spatial_position": [
                round(self.spatial_position[0], 2),
                round(self.spatial_position[1], 2),
                round(self.spatial_position[2], 2),
            ],
            "is_looping": self.is_looping,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"AudioLayer(id={self.id[:8]}..., name={self.name}, "
            f"presets={self.preset_count}, vol={self.volume:.2f})"
        )


class ProceduralAudio:
    """Singleton system for runtime procedural audio synthesis.

    Generates sound effects algorithmically using configurable synthesis
    methods. Manages sound presets, layered audio mixing, volume control,
    and environment-aware ambience generation. All audio is synthesized
    at runtime without pre-recorded files.

    Thread-safe via a reentrant lock. Use get_procedural_audio() or
    ProceduralAudio.get_instance() to obtain the singleton.
    """

    _instance: Optional["ProceduralAudio"] = None
    _lock: threading.RLock = threading.RLock()

    # Internal constants for synthesis estimation.
    _BYTES_PER_SAMPLE: int = 2
    _DEFAULT_SAMPLE_RATE: int = 44100
    _DEFAULT_CHANNELS: int = 2
    _MAX_HARMONICS: int = 32
    _MIN_FREQUENCY: float = 20.0
    _MAX_FREQUENCY: float = 20000.0

    def __new__(cls) -> "ProceduralAudio":
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
        if getattr(self, "_initialized", False):
            return
        self._sound_presets: Dict[str, SoundPreset] = {}
        self._audio_layers: Dict[str, AudioLayer] = {}
        self._master_volume: float = 1.0
        self._sample_rate: int = self._DEFAULT_SAMPLE_RATE
        self._stats: Dict[str, Any] = {
            "total_synthesis_operations": 0,
            "total_presets_created": 0,
            "total_layers_created": 0,
            "total_ambience_generations": 0,
            "total_play_requests": 0,
            "last_synthesis_time_ms": 0.0,
            "estimated_total_samples": 0,
            "estimated_total_bytes": 0,
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "ProceduralAudio":
        """Returns the singleton ProceduralAudio instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_frequency(self, frequency: float) -> float:
        """Clamps a frequency value to the valid audible range.

        Returns:
            The clamped frequency value between _MIN_FREQUENCY and _MAX_FREQUENCY.
        """
        return max(self._MIN_FREQUENCY, min(self._MAX_FREQUENCY, frequency))

    def _validate_duration(self, duration: float) -> float:
        """Clamps a duration value to a reasonable minimum.

        Returns:
            The clamped duration, never less than 0.001 seconds.
        """
        return max(0.001, duration)

    def _compute_adsr_amplitude(
        self,
        time_position: float,
        env: Dict[str, float],
    ) -> float:
        """Computes the ADSR envelope amplitude at a given time position.

        Args:
            time_position: Current time offset in seconds within the sound.
            env: Envelope dictionary with attack, decay, sustain, release keys.

        Returns:
            Amplitude value between 0.0 and 1.0.
        """
        attack = env.get("attack", 0.01)
        decay = env.get("decay", 0.1)
        sustain = env.get("sustain", 0.7)
        release = env.get("release", 0.1)

        attack_end = attack
        decay_end = attack + decay
        sustain_end = self._validate_duration(
            env.get("_total_duration", 1.0)
        ) - release
        total_end = sustain_end + release

        if time_position <= 0.0:
            return 0.0

        if time_position <= attack_end:
            return time_position / max(0.001, attack_end)

        if time_position <= decay_end:
            decay_t = (time_position - attack_end) / max(0.001, decay)
            return 1.0 - (1.0 - sustain) * decay_t

        if time_position <= sustain_end:
            return sustain

        if time_position <= total_end:
            release_t = (time_position - sustain_end) / max(0.001, release)
            return sustain * (1.0 - release_t)

        return 0.0

    def _estimate_sample_count(
        self,
        duration_seconds: float,
        channel_count: int,
    ) -> int:
        """Estimates total sample count for a given duration and channel count.

        Returns:
            Total number of sample frames across all channels.
        """
        samples_per_channel = int(self._sample_rate * duration_seconds)
        return samples_per_channel * channel_count

    def _estimate_file_size(
        self,
        duration_seconds: float,
        channel_count: int,
    ) -> int:
        """Estimates raw PCM file size in bytes for the given parameters.

        Uses 16-bit integer samples. Does not include header overhead.

        Returns:
            Estimated file size in bytes.
        """
        total_frames = self._estimate_sample_count(duration_seconds, channel_count)
        return total_frames * self._BYTES_PER_SAMPLE

    def _generate_playback_id(self) -> str:
        """Generates a unique playback identifier for a sound play request.

        Returns:
            A hex string ID prefixed with 'playback_'.
        """
        return f"playback_{uuid.uuid4().hex[:12]}"

    def _describe_sample_data(
        self,
        preset: SoundPreset,
        method: SynthesisMethod,
        modifiers: Optional[Dict[str, Any]],
    ) -> str:
        """Produces a textual description of the synthesized sample data.

        Since actual audio sample generation is platform-dependent, this
        method creates a human-readable description of the waveform that
        would be produced, useful for debugging and logging.

        Returns:
            A string describing the synthesized audio characteristics.
        """
        mod_info = ""
        if modifiers:
            parts = []
            for key, val in modifiers.items():
                parts.append(f"{key}={val}")
            mod_info = ", modifiers: " + ", ".join(parts)

        return (
            f"{method.value} synthesis: {preset.waveform.value} wave at "
            f"{preset.base_frequency:.0f}Hz, {preset.harmonic_count} harmonics, "
            f"duration={preset.duration:.3f}s, category={preset.category.value}"
            f"{mod_info}"
        )

    def _resolve_synthesis_method(
        self,
        waveform: WaveformType,
    ) -> SynthesisMethod:
        """Selects the most appropriate synthesis method for a waveform type.

        Returns:
            A SynthesisMethod suited to the given waveform.
        """
        mapping = {
            WaveformType.SINE: SynthesisMethod.ADDITIVE,
            WaveformType.SQUARE: SynthesisMethod.SUBTRACTIVE,
            WaveformType.TRIANGLE: SynthesisMethod.ADDITIVE,
            WaveformType.SAWTOOTH: SynthesisMethod.SUBTRACTIVE,
            WaveformType.NOISE: SynthesisMethod.GRANULAR,
            WaveformType.PULSE: SynthesisMethod.SUBTRACTIVE,
            WaveformType.CUSTOM: SynthesisMethod.SAMPLE_BASED,
        }
        return mapping.get(waveform, SynthesisMethod.ADDITIVE)

    def _default_envelope_for_category(
        self,
        category: SoundCategory,
    ) -> Dict[str, float]:
        """Returns a default ADSR envelope suited to a sound category.

        Impact sounds have fast attack and long release. Ambience has slow
        attack and long sustain. UI sounds are short and crisp.
        """
        defaults = {
            SoundCategory.IMPACT: {
                "attack": 0.002, "decay": 0.08, "sustain": 0.3, "release": 0.3
            },
            SoundCategory.FOOTSTEP: {
                "attack": 0.001, "decay": 0.03, "sustain": 0.2, "release": 0.1
            },
            SoundCategory.AMBIENCE: {
                "attack": 1.0, "decay": 0.5, "sustain": 0.8, "release": 2.0
            },
            SoundCategory.UI_CLICK: {
                "attack": 0.001, "decay": 0.01, "sustain": 0.1, "release": 0.02
            },
            SoundCategory.COLLECTIBLE: {
                "attack": 0.005, "decay": 0.05, "sustain": 0.5, "release": 0.3
            },
            SoundCategory.EXPLOSION: {
                "attack": 0.01, "decay": 0.3, "sustain": 0.5, "release": 1.5
            },
            SoundCategory.WHOOSH: {
                "attack": 0.05, "decay": 0.1, "sustain": 0.4, "release": 0.3
            },
            SoundCategory.MAGIC: {
                "attack": 0.1, "decay": 0.2, "sustain": 0.6, "release": 0.8
            },
            SoundCategory.MECHANICAL: {
                "attack": 0.002, "decay": 0.1, "sustain": 0.5, "release": 0.3
            },
            SoundCategory.WATER: {
                "attack": 0.3, "decay": 0.4, "sustain": 0.6, "release": 1.0
            },
        }
        return dict(defaults.get(category, defaults[SoundCategory.IMPACT]))

    # ------------------------------------------------------------------
    # Public API: Preset management
    # ------------------------------------------------------------------

    def create_preset(
        self,
        name: str,
        category: SoundCategory,
        base_frequency: float,
        waveform: WaveformType,
    ) -> SoundPreset:
        """Creates a new sound preset with the specified parameters.

        Generates a preset with default envelope and harmonics appropriate
        for the category and waveform type. The preset is registered in the
        internal catalog for later synthesis.

        Args:
            name: Human-readable name for the preset.
            category: The sound category this preset belongs to.
            base_frequency: Fundamental frequency in Hz.
            waveform: The oscillator waveform shape.

        Returns:
            The newly created SoundPreset instance.

        Raises:
            ValueError: If base_frequency is outside the audible range.
        """
        valid_freq = self._validate_frequency(base_frequency)
        if valid_freq != base_frequency:
            raise ValueError(
                f"base_frequency must be between {self._MIN_FREQUENCY} and "
                f"{self._MAX_FREQUENCY} Hz, got {base_frequency}"
            )

        env = self._default_envelope_for_category(category)
        duration = category.default_duration

        preset = SoundPreset(
            name=name,
            category=category,
            base_frequency=valid_freq,
            harmonics=list(waveform.harmonic_profile),
            envelope=env,
            waveform=waveform,
            duration=duration,
        )

        with self._lock:
            self._sound_presets[preset.id] = preset
            self._stats["total_presets_created"] += 1

        return preset

    def get_preset(self, preset_id: str) -> Optional[SoundPreset]:
        """Retrieves a sound preset by its unique ID.

        Args:
            preset_id: The preset's unique identifier.

        Returns:
            The SoundPreset if found, None otherwise.
        """
        with self._lock:
            return self._sound_presets.get(preset_id)

    def list_presets(
        self,
        category: Optional[SoundCategory] = None,
    ) -> List[SoundPreset]:
        """Lists all sound presets, optionally filtered by category.

        Args:
            category: If provided, only presets of this category are returned.

        Returns:
            A list of SoundPreset objects.
        """
        with self._lock:
            presets = list(self._sound_presets.values())
            if category is not None:
                presets = [p for p in presets if p.category == category]
            return presets

    def remove_preset(self, preset_id: str) -> bool:
        """Removes a sound preset and cleans up layer references.

        Args:
            preset_id: The preset's unique identifier.

        Returns:
            True if the preset was found and removed, False otherwise.
        """
        with self._lock:
            if preset_id not in self._sound_presets:
                return False
            del self._sound_presets[preset_id]

            for layer in self._audio_layers.values():
                if preset_id in layer.presets:
                    layer.presets.remove(preset_id)

            return True

    # ------------------------------------------------------------------
    # Public API: Synthesis
    # ------------------------------------------------------------------

    def synthesize(
        self,
        preset_id: str,
        modifiers: Optional[Dict[str, Any]] = None,
    ) -> SynthesisResult:
        """Synthesizes audio from a sound preset with optional modifiers.

        Produces a SynthesisResult describing the generated audio. The
        synthesis method is automatically selected based on the preset's
        waveform type. Modifiers can adjust frequency, duration, envelope,
        or harmonics at synthesis time.

        Args:
            preset_id: The ID of the sound preset to synthesize.
            modifiers: Optional dict of synthesis overrides. Supported keys
                include 'frequency_multiplier', 'duration_scale',
                'envelope_override', 'harmonic_filter'.

        Returns:
            A SynthesisResult describing the generated audio.

        Raises:
            ValueError: If the preset_id does not exist.
        """
        with self._lock:
            preset = self._sound_presets.get(preset_id)
            if preset is None:
                raise ValueError(f"Sound preset not found: {preset_id}")

            synthesis_start = _time_module.perf_counter()

            freq_mod = 1.0
            dur_mod = 1.0
            if modifiers:
                freq_mod = float(modifiers.get("frequency_multiplier", 1.0))
                dur_mod = float(modifiers.get("duration_scale", 1.0))

            effective_freq = self._validate_frequency(
                preset.base_frequency * freq_mod
            )
            effective_duration = self._validate_duration(
                preset.duration * dur_mod
            )

            method = self._resolve_synthesis_method(preset.waveform)
            description = self._describe_sample_data(preset, method, modifiers)

            # Determine channel count based on preset category.
            channel_count = self._DEFAULT_CHANNELS
            if preset.category == SoundCategory.AMBIENCE:
                channel_count = AudioChannel.STEREO.channel_count

            file_size = self._estimate_file_size(effective_duration, channel_count)

            synthesis_end = _time_module.perf_counter()
            synthesis_time_ms = (synthesis_end - synthesis_start) * 1000.0

            result = SynthesisResult(
                preset_id=preset_id,
                sample_data=description,
                duration_seconds=effective_duration,
                sample_rate=self._sample_rate,
                channel_count=channel_count,
                file_size_estimate=file_size,
            )

            self._stats["total_synthesis_operations"] += 1
            self._stats["last_synthesis_time_ms"] = round(synthesis_time_ms, 3)
            self._stats["estimated_total_samples"] += result.total_sample_frames
            self._stats["estimated_total_bytes"] += file_size

            return result

    # ------------------------------------------------------------------
    # Public API: Playback
    # ------------------------------------------------------------------

    def play_sound(
        self,
        category: SoundCategory,
        position: Tuple[float, float, float],
        volume: float,
    ) -> str:
        """Requests playback of a sound by category at a 3D position.

        Finds the best matching preset for the category or synthesizes one
        on demand. Returns a playback ID for tracking the sound instance.

        Args:
            category: The sound category to play.
            position: 3D world position as (x, y, z).
            volume: Playback volume between 0.0 and 1.0.

        Returns:
            A unique playback ID string for tracking this sound instance.
        """
        effective_volume = max(0.0, min(1.0, volume)) * self._master_volume
        playback_id = self._generate_playback_id()

        with self._lock:
            matching_presets = [
                p for p in self._sound_presets.values()
                if p.category == category
            ]

            if matching_presets:
                preset = matching_presets[0]
                preset_id = preset.id
            else:
                # Auto-create a fallback preset for the requested category.
                fallback = self.create_preset(
                    name=f"auto_{category.value}",
                    category=category,
                    base_frequency=category.default_frequency,
                    waveform=WaveformType.SINE,
                )
                preset_id = fallback.id

            self._stats["total_play_requests"] += 1

        # Synthesize with volume and position modifiers.
        self.synthesize(
            preset_id,
            modifiers={
                "volume": effective_volume,
                "spatial_x": position[0],
                "spatial_y": position[1],
                "spatial_z": position[2],
            },
        )

        return playback_id

    def play_preset(
        self,
        preset_id: str,
        volume: float = 1.0,
    ) -> Optional[str]:
        """Requests playback of a specific sound preset.

        Args:
            preset_id: The preset to play.
            volume: Playback volume between 0.0 and 1.0.

        Returns:
            A playback ID if the preset exists, None otherwise.
        """
        with self._lock:
            if preset_id not in self._sound_presets:
                return None

        effective_volume = max(0.0, min(1.0, volume)) * self._master_volume
        playback_id = self._generate_playback_id()

        self.synthesize(
            preset_id,
            modifiers={"volume": effective_volume},
        )

        with self._lock:
            self._stats["total_play_requests"] += 1

        return playback_id

    # ------------------------------------------------------------------
    # Public API: Layer management
    # ------------------------------------------------------------------

    def create_layer(
        self,
        name: str,
        presets: List[str],
    ) -> AudioLayer:
        """Creates an audio layer grouping multiple sound presets.

        Layers provide coordinated volume, pitch, spatial positioning,
        and looping control over a collection of presets.

        Args:
            name: Human-readable name for the layer.
            presets: List of preset IDs to include. Invalid IDs are silently
                filtered out.

        Returns:
            The newly created AudioLayer instance.
        """
        with self._lock:
            valid_presets = [
                pid for pid in presets if pid in self._sound_presets
            ]
            layer = AudioLayer(
                name=name,
                presets=valid_presets,
            )
            self._audio_layers[layer.id] = layer
            self._stats["total_layers_created"] += 1
            return layer

    def get_layer(self, layer_id: str) -> Optional[AudioLayer]:
        """Retrieves an audio layer by its unique ID.

        Args:
            layer_id: The layer's unique identifier.

        Returns:
            The AudioLayer if found, None otherwise.
        """
        with self._lock:
            return self._audio_layers.get(layer_id)

    def list_layers(self) -> List[AudioLayer]:
        """Returns all registered audio layers.

        Returns:
            A list of all AudioLayer objects.
        """
        with self._lock:
            return list(self._audio_layers.values())

    def add_preset_to_layer(
        self,
        layer_id: str,
        preset_id: str,
    ) -> bool:
        """Adds a preset to an existing audio layer.

        Args:
            layer_id: The target layer's ID.
            preset_id: The preset ID to add.

        Returns:
            True if both the layer and preset exist and the preset was added,
            False otherwise.
        """
        with self._lock:
            layer = self._audio_layers.get(layer_id)
            if layer is None:
                return False
            if preset_id not in self._sound_presets:
                return False
            if preset_id not in layer.presets:
                layer.presets.append(preset_id)
            return True

    def remove_layer(self, layer_id: str) -> bool:
        """Removes an audio layer from the system.

        Args:
            layer_id: The layer's unique identifier.

        Returns:
            True if the layer was found and removed, False otherwise.
        """
        with self._lock:
            if layer_id not in self._audio_layers:
                return False
            del self._audio_layers[layer_id]
            return True

    def set_layer_volume(self, layer_id: str, volume: float) -> bool:
        """Sets the volume of a specific audio layer.

        Args:
            layer_id: The layer's unique identifier.
            volume: Volume between 0.0 and 1.0.

        Returns:
            True if the layer was found and updated, False otherwise.
        """
        with self._lock:
            layer = self._audio_layers.get(layer_id)
            if layer is None:
                return False
            layer.volume = max(0.0, min(1.0, volume))
            return True

    def set_layer_pitch(self, layer_id: str, semitones: float) -> bool:
        """Sets the pitch shift for a layer in semitones.

        Args:
            layer_id: The layer's unique identifier.
            semitones: Pitch shift in semitones, clamped to [-24, 24].

        Returns:
            True if the layer was found and updated, False otherwise.
        """
        with self._lock:
            layer = self._audio_layers.get(layer_id)
            if layer is None:
                return False
            layer.pitch_shift = max(-24.0, min(24.0, semitones))
            return True

    def set_layer_spatial_position(
        self,
        layer_id: str,
        x: float,
        y: float,
        z: float,
    ) -> bool:
        """Sets the 3D spatial position of an audio layer.

        Args:
            layer_id: The layer's unique identifier.
            x: X coordinate in world space.
            y: Y coordinate in world space.
            z: Z coordinate in world space.

        Returns:
            True if the layer was found and updated, False otherwise.
        """
        with self._lock:
            layer = self._audio_layers.get(layer_id)
            if layer is None:
                return False
            layer.spatial_position = (x, y, z)
            return True

    # ------------------------------------------------------------------
    # Public API: Volume control
    # ------------------------------------------------------------------

    def set_master_volume(self, volume: float) -> None:
        """Sets the global master volume for all procedural audio output.

        Args:
            volume: Master volume between 0.0 and 1.0. 0.0 is silent,
                1.0 is full volume.
        """
        with self._lock:
            self._master_volume = max(0.0, min(1.0, volume))

    def get_master_volume(self) -> float:
        """Returns the current master volume level.

        Returns:
            The master volume as a float between 0.0 and 1.0.
        """
        with self._lock:
            return self._master_volume

    def set_sample_rate(self, sample_rate: int) -> None:
        """Configures the output sample rate for future synthesis operations.

        Args:
            sample_rate: Target sample rate in Hz. Clamped to [8000, 192000].

        Raises:
            ValueError: If sample_rate is outside the valid range.
        """
        if sample_rate < 8000 or sample_rate > 192000:
            raise ValueError(
                f"Sample rate must be between 8000 and 192000 Hz, "
                f"got {sample_rate}"
            )
        with self._lock:
            self._sample_rate = sample_rate

    def get_sample_rate(self) -> int:
        """Returns the current output sample rate.

        Returns:
            The sample rate in Hz.
        """
        with self._lock:
            return self._sample_rate

    # ------------------------------------------------------------------
    # Public API: Ambience generation
    # ------------------------------------------------------------------

    def generate_ambience(
        self,
        environment_type: str,
        duration: float,
    ) -> SynthesisResult:
        """Generates ambient sound for a given environment type and duration.

        Creates or selects an appropriate ambience preset, then synthesizes
        it for the requested duration. Environment types map to different
        frequency profiles and harmonic structures.

        Args:
            environment_type: Descriptor for the environment, e.g. 'forest',
                'cave', 'ocean', 'city', 'space', 'desert'.
            duration: Desired ambience duration in seconds.

        Returns:
            A SynthesisResult describing the generated ambient audio.
        """
        environment_profiles: Dict[str, Dict[str, Any]] = {
            "forest": {
                "base_frequency": 120.0,
                "waveform": WaveformType.NOISE,
                "harmonics": [(1.0, 1.0), (1.5, 0.4), (2.3, 0.2)],
            },
            "cave": {
                "base_frequency": 55.0,
                "waveform": WaveformType.SINE,
                "harmonics": [(1.0, 1.0), (2.0, 0.3), (4.0, 0.15)],
            },
            "ocean": {
                "base_frequency": 80.0,
                "waveform": WaveformType.NOISE,
                "harmonics": [(1.0, 1.0), (1.3, 0.5), (1.8, 0.25)],
            },
            "city": {
                "base_frequency": 200.0,
                "waveform": WaveformType.NOISE,
                "harmonics": [(1.0, 1.0), (2.0, 0.6), (3.0, 0.3)],
            },
            "space": {
                "base_frequency": 40.0,
                "waveform": WaveformType.SINE,
                "harmonics": [(1.0, 1.0), (3.0, 0.2), (5.0, 0.1)],
            },
            "desert": {
                "base_frequency": 150.0,
                "waveform": WaveformType.NOISE,
                "harmonics": [(1.0, 1.0), (1.7, 0.35), (2.5, 0.15)],
            },
        }

        profile = environment_profiles.get(
            environment_type.lower(),
            environment_profiles["forest"],
        )

        # Check for an existing ambience preset matching this environment.
        ambience_preset_id: Optional[str] = None
        with self._lock:
            for preset in self._sound_presets.values():
                if (
                    preset.category == SoundCategory.AMBIENCE
                    and preset.name == f"ambience_{environment_type.lower()}"
                ):
                    ambience_preset_id = preset.id
                    break

        if ambience_preset_id is None:
            preset = self.create_preset(
                name=f"ambience_{environment_type.lower()}",
                category=SoundCategory.AMBIENCE,
                base_frequency=profile["base_frequency"],
                waveform=profile["waveform"],
            )
            preset.harmonics = list(profile["harmonics"])
            preset.duration = self._validate_duration(duration)
            ambience_preset_id = preset.id

        with self._lock:
            preset_for_check = self._sound_presets.get(ambience_preset_id)
            preset_duration = (
                preset_for_check.duration
                if preset_for_check else self._validate_duration(duration)
            )

        result = self.synthesize(
            ambience_preset_id,
            modifiers={
                "duration_scale": max(
                    1.0,
                    self._validate_duration(duration)
                    / max(0.001, preset_duration),
                ),
                "environment_type": environment_type,
            },
        )

        with self._lock:
            self._stats["total_ambience_generations"] += 1

        return result

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Returns a comprehensive statistics dictionary for monitoring.

        Includes preset and layer counts, synthesis operation totals,
        estimated resource usage, and category breakdowns.

        Returns:
            A dictionary with string keys and numeric/collection values.
        """
        with self._lock:
            category_counts: Dict[str, int] = {}
            for preset in self._sound_presets.values():
                cat = preset.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1

            waveform_counts: Dict[str, int] = {}
            for preset in self._sound_presets.values():
                wf = preset.waveform.value
                waveform_counts[wf] = waveform_counts.get(wf, 0) + 1

            total_envelope_durations = sum(
                p.duration for p in self._sound_presets.values()
            )
            avg_envelope_duration = 0.0
            if self._sound_presets:
                avg_envelope_duration = (
                    total_envelope_durations / len(self._sound_presets)
                )

            layers_with_looping = sum(
                1 for l in self._audio_layers.values() if l.is_looping
            )

            avg_presets_per_layer = 0.0
            if self._audio_layers:
                avg_presets_per_layer = sum(
                    l.preset_count for l in self._audio_layers.values()
                ) / len(self._audio_layers)

            return {
                "preset_count": len(self._sound_presets),
                "layer_count": len(self._audio_layers),
                "master_volume": round(self._master_volume, 3),
                "sample_rate": self._sample_rate,
                "total_synthesis_operations": self._stats[
                    "total_synthesis_operations"
                ],
                "total_presets_created": self._stats["total_presets_created"],
                "total_layers_created": self._stats["total_layers_created"],
                "total_ambience_generations": self._stats[
                    "total_ambience_generations"
                ],
                "total_play_requests": self._stats["total_play_requests"],
                "last_synthesis_time_ms": self._stats[
                    "last_synthesis_time_ms"
                ],
                "estimated_total_samples": self._stats[
                    "estimated_total_samples"
                ],
                "estimated_total_bytes": self._stats["estimated_total_bytes"],
                "category_distribution": category_counts,
                "waveform_distribution": waveform_counts,
                "avg_envelope_duration": round(avg_envelope_duration, 3),
                "layers_with_looping": layers_with_looping,
                "avg_presets_per_layer": round(avg_presets_per_layer, 2),
                "bytes_per_sample": self._BYTES_PER_SAMPLE,
                "max_harmonics": self._MAX_HARMONICS,
            }

    # ------------------------------------------------------------------
    # Public API: Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Performs a complete reset of all procedural audio state.

        Clears all presets, layers, and statistics. Master volume and
        sample rate are reset to their defaults.
        """
        with self._lock:
            self._sound_presets.clear()
            self._audio_layers.clear()
            self._master_volume = 1.0
            self._sample_rate = self._DEFAULT_SAMPLE_RATE
            self._stats = {
                "total_synthesis_operations": 0,
                "total_presets_created": 0,
                "total_layers_created": 0,
                "total_ambience_generations": 0,
                "total_play_requests": 0,
                "last_synthesis_time_ms": 0.0,
                "estimated_total_samples": 0,
                "estimated_total_bytes": 0,
            }

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"ProceduralAudio(presets={len(self._sound_presets)}, "
                f"layers={len(self._audio_layers)}, "
                f"vol={self._master_volume:.2f}, "
                f"rate={self._sample_rate}Hz)"
            )


def get_procedural_audio() -> ProceduralAudio:
    """Module-level accessor for the ProceduralAudio singleton.

    Convenience function that returns the singleton instance without
    needing to reference ProceduralAudio.get_instance() directly.

    Returns:
        The singleton ProceduralAudio instance.
    """
    return ProceduralAudio.get_instance()