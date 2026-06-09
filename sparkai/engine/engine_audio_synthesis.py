"""
SparkLabs Engine - Audio Synthesis

Procedural audio synthesis engine for the AI-native game engine.
Generates sound effects, ambient textures, and musical elements
programmatically through waveform synthesis, noise generation,
and real-time audio processing.

Architecture:
  EngineAudioSynthesis
    |-- OscillatorBank (multi-waveform tone generation)
    |-- NoiseGenerator (white/pink/brown/Perlin noise)
    |-- EnvelopeShaper (ADSR amplitude contouring)
    |-- FilterChain (lowpass/highpass/bandpass/notch filtering)
    |-- ModulationMatrix (LFO, FM, AM routing)
    |-- EffectProcessor (reverb, delay, chorus, distortion)
    |-- NoteSequencer (melodic/rhythmic pattern generation)
    |-- SampleBuffer (waveform data storage and manipulation)
"""

from __future__ import annotations

import math
import random
import struct
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WaveformType(str, Enum):
    """Supported oscillator waveforms."""
    SINE = "sine"
    SQUARE = "square"
    SAWTOOTH = "sawtooth"
    TRIANGLE = "triangle"
    NOISE = "noise"
    PULSE = "pulse"
    CUSTOM = "custom"


class NoiseColor(str, Enum):
    """Noise spectrum coloration."""
    WHITE = "white"
    PINK = "pink"
    BROWN = "brown"
    BLUE = "blue"
    VIOLET = "violet"
    PERLIN = "perlin"


class FilterType(str, Enum):
    """Audio filter types."""
    LOWPASS = "lowpass"
    HIGHPASS = "highpass"
    BANDPASS = "bandpass"
    NOTCH = "notch"
    ALLPASS = "allpass"
    PEAKING = "peaking"
    LOWSHELF = "lowshelf"
    HIGHSHELF = "highshelf"


class ModulationTarget(str, Enum):
    """Modulation destination parameters."""
    AMPLITUDE = "amplitude"
    FREQUENCY = "frequency"
    PHASE = "phase"
    FILTER_CUTOFF = "filter_cutoff"
    FILTER_RESONANCE = "filter_resonance"
    PAN = "pan"


class EffectType(str, Enum):
    """Audio effect processors."""
    REVERB = "reverb"
    DELAY = "delay"
    CHORUS = "chorus"
    DISTORTION = "distortion"
    FLANGER = "flanger"
    PHASER = "phaser"
    COMPRESSOR = "compressor"
    EQ = "eq"


class NoteName(str, Enum):
    """Musical note names with octave."""
    C = "C"
    CS = "C#"
    D = "D"
    DS = "D#"
    E = "E"
    F = "F"
    FS = "F#"
    G = "G"
    GS = "G#"
    A = "A"
    AS = "A#"
    B = "B"


class ScaleType(str, Enum):
    """Musical scale patterns."""
    MAJOR = "major"
    MINOR = "minor"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    CHROMATIC = "chromatic"
    BLUES = "blues"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OscillatorConfig:
    """Configuration for a single oscillator voice."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    waveform: WaveformType = WaveformType.SINE
    frequency: float = 440.0
    amplitude: float = 0.5
    phase_offset: float = 0.0
    pulse_width: float = 0.5
    detune_cents: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "waveform": self.waveform.value,
            "frequency": self.frequency,
            "amplitude": self.amplitude,
            "phase_offset": self.phase_offset,
            "pulse_width": self.pulse_width,
            "detune_cents": self.detune_cents,
            "enabled": self.enabled,
        }


@dataclass
class EnvelopeConfig:
    """ADSR envelope configuration."""
    attack_ms: float = 10.0
    decay_ms: float = 50.0
    sustain_level: float = 0.7
    release_ms: float = 200.0
    velocity_sensitivity: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_ms": self.attack_ms,
            "decay_ms": self.decay_ms,
            "sustain_level": self.sustain_level,
            "release_ms": self.release_ms,
            "velocity_sensitivity": self.velocity_sensitivity,
        }


@dataclass
class FilterConfig:
    """Audio filter configuration."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    filter_type: FilterType = FilterType.LOWPASS
    cutoff_hz: float = 1000.0
    resonance: float = 0.5
    gain_db: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filter_type": self.filter_type.value,
            "cutoff_hz": self.cutoff_hz,
            "resonance": self.resonance,
            "gain_db": self.gain_db,
            "enabled": self.enabled,
        }


@dataclass
class ModulationConfig:
    """Modulation routing configuration."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_id: str = ""
    target: ModulationTarget = ModulationTarget.AMPLITUDE
    depth: float = 0.5
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target": self.target.value,
            "depth": self.depth,
            "enabled": self.enabled,
        }


@dataclass
class EffectConfig:
    """Audio effect processor configuration."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    effect_type: EffectType = EffectType.REVERB
    mix: float = 0.3
    parameters: Dict[str, float] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "effect_type": self.effect_type.value,
            "mix": self.mix,
            "parameters": self.parameters,
            "enabled": self.enabled,
        }


@dataclass
class NoteEvent:
    """A single musical note event."""
    note: str = "C4"
    frequency: float = 261.63
    velocity: float = 0.8
    start_beat: float = 0.0
    duration_beats: float = 1.0
    channel: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "note": self.note,
            "frequency": self.frequency,
            "velocity": self.velocity,
            "start_beat": self.start_beat,
            "duration_beats": self.duration_beats,
            "channel": self.channel,
        }


@dataclass
class AudioSample:
    """Container for generated audio sample data."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sample_rate: int = 44100
    channels: int = 1
    bit_depth: int = 16
    duration_ms: float = 0.0
    data: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    @property
    def sample_count(self) -> int:
        return len(self.data)

    @property
    def duration_seconds(self) -> float:
        if self.sample_rate > 0:
            return self.sample_count / (self.sample_rate * self.channels)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "duration_ms": self.duration_ms,
            "sample_count": self.sample_count,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at,
        }

    def to_wav_bytes(self) -> bytes:
        """Convert sample data to WAV format bytes."""
        if not self.data:
            return b""

        max_val = 2 ** (self.bit_depth - 1) - 1
        samples = [int(max(0.0, min(1.0, s)) * max_val) for s in self.data]

        fmt = {
            8: "b",
            16: "h",
            24: "i",
            32: "i",
        }.get(self.bit_depth, "h")

        data_bytes = b"".join(
            struct.pack(f"<{fmt}", s) for s in samples
        )

        byte_rate = self.sample_rate * self.channels * self.bit_depth // 8
        block_align = self.channels * self.bit_depth // 8
        data_size = len(data_bytes)

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,
            self.channels,
            self.sample_rate,
            byte_rate,
            block_align,
            self.bit_depth,
            b"data",
            data_size,
        )

        return header + data_bytes


# ---------------------------------------------------------------------------
# Note Frequency Map
# ---------------------------------------------------------------------------

NOTE_FREQUENCIES: Dict[str, float] = {
    "C0": 16.35, "C#0": 17.32, "D0": 18.35, "D#0": 19.45, "E0": 20.60,
    "F0": 21.83, "F#0": 23.12, "G0": 24.50, "G#0": 25.96, "A0": 27.50,
    "A#0": 29.14, "B0": 30.87,
    "C1": 32.70, "C#1": 34.65, "D1": 36.71, "D#1": 38.89, "E1": 41.20,
    "F1": 43.65, "F#1": 46.25, "G1": 49.00, "G#1": 51.91, "A1": 55.00,
    "A#1": 58.27, "B1": 61.74,
    "C2": 65.41, "C#2": 69.30, "D2": 73.42, "D#2": 77.78, "E2": 82.41,
    "F2": 87.31, "F#2": 92.50, "G2": 98.00, "G#2": 103.83, "A2": 110.00,
    "A#2": 116.54, "B2": 123.47,
    "C3": 130.81, "C#3": 138.59, "D3": 146.83, "D#3": 155.56, "E3": 164.81,
    "F3": 174.61, "F#3": 185.00, "G3": 196.00, "G#3": 207.65, "A3": 220.00,
    "A#3": 233.08, "B3": 246.94,
    "C4": 261.63, "C#4": 277.18, "D4": 293.66, "D#4": 311.13, "E4": 329.63,
    "F4": 349.23, "F#4": 369.99, "G4": 392.00, "G#4": 415.30, "A4": 440.00,
    "A#4": 466.16, "B4": 493.88,
    "C5": 523.25, "C#5": 554.37, "D5": 587.33, "D#5": 622.25, "E5": 659.25,
    "F5": 698.46, "F#5": 739.99, "G5": 783.99, "G#5": 830.61, "A5": 880.00,
    "A#5": 932.33, "B5": 987.77,
    "C6": 1046.50, "C#6": 1108.73, "D6": 1174.66, "D#6": 1244.51, "E6": 1318.51,
    "F6": 1396.91, "F#6": 1479.98, "G6": 1567.98, "G#6": 1661.22, "A6": 1760.00,
    "A#6": 1864.66, "B6": 1975.53,
    "C7": 2093.00, "C#7": 2217.46, "D7": 2349.32, "D#7": 2489.02, "E7": 2637.02,
    "F7": 2793.83, "F#7": 2959.96, "G7": 3135.96, "G#7": 3322.44, "A7": 3520.00,
    "A#7": 3729.31, "B7": 3951.07,
    "C8": 4186.01,
}

SCALE_INTERVALS: Dict[ScaleType, List[int]] = {
    ScaleType.MAJOR: [0, 2, 4, 5, 7, 9, 11],
    ScaleType.MINOR: [0, 2, 3, 5, 7, 8, 10],
    ScaleType.PENTATONIC_MAJOR: [0, 2, 4, 7, 9],
    ScaleType.PENTATONIC_MINOR: [0, 3, 5, 7, 10],
    ScaleType.CHROMATIC: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    ScaleType.BLUES: [0, 3, 5, 6, 7, 10],
    ScaleType.DORIAN: [0, 2, 3, 5, 7, 9, 10],
    ScaleType.PHRYGIAN: [0, 1, 3, 5, 7, 8, 10],
    ScaleType.LYDIAN: [0, 2, 4, 6, 7, 9, 11],
    ScaleType.MIXOLYDIAN: [0, 2, 4, 5, 7, 9, 10],
}

SEMITONE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ---------------------------------------------------------------------------
# EngineAudioSynthesis
# ---------------------------------------------------------------------------

class EngineAudioSynthesis:
    """
    Procedural audio synthesis engine for the SparkLabs AI-native game engine.

    Generates audio content programmatically through waveform synthesis,
    noise generation, filtering, modulation, and effects processing.
    Supports sound effect synthesis, ambient texture generation, and
    musical pattern creation.
    """

    _instance: Optional["EngineAudioSynthesis"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineAudioSynthesis":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._oscillators: Dict[str, OscillatorConfig] = {}
        self._envelopes: Dict[str, EnvelopeConfig] = {}
        self._filters: Dict[str, FilterConfig] = {}
        self._modulations: Dict[str, ModulationConfig] = {}
        self._effects: Dict[str, EffectConfig] = {}
        self._samples: Dict[str, AudioSample] = {}
        self._sample_rate: int = 44100
        self._master_volume: float = 1.0
        self._generated_count: int = 0
        self._total_samples: int = 0

    # ------------------------------------------------------------------
    # Oscillator Management
    # ------------------------------------------------------------------

    def create_oscillator(
        self,
        waveform: str = "sine",
        frequency: float = 440.0,
        amplitude: float = 0.5,
        detune_cents: float = 0.0,
    ) -> OscillatorConfig:
        """Create a new oscillator voice."""
        osc = OscillatorConfig(
            waveform=WaveformType(waveform),
            frequency=frequency,
            amplitude=amplitude,
            detune_cents=detune_cents,
        )
        self._oscillators[osc.id] = osc
        return osc

    def remove_oscillator(self, oscillator_id: str) -> bool:
        """Remove an oscillator by ID."""
        if oscillator_id in self._oscillators:
            del self._oscillators[oscillator_id]
            return True
        return False

    def get_oscillator(self, oscillator_id: str) -> Optional[Dict[str, Any]]:
        """Get oscillator configuration."""
        osc = self._oscillators.get(oscillator_id)
        return osc.to_dict() if osc else None

    def list_oscillators(self) -> List[Dict[str, Any]]:
        """List all oscillator configurations."""
        return [o.to_dict() for o in self._oscillators.values()]

    # ------------------------------------------------------------------
    # Waveform Generation
    # ------------------------------------------------------------------

    def generate_waveform(
        self,
        waveform: str = "sine",
        frequency: float = 440.0,
        duration_ms: float = 1000.0,
        amplitude: float = 0.5,
        sample_rate: Optional[int] = None,
    ) -> List[float]:
        """Generate a single waveform sample buffer."""
        sr = sample_rate or self._sample_rate
        num_samples = int(sr * duration_ms / 1000.0)
        samples: List[float] = []

        wf = WaveformType(waveform)
        for i in range(num_samples):
            t = i / sr
            phase = (t * frequency) % 1.0

            if wf == WaveformType.SINE:
                value = math.sin(2.0 * math.pi * t * frequency)
            elif wf == WaveformType.SQUARE:
                value = 1.0 if phase < 0.5 else -1.0
            elif wf == WaveformType.SAWTOOTH:
                value = 2.0 * phase - 1.0
            elif wf == WaveformType.TRIANGLE:
                value = 4.0 * abs(phase - 0.5) - 1.0
            elif wf == WaveformType.PULSE:
                value = 1.0 if phase < 0.25 else -1.0
            elif wf == WaveformType.NOISE:
                value = random.uniform(-1.0, 1.0)
            else:
                value = math.sin(2.0 * math.pi * t * frequency)

            samples.append(value * amplitude)

        return samples

    # ------------------------------------------------------------------
    # Noise Generation
    # ------------------------------------------------------------------

    def generate_noise(
        self,
        color: str = "white",
        duration_ms: float = 1000.0,
        amplitude: float = 0.5,
        sample_rate: Optional[int] = None,
    ) -> List[float]:
        """Generate colored noise samples."""
        sr = sample_rate or self._sample_rate
        num_samples = int(sr * duration_ms / 1000.0)
        noise_color = NoiseColor(color)

        if noise_color == NoiseColor.WHITE:
            return [random.uniform(-amplitude, amplitude) for _ in range(num_samples)]

        if noise_color == NoiseColor.PERLIN:
            return self._generate_perlin_noise(num_samples, amplitude)

        white = [random.uniform(-amplitude, amplitude) for _ in range(num_samples)]

        if noise_color == NoiseColor.PINK:
            result = [0.0] * num_samples
            b = [0.0] * 7
            for i in range(num_samples):
                b[0] = white[i]
                for j in range(6):
                    b[j] = (b[j] + (b[j + 1] if j < 5 else 0.0)) * 0.5
                result[i] = sum(b[:5]) * 0.2
            return result

        if noise_color == NoiseColor.BROWN:
            result = [0.0] * num_samples
            for i in range(1, num_samples):
                result[i] = (result[i - 1] + white[i] * 0.02)
                result[i] = max(-amplitude, min(amplitude, result[i]))
            return result

        if noise_color == NoiseColor.BLUE:
            result = [0.0] * num_samples
            for i in range(1, num_samples):
                result[i] = white[i] - white[i - 1]
            return [max(-amplitude, min(amplitude, v)) for v in result]

        if noise_color == NoiseColor.VIOLET:
            result = [0.0] * num_samples
            for i in range(2, num_samples):
                result[i] = white[i] - 2.0 * white[i - 1] + white[i - 2]
            return [max(-amplitude, min(amplitude, v)) for v in result]

        return white

    def _generate_perlin_noise(self, num_samples: int, amplitude: float) -> List[float]:
        """Generate Perlin noise samples."""
        perm = [i for i in range(256)]
        random.shuffle(perm)
        perm = perm + perm

        def _fade(t: float) -> float:
            return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

        def _lerp(a: float, b: float, t: float) -> float:
            return a + t * (b - a)

        def _grad(hash_val: int, x: float, y: float) -> float:
            h = hash_val & 3
            u = x if h == 0 or h == 1 else y
            v = y if h == 0 or h == 1 else x
            return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

        result = []
        for i in range(num_samples):
            x = i * 0.01
            y = 0.0
            xi = int(x) & 255
            yi = int(y) & 255
            xf = x - int(x)
            yf = y - int(y)
            u = _fade(xf)
            v = _fade(yf)

            aa = perm[perm[xi] + yi]
            ab = perm[perm[xi] + yi + 1]
            ba = perm[perm[xi + 1] + yi]
            bb = perm[perm[xi + 1] + yi + 1]

            val = _lerp(
                _lerp(_grad(aa, xf, yf), _grad(ba, xf - 1, yf), u),
                _lerp(_grad(ab, xf, yf - 1), _grad(bb, xf - 1, yf - 1), u),
                v,
            )
            result.append(val * amplitude)

        return result

    # ------------------------------------------------------------------
    # Envelope Processing
    # ------------------------------------------------------------------

    def apply_envelope(
        self,
        samples: List[float],
        attack_ms: float = 10.0,
        decay_ms: float = 50.0,
        sustain_level: float = 0.7,
        release_ms: float = 200.0,
        sample_rate: Optional[int] = None,
    ) -> List[float]:
        """Apply ADSR envelope to a sample buffer."""
        sr = sample_rate or self._sample_rate
        num_samples = len(samples)
        attack_samples = int(sr * attack_ms / 1000.0)
        decay_samples = int(sr * decay_ms / 1000.0)
        release_samples = int(sr * release_ms / 1000.0)

        if attack_samples + decay_samples + release_samples > num_samples:
            attack_samples = max(1, num_samples // 4)
            decay_samples = max(1, num_samples // 4)
            release_samples = max(1, num_samples // 4)

        sustain_start = attack_samples + decay_samples
        sustain_end = num_samples - release_samples

        result = []
        for i, sample in enumerate(samples):
            if i < attack_samples:
                envelope = i / max(attack_samples, 1)
            elif i < sustain_start:
                envelope = 1.0 - (1.0 - sustain_level) * ((i - attack_samples) / max(decay_samples, 1))
            elif i < sustain_end:
                envelope = sustain_level
            else:
                envelope = sustain_level * (1.0 - (i - sustain_end) / max(release_samples, 1))

            result.append(sample * envelope)

        return result

    # ------------------------------------------------------------------
    # Filter Processing
    # ------------------------------------------------------------------

    def apply_filter(
        self,
        samples: List[float],
        filter_type: str = "lowpass",
        cutoff_hz: float = 1000.0,
        resonance: float = 0.5,
        sample_rate: Optional[int] = None,
    ) -> List[float]:
        """Apply a filter to a sample buffer."""
        sr = sample_rate or self._sample_rate
        ft = FilterType(filter_type)

        cutoff = min(cutoff_hz, sr / 2.0)
        w = 2.0 * math.pi * cutoff / sr
        alpha = math.sin(w) / (2.0 * resonance + 0.001)
        cos_w = math.cos(w)

        b0, b1, b2 = 0.0, 0.0, 0.0
        a0, a1, a2 = 0.0, 0.0, 0.0

        if ft == FilterType.LOWPASS:
            b0 = (1.0 - cos_w) / 2.0
            b1 = 1.0 - cos_w
            b2 = (1.0 - cos_w) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w
            a2 = 1.0 - alpha
        elif ft == FilterType.HIGHPASS:
            b0 = (1.0 + cos_w) / 2.0
            b1 = -(1.0 + cos_w)
            b2 = (1.0 + cos_w) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w
            a2 = 1.0 - alpha
        elif ft == FilterType.BANDPASS:
            b0 = alpha
            b1 = 0.0
            b2 = -alpha
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w
            a2 = 1.0 - alpha
        elif ft == FilterType.NOTCH:
            b0 = 1.0
            b1 = -2.0 * cos_w
            b2 = 1.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w
            a2 = 1.0 - alpha
        else:
            return list(samples)

        result = []
        x1, x2 = 0.0, 0.0
        y1, y2 = 0.0, 0.0

        for sample in samples:
            output = (b0 / a0) * sample + (b1 / a0) * x1 + (b2 / a0) * x2 - (a1 / a0) * y1 - (a2 / a0) * y2
            x2, x1 = x1, sample
            y2, y1 = y1, output
            result.append(output)

        return result

    # ------------------------------------------------------------------
    # Effect Processing
    # ------------------------------------------------------------------

    def apply_delay(
        self,
        samples: List[float],
        delay_ms: float = 300.0,
        feedback: float = 0.3,
        mix: float = 0.3,
        sample_rate: Optional[int] = None,
    ) -> List[float]:
        """Apply delay effect."""
        sr = sample_rate or self._sample_rate
        delay_samples = int(sr * delay_ms / 1000.0)
        delay_buffer = [0.0] * delay_samples
        write_pos = 0

        result = []
        for sample in samples:
            delayed = delay_buffer[write_pos % delay_samples]
            delay_buffer[write_pos % delay_samples] = sample + delayed * feedback
            write_pos += 1
            result.append(sample * (1.0 - mix) + delayed * mix)

        return result

    def apply_reverb(
        self,
        samples: List[float],
        room_size: float = 0.5,
        damping: float = 0.5,
        mix: float = 0.3,
        sample_rate: Optional[int] = None,
    ) -> List[float]:
        """Apply reverb effect using a simple Schroeder model."""
        sr = sample_rate or self._sample_rate
        comb_delays = [int(sr * d) for d in [0.0297, 0.0371, 0.0411, 0.0437]]
        comb_gains = [0.84, 0.84, 0.84, 0.84]
        allpass_delays = [int(sr * d) for d in [0.005, 0.0017]]
        allpass_gain = 0.5

        comb_buffers = [[0.0] * d for d in comb_delays]
        comb_positions = [0] * 4
        allpass_buffers = [[0.0] * d for d in allpass_delays]
        allpass_positions = [0] * 2

        result = []
        for sample in samples:
            wet = 0.0
            for i in range(4):
                cidx = comb_positions[i]
                wet += comb_buffers[i][cidx] * comb_gains[i] * (1.0 - damping)
                comb_buffers[i][cidx] = sample + wet * room_size * damping
                comb_positions[i] = (cidx + 1) % comb_delays[i]

            for i in range(2):
                aidx = allpass_positions[i]
                buf_val = allpass_buffers[i][aidx]
                allpass_buffers[i][aidx] = wet + buf_val * allpass_gain
                wet = buf_val - wet * allpass_gain
                allpass_positions[i] = (aidx + 1) % allpass_delays[i]

            result.append(sample * (1.0 - mix) + wet * mix)

        return result

    def apply_distortion(
        self,
        samples: List[float],
        drive: float = 0.5,
        mix: float = 0.5,
    ) -> List[float]:
        """Apply distortion effect."""
        result = []
        for sample in samples:
            driven = sample * (1.0 + drive * 10.0)
            wet = 2.0 / math.pi * math.atan(driven)
            result.append(sample * (1.0 - mix) + wet * mix)
        return result

    def apply_chorus(
        self,
        samples: List[float],
        rate: float = 0.5,
        depth_ms: float = 5.0,
        mix: float = 0.3,
        sample_rate: Optional[int] = None,
    ) -> List[float]:
        """Apply chorus effect."""
        sr = sample_rate or self._sample_rate
        max_delay = int(sr * depth_ms / 1000.0) + 1
        delay_buffer = [0.0] * max_delay
        write_pos = 0

        result = []
        for i, sample in enumerate(samples):
            lfo = math.sin(2.0 * math.pi * rate * i / sr)
            delay = int(max_delay * 0.5 + max_delay * 0.5 * lfo)
            delay = max(0, min(max_delay - 1, delay))
            read_pos = (write_pos - delay) % max_delay
            delayed = delay_buffer[read_pos]

            delay_buffer[write_pos % max_delay] = sample
            write_pos += 1

            result.append(sample * (1.0 - mix) + delayed * mix)

        return result

    # ------------------------------------------------------------------
    # Sound Effect Synthesis
    # ------------------------------------------------------------------

    def synthesize_laser(
        self,
        start_freq: float = 800.0,
        end_freq: float = 100.0,
        duration_ms: float = 300.0,
        amplitude: float = 0.6,
    ) -> AudioSample:
        """Synthesize a laser sound effect."""
        samples = self._sweep_frequency(start_freq, end_freq, duration_ms, WaveformType.SAWTOOTH, amplitude)
        samples = self.apply_filter(samples, "lowpass", 2000.0, 0.3)
        samples = self.apply_envelope(
            samples, attack_ms=5, decay_ms=50, sustain_level=0.3, release_ms=100
        )

        return self._create_sample(samples, duration_ms)

    def synthesize_explosion(
        self,
        duration_ms: float = 1000.0,
        amplitude: float = 0.8,
    ) -> AudioSample:
        """Synthesize an explosion sound effect."""
        noise = self.generate_noise("white", duration_ms, amplitude)
        noise = self.apply_filter(noise, "lowpass", 500.0, 0.4)
        noise = self.apply_envelope(
            noise, attack_ms=5, decay_ms=200, sustain_level=0.1, release_ms=500
        )

        sub = self.generate_waveform("sine", 40, duration_ms, amplitude * 0.5)
        sub = self.apply_envelope(sub, attack_ms=5, decay_ms=100, sustain_level=0.05, release_ms=500)

        combined = [n + s for n, s in zip(noise, sub)]
        return self._create_sample(combined, duration_ms)

    def synthesize_collect(
        self,
        frequency: float = 800.0,
        duration_ms: float = 200.0,
        amplitude: float = 0.5,
    ) -> AudioSample:
        """Synthesize a collect/pickup sound effect."""
        samples = self._sweep_frequency(
            frequency, frequency * 2.0, duration_ms, WaveformType.SINE, amplitude
        )
        samples = self.apply_envelope(
            samples, attack_ms=2, decay_ms=50, sustain_level=0.5, release_ms=100
        )
        return self._create_sample(samples, duration_ms)

    def synthesize_jump(
        self,
        start_freq: float = 300.0,
        end_freq: float = 600.0,
        duration_ms: float = 200.0,
        amplitude: float = 0.4,
    ) -> AudioSample:
        """Synthesize a jump sound effect."""
        samples = self._sweep_frequency(start_freq, end_freq, duration_ms, WaveformType.SQUARE, amplitude)
        samples = self.apply_filter(samples, "lowpass", 3000.0, 0.2)
        samples = self.apply_envelope(
            samples, attack_ms=5, decay_ms=50, sustain_level=0.3, release_ms=100
        )
        return self._create_sample(samples, duration_ms)

    def synthesize_hit(
        self,
        frequency: float = 200.0,
        duration_ms: float = 150.0,
        amplitude: float = 0.6,
    ) -> AudioSample:
        """Synthesize a hit/impact sound effect."""
        noise = self.generate_noise("white", duration_ms, amplitude * 0.7)
        noise = self.apply_filter(noise, "lowpass", 300.0, 0.5)

        tone = self.generate_waveform("sine", frequency, duration_ms, amplitude * 0.5)
        tone = self.apply_envelope(tone, attack_ms=1, decay_ms=30, sustain_level=0.1, release_ms=50)

        combined = [n + t for n, t in zip(noise, tone)]
        return self._create_sample(combined, duration_ms)

    def synthesize_powerup(
        self,
        duration_ms: float = 500.0,
        amplitude: float = 0.5,
    ) -> AudioSample:
        """Synthesize a powerup sound effect."""
        notes = [
            self._sweep_frequency(200, 400, 100, WaveformType.SINE, amplitude),
            self._sweep_frequency(400, 800, 150, WaveformType.SINE, amplitude),
            self._sweep_frequency(800, 1200, 250, WaveformType.SINE, amplitude),
        ]

        combined = []
        sample_count = max(len(n) for n in notes)
        for i in range(sample_count):
            total = 0.0
            for note in notes:
                if i < len(note):
                    total += note[i]
            combined.append(total)

        combined = self.apply_envelope(
            combined, attack_ms=10, decay_ms=100, sustain_level=0.6, release_ms=200
        )
        return self._create_sample(combined, duration_ms)

    def synthesize_ambient(
        self,
        duration_ms: float = 5000.0,
        base_freq: float = 200.0,
        amplitude: float = 0.3,
    ) -> AudioSample:
        """Synthesize an ambient drone texture."""
        samples = self.generate_noise("perlin", duration_ms, amplitude * 0.5)
        samples = self.apply_filter(samples, "lowpass", 400.0, 0.6)

        tone1 = self.generate_waveform("sine", base_freq, duration_ms, amplitude * 0.3)
        tone2 = self.generate_waveform("sine", base_freq * 1.5, duration_ms, amplitude * 0.2)
        tone3 = self.generate_waveform("triangle", base_freq * 0.5, duration_ms, amplitude * 0.15)

        combined = []
        for i in range(len(samples)):
            total = samples[i]
            if i < len(tone1):
                total += tone1[i]
            if i < len(tone2):
                total += tone2[i]
            if i < len(tone3):
                total += tone3[i]
            combined.append(total)

        combined = self.apply_reverb(combined, room_size=0.8, damping=0.3, mix=0.4)
        return self._create_sample(combined, duration_ms)

    def _sweep_frequency(
        self,
        start_freq: float,
        end_freq: float,
        duration_ms: float,
        waveform: WaveformType,
        amplitude: float,
    ) -> List[float]:
        """Generate a frequency sweep."""
        sr = self._sample_rate
        num_samples = int(sr * duration_ms / 1000.0)
        samples = []

        for i in range(num_samples):
            t = i / sr
            progress = i / max(num_samples - 1, 1)
            freq = start_freq + (end_freq - start_freq) * progress
            phase = (t * freq) % 1.0

            if waveform == WaveformType.SINE:
                value = math.sin(2.0 * math.pi * t * freq)
            elif waveform == WaveformType.SQUARE:
                value = 1.0 if phase < 0.5 else -1.0
            elif waveform == WaveformType.SAWTOOTH:
                value = 2.0 * phase - 1.0
            elif waveform == WaveformType.TRIANGLE:
                value = 4.0 * abs(phase - 0.5) - 1.0
            else:
                value = math.sin(2.0 * math.pi * t * freq)

            samples.append(value * amplitude)

        return samples

    def _create_sample(self, data: List[float], duration_ms: float) -> AudioSample:
        """Create and register an AudioSample."""
        sample = AudioSample(
            sample_rate=self._sample_rate,
            duration_ms=duration_ms,
            data=data,
        )
        self._samples[sample.id] = sample
        self._generated_count += 1
        self._total_samples += len(data)
        return sample

    # ------------------------------------------------------------------
    # Musical Note Generation
    # ------------------------------------------------------------------

    def get_scale_notes(
        self,
        root_note: str = "C4",
        scale_type: str = "major",
    ) -> List[Dict[str, Any]]:
        """Get all notes in a musical scale."""
        st = ScaleType(scale_type)
        intervals = SCALE_INTERVALS.get(st, SCALE_INTERVALS[ScaleType.MAJOR])

        root_idx = -1
        for i, name in enumerate(SEMITONE_NAMES):
            if f"{name}4" == root_note or name == root_note.replace("4", ""):
                root_idx = i
                break
        if root_idx < 0:
            root_idx = 0

        notes = []
        for interval in intervals:
            note_idx = (root_idx + interval) % 12
            note_name = f"{SEMITONE_NAMES[note_idx]}4"
            freq = NOTE_FREQUENCIES.get(note_name, 440.0)
            notes.append({
                "name": note_name,
                "frequency": freq,
                "interval": interval,
            })

        return notes

    def get_note_frequency(self, note_name: str) -> float:
        """Get frequency for a named note."""
        return NOTE_FREQUENCIES.get(note_name, 440.0)

    def generate_chord(
        self,
        root_note: str = "C4",
        chord_type: str = "major",
        duration_ms: float = 1000.0,
        amplitude: float = 0.4,
        waveform: str = "sine",
    ) -> AudioSample:
        """Generate a chord from multiple notes."""
        chord_intervals: Dict[str, List[int]] = {
            "major": [0, 4, 7],
            "minor": [0, 3, 7],
            "diminished": [0, 3, 6],
            "augmented": [0, 4, 8],
            "sus2": [0, 2, 7],
            "sus4": [0, 5, 7],
            "major7": [0, 4, 7, 11],
            "minor7": [0, 3, 7, 10],
            "dominant7": [0, 4, 7, 10],
        }

        intervals = chord_intervals.get(chord_type, chord_intervals["major"])
        root_freq = NOTE_FREQUENCIES.get(root_note, 261.63)

        all_samples: List[List[float]] = []
        for interval in intervals:
            freq = root_freq * (2.0 ** (interval / 12.0))
            wave = self.generate_waveform(waveform, freq, duration_ms, amplitude / len(intervals))
            all_samples.append(wave)

        combined = []
        max_len = max(len(w) for w in all_samples)
        for i in range(max_len):
            total = sum(w[i] if i < len(w) else 0.0 for w in all_samples)
            combined.append(total)

        combined = self.apply_envelope(
            combined, attack_ms=20, decay_ms=100, sustain_level=0.7, release_ms=300
        )
        return self._create_sample(combined, duration_ms)

    def generate_melody(
        self,
        scale_type: str = "major",
        root_note: str = "C4",
        note_count: int = 8,
        note_duration_ms: float = 250.0,
        amplitude: float = 0.4,
        waveform: str = "sine",
        seed: Optional[int] = None,
    ) -> AudioSample:
        """Generate a random melody from a scale."""
        if seed is not None:
            random.seed(seed)

        scale_notes = self.get_scale_notes(root_note, scale_type)
        all_samples: List[float] = []

        for i in range(note_count):
            note = random.choice(scale_notes)
            freq = note["frequency"]
            dur = note_duration_ms * random.uniform(0.5, 1.5)
            if i == 0:
                dur = note_duration_ms

            wave = self.generate_waveform(waveform, freq, dur, amplitude)
            env = self.apply_envelope(
                wave, attack_ms=5, decay_ms=30, sustain_level=0.6, release_ms=dur * 0.3
            )
            all_samples.extend(env)

        return self._create_sample(all_samples, note_count * note_duration_ms)

    def generate_rhythm_pattern(
        self,
        bpm: float = 120.0,
        beats: int = 8,
        hit_duration_ms: float = 50.0,
        amplitude: float = 0.5,
    ) -> AudioSample:
        """Generate a rhythmic percussion pattern."""
        beat_duration_ms = 60000.0 / bpm
        total_duration_ms = beat_duration_ms * beats

        all_samples: List[float] = []
        sr = self._sample_rate

        for beat in range(beats):
            beat_start_s = beat * beat_duration_ms / 1000.0
            beat_samples = int(sr * beat_duration_ms / 1000.0)

            if beat % 2 == 0:
                noise = self.generate_noise("white", hit_duration_ms, amplitude * 0.8, sr)
                noise = self.apply_filter(noise, "highpass", 500.0, 0.3)
                tone = self.generate_waveform("sine", 150, hit_duration_ms, amplitude * 0.3, sr)
                combined = [n + t for n, t in zip(noise, tone)]
                env = self.apply_envelope(combined, attack_ms=1, decay_ms=20, sustain_level=0.1, release_ms=hit_duration_ms * 0.5)
                all_samples.extend(env)
            else:
                noise = self.generate_noise("white", hit_duration_ms * 0.5, amplitude * 0.4, sr)
                noise = self.apply_filter(noise, "highpass", 800.0, 0.2)
                env = self.apply_envelope(noise, attack_ms=1, decay_ms=10, sustain_level=0.05, release_ms=hit_duration_ms * 0.3)
                all_samples.extend(env)

            silence = int(sr * beat_duration_ms / 1000.0) - len(env if beat % 2 == 0 else [])
            all_samples.extend([0.0] * max(0, silence))

        return self._create_sample(all_samples, total_duration_ms)

    # ------------------------------------------------------------------
    # Sample Management
    # ------------------------------------------------------------------

    def get_sample(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """Get a generated sample by ID."""
        sample = self._samples.get(sample_id)
        return sample.to_dict() if sample else None

    def list_samples(self) -> List[Dict[str, Any]]:
        """List all generated samples."""
        return [s.to_dict() for s in self._samples.values()]

    def get_sample_wav(self, sample_id: str) -> Optional[bytes]:
        """Get a sample as WAV bytes."""
        sample = self._samples.get(sample_id)
        return sample.to_wav_bytes() if sample else None

    def remove_sample(self, sample_id: str) -> bool:
        """Remove a generated sample."""
        if sample_id in self._samples:
            del self._samples[sample_id]
            return True
        return False

    def clear_samples(self) -> int:
        """Clear all generated samples."""
        count = len(self._samples)
        self._samples.clear()
        return count

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_sample_rate(self, sample_rate: int) -> None:
        """Set the global sample rate."""
        self._sample_rate = max(8000, min(192000, sample_rate))

    def set_master_volume(self, volume: float) -> None:
        """Set master volume level."""
        self._master_volume = max(0.0, min(1.0, volume))

    def get_stats(self) -> Dict[str, Any]:
        """Get synthesis engine statistics."""
        return {
            "sample_rate": self._sample_rate,
            "master_volume": self._master_volume,
            "generated_count": self._generated_count,
            "total_samples": self._total_samples,
            "stored_samples": len(self._samples),
            "oscillators": len(self._oscillators),
            "filters": len(self._filters),
            "effects": len(self._effects),
        }


# ---------------------------------------------------------------------------
# Global Accessor
# ---------------------------------------------------------------------------

def get_audio_synthesis() -> EngineAudioSynthesis:
    """Get the global EngineAudioSynthesis singleton."""
    return EngineAudioSynthesis()