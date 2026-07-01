"""
SparkLabs Engine - Character Appearance System

A complete character appearance engine providing facial animation,
lip synchronization, and hair/fur simulation for the AI-native game
engine. It fills the facial animation, lip sync, and hair/fur gaps
in the engine.

Architecture:
  CharacterAppearanceEngine (Singleton)
    |-- BlendShape          -- a single morph target (e.g. Smile, JawOpen)
    |-- BlendShapeGroup     -- a logical group of related blend shapes
    |-- ExpressionPreset    -- a named preset expression configuration
    |-- FacialRig           -- a character's complete facial rig
    |-- PhonemeMapping      -- maps phonemes to a viseme and shape weights
    |-- LipSyncTrack        -- a timed viseme sequence for spoken text
    |-- HairStrand          -- a single simulated hair strand
    |-- HairStyle           -- a character's full hair configuration
    |-- FurCoat             -- a character's fur coat configuration
    |-- WindConfig          -- global wind parameters
    |-- AppearanceStats     -- aggregate counts
    |-- AppearanceSnapshot  -- immutable engine state snapshot
    |-- AppearanceEvent     -- audit log entry

Facial Animation:
  Blend shapes are weighted morph targets (0.0 to 1.0). Expression
  presets bundle a set of weights for a given FacialExpression +
  EmotionIntensity. Expression blending interpolates between the
  current weights and a target preset over a duration using the
  selected AnimationBlendMode easing curve.

Lip Synchronization:
  Phonemes are mapped to visemes (visual mouth shapes). The engine
  splits spoken text into phonemes using simple vowel/consonant
  detection, maps each phoneme to a viseme, and lays the visemes
  out evenly across the requested duration. Ticking advances the
  current time and applies the active viseme's blend shape weights
  to the character's facial rig.

Hair & Fur Simulation:
  Hair strands are chains of segments advanced each tick by gravity
  and wind forces. The simulation method (PBD, Verlet, mass-spring,
  strand-based, hybrid) controls the integrator. Fur uses the same
  solver pipeline with shorter strands and higher density. A global
  WindConfig drives all simulations.
"""

from __future__ import annotations

import datetime
import math
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Maximum number of registered facial rigs (one per character).
_MAX_RIGS: int = 500

# Maximum number of stored expression presets.
_MAX_PRESETS: int = 200

# Maximum number of phoneme-to-viseme mappings.
_MAX_PHONEME_MAPPINGS: int = 50

# Maximum number of concurrent lip sync tracks.
_MAX_LIP_SYNC_TRACKS: int = 500

# Maximum number of registered hair styles.
_MAX_HAIR_STYLES: int = 500

# Maximum number of registered fur coats.
_MAX_FUR_COATS: int = 500

# Maximum number of retained audit-log events (FIFO eviction).
_MAX_EVENTS: int = 2000

# Default gravity vector applied during hair/fur simulation (m/s^2).
_DEFAULT_GRAVITY: Tuple[float, float, float] = (0.0, -9.81, 0.0)

# Default number of segments per simulated hair/fur strand.
_DEFAULT_STRAND_SEGMENTS: int = 8


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FacialExpression(Enum):
    """Recognized facial expression categories."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    FEARFUL = "fearful"
    CONTEMPT = "contempt"
    SLEEPY = "sleepy"
    PAIN = "pain"
    JOY = "joy"
    DETERMINATION = "determination"
    SUSPICIOUS = "suspicious"
    BORED = "bored"
    EXCITED = "excited"
    CONFUSED = "confused"
    AMUSED = "amused"
    PROUD = "proud"
    EMBARRASSED = "embarrassed"
    CONCENTRATING = "concentrating"


class VisemeType(Enum):
    """Visual mouth shapes corresponding to speech phonemes."""
    REST = "rest"
    A = "a"
    E = "e"
    I = "i"
    O = "o"
    U = "u"
    F_V = "f_v"
    TH = "th"
    S_Z = "s_z"
    L = "l"
    R = "r"
    P_B = "p_b"
    M = "m"
    N = "n"
    K_G = "k_g"
    T_D = "t_d"
    W = "w"
    SH_CH_J = "sh_ch_j"
    Y = "y"


class HairType(Enum):
    """Categorization of hair geometry and styling."""
    STRAIGHT = "straight"
    WAVY = "wavy"
    CURLY = "curly"
    COILY = "coily"
    BRAIDED = "braided"
    DREADLOCKS = "dreadlocks"
    PONYTAIL = "ponytail"
    BUN = "bun"
    SHORT = "short"
    LONG = "long"
    BALD = "bald"
    MOHAWK = "mohawk"
    AFRO = "afro"
    PIGTAILS = "pigtails"


class HairSimulationMethod(Enum):
    """Numerical solver used for hair/fur strand simulation."""
    NONE = "none"
    POSITION_BASED_DYNAMICS = "position_based_dynamics"
    MASS_SPRING = "mass_spring"
    VERLET_INTEGRATION = "verlet_integration"
    STRAND_BASED = "strand_based"
    HYBRID = "hybrid"


class FurType(Enum):
    """Categorization of fur coat geometry and density."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    DENSE = "dense"
    SPARSE = "sparse"
    FLUFFY = "fluffy"
    WIRE = "wire"
    CURLY = "curly"
    FEATHERED = "feathered"


class AppearanceEventKind(Enum):
    """Audit-log event categories emitted by the engine."""
    FACE_REGISTERED = "face_registered"
    EXPRESSION_SET = "expression_set"
    EXPRESSION_BLEND = "expression_blend"
    LIP_SYNC_STARTED = "lip_sync_started"
    LIP_SYNC_STOPPED = "lip_sync_stopped"
    PHONEME_REACHED = "phoneme_reached"
    HAIR_REGISTERED = "hair_registered"
    HAIR_SIMULATED = "hair_simulated"
    FUR_REGISTERED = "fur_registered"
    FUR_SIMULATED = "fur_simulated"
    WIND_APPLIED = "wind_applied"
    BLEND_SHAPE_UPDATED = "blend_shape_updated"


class AnimationBlendMode(Enum):
    """Easing curve applied during expression blending."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    SPLINE = "spline"
    STEP = "step"


class SyncState(Enum):
    """Playback state of a lip sync track."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"


class EmotionIntensity(Enum):
    """Intensity bands applied to facial expressions."""
    SUBTLE = "subtle"
    MILD = "mild"
    MODERATE = "moderate"
    STRONG = "strong"
    EXTREME = "extreme"


# ---------------------------------------------------------------------------
# Helper Functions (3D vector math on plain tuples)
# ---------------------------------------------------------------------------

def _vec3_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec3_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec3_scale(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec3_dot(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec3_length(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec3_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    length_val = _vec3_length(v)
    if length_val < 1e-9:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / length_val
    return (v[0] * inv, v[1] * inv, v[2] * inv)


def _vec3_lerp(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a float to ``[low, high]``."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with 'Z' suffix."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


# ---------------------------------------------------------------------------
# Blend Shapes & Facial Rig
# ---------------------------------------------------------------------------

@dataclass
class BlendShape:
    """A single morph target (e.g. Smile, JawOpen) for a facial rig.

    The ``weight`` field is normalized to ``[min_value, max_value]``; most
    rigs use ``0.0`` to ``1.0``. The ``alias`` is an alternative name used
    by external animation tools.
    """

    id: str = field(default_factory=lambda: _new_id("bs"))
    name: str = ""
    alias: str = ""
    weight: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    category: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.weight = _clamp(self.weight, self.min_value, self.max_value)

    def set_weight(self, weight: float) -> None:
        """Update the weight, clamping it to the valid range."""
        self.weight = _clamp(weight, self.min_value, self.max_value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "alias": self.alias,
            "weight": self.weight,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "category": self.category,
            "metadata": dict(self.metadata),
        }


@dataclass
class BlendShapeGroup:
    """A logical grouping of related blend shapes (e.g. "mouth", "eyes")."""

    id: str = field(default_factory=lambda: _new_id("bsg"))
    name: str = ""
    blend_shape_ids: List[str] = field(default_factory=list)
    category: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "blend_shape_ids": list(self.blend_shape_ids),
            "category": self.category,
            "metadata": dict(self.metadata),
        }


@dataclass
class ExpressionPreset:
    """A named, reusable expression configuration.

    ``blend_weights`` is a mapping of blend-shape name -> target weight.
    """

    id: str = field(default_factory=lambda: _new_id("preset"))
    name: str = ""
    expression: FacialExpression = FacialExpression.NEUTRAL
    intensity: EmotionIntensity = EmotionIntensity.MODERATE
    blend_weights: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "expression": self.expression.value,
            "intensity": self.intensity.value,
            "blend_weights": dict(self.blend_weights),
            "description": self.description,
            "metadata": dict(self.metadata),
        }


@dataclass
class FacialRig:
    """A character's complete facial rig.

    Holds the blend shapes available on the character, any logical
    groups, the currently active expression, and the live weights
    keyed by blend-shape name.
    """

    id: str = field(default_factory=lambda: _new_id("rig"))
    character_id: str = ""
    blend_shapes: List[BlendShape] = field(default_factory=list)
    groups: List[BlendShapeGroup] = field(default_factory=list)
    current_expression: FacialExpression = FacialExpression.NEUTRAL
    current_weights: Dict[str, float] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    # Internal lookup by blend-shape name for fast weight updates.
    _shape_map: Dict[str, BlendShape] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._rebuild_shape_map()
        # Ensure current_weights has an entry for every shape.
        for shape in self.blend_shapes:
            self.current_weights.setdefault(shape.name, shape.weight)

    def _rebuild_shape_map(self) -> None:
        self._shape_map = {s.name: s for s in self.blend_shapes}

    def get_shape(self, name: str) -> Optional[BlendShape]:
        """Return the blend shape with the given name, if any."""
        return self._shape_map.get(name)

    def apply_weights(self, weights: Dict[str, float]) -> None:
        """Apply a weight map, clamping each value to the shape's range."""
        for name, weight in weights.items():
            shape = self._shape_map.get(name)
            if shape is None:
                continue
            shape.set_weight(weight)
            self.current_weights[name] = shape.weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_id": self.character_id,
            "blend_shapes": [s.to_dict() for s in self.blend_shapes],
            "groups": [g.to_dict() for g in self.groups],
            "current_expression": self.current_expression.value,
            "current_weights": dict(self.current_weights),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Lip Sync
# ---------------------------------------------------------------------------

@dataclass
class PhonemeMapping:
    """Maps a viseme to a set of phonemes and blend-shape weights."""

    viseme: VisemeType = VisemeType.REST
    phonemes: List[str] = field(default_factory=list)
    blend_shape_weights: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "viseme": self.viseme.value,
            "phonemes": list(self.phonemes),
            "blend_shape_weights": dict(self.blend_shape_weights),
        }


@dataclass
class LipSyncTrack:
    """A timed viseme sequence for a piece of spoken text.

    ``visemes`` is a list of ``(VisemeType, start_time, end_time, weight)``
    tuples spanning the track ``duration``.
    """

    id: str = field(default_factory=lambda: _new_id("ls"))
    character_id: str = ""
    text: str = ""
    duration: float = 0.0
    visemes: List[Tuple[VisemeType, float, float, float]] = field(default_factory=list)
    state: SyncState = SyncState.IDLE
    start_time: float = 0.0
    current_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_id": self.character_id,
            "text": self.text,
            "duration": self.duration,
            "visemes": [
                [v.value, start, end, weight]
                for (v, start, end, weight) in self.visemes
            ],
            "state": self.state.value,
            "start_time": self.start_time,
            "current_time": self.current_time,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Hair & Fur
# ---------------------------------------------------------------------------

@dataclass
class HairStrand:
    """A single simulated hair strand.

    The strand is a chain of segment positions starting at
    ``root_position``. ``stiffness`` controls constraint rigidity,
    ``damping`` controls velocity loss, and ``rest_length`` is the
    target distance between adjacent segments.
    """

    id: str = field(default_factory=lambda: _new_id("strand"))
    root_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    segments: List[Tuple[float, float, float]] = field(default_factory=list)
    stiffness: float = 0.5
    damping: float = 0.1
    rest_length: float = 0.05
    mass: float = 0.001
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Previous positions used by the Verlet integrator.
    _prev_segments: List[Tuple[float, float, float]] = field(
        default_factory=list, repr=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "root_position": list(self.root_position),
            "segments": [list(s) for s in self.segments],
            "stiffness": self.stiffness,
            "damping": self.damping,
            "rest_length": self.rest_length,
            "mass": self.mass,
            "metadata": dict(self.metadata),
        }


@dataclass
class HairStyle:
    """A character's full hair configuration."""

    id: str = field(default_factory=lambda: _new_id("hair"))
    character_id: str = ""
    hair_type: HairType = HairType.STRAIGHT
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    root_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    tip_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    simulation_method: HairSimulationMethod = HairSimulationMethod.NONE
    strand_count: int = 0
    length: float = 0.0
    thickness: float = 0.001
    stiffness: float = 0.5
    damping: float = 0.1
    gravity_factor: float = 1.0
    wind_factor: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    # Simulated strands (only populated when simulation is enabled).
    strands: List[HairStrand] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_id": self.character_id,
            "hair_type": self.hair_type.value,
            "color": list(self.color),
            "root_color": list(self.root_color),
            "tip_color": list(self.tip_color),
            "simulation_method": self.simulation_method.value,
            "strand_count": self.strand_count,
            "length": self.length,
            "thickness": self.thickness,
            "stiffness": self.stiffness,
            "damping": self.damping,
            "gravity_factor": self.gravity_factor,
            "wind_factor": self.wind_factor,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
            "strands": [s.to_dict() for s in self.strands],
        }


@dataclass
class FurCoat:
    """A character's fur coat configuration."""

    id: str = field(default_factory=lambda: _new_id("fur"))
    character_id: str = ""
    fur_type: FurType = FurType.SHORT
    base_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    tip_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    density: float = 0.5
    length: float = 0.02
    thickness: float = 0.0005
    simulation_method: HairSimulationMethod = HairSimulationMethod.NONE
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    # Simulated fur strands (shorter, higher density than hair).
    strands: List[HairStrand] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_id": self.character_id,
            "fur_type": self.fur_type.value,
            "base_color": list(self.base_color),
            "tip_color": list(self.tip_color),
            "density": self.density,
            "length": self.length,
            "thickness": self.thickness,
            "simulation_method": self.simulation_method.value,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
            "strands": [s.to_dict() for s in self.strands],
        }


@dataclass
class WindConfig:
    """Global wind parameters driving hair/fur simulation."""

    direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    strength: float = 0.0
    turbulence: float = 0.0
    frequency: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": list(self.direction),
            "strength": self.strength,
            "turbulence": self.turbulence,
            "frequency": self.frequency,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Stats, Snapshot & Events
# ---------------------------------------------------------------------------

@dataclass
class AppearanceStats:
    """Aggregate counts of registered appearance assets."""

    total_rigs: int = 0
    total_expressions: int = 0
    total_lip_sync_tracks: int = 0
    total_hair_styles: int = 0
    total_fur_coats: int = 0
    active_lip_syncs: int = 0
    active_simulations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_rigs": self.total_rigs,
            "total_expressions": self.total_expressions,
            "total_lip_sync_tracks": self.total_lip_sync_tracks,
            "total_hair_styles": self.total_hair_styles,
            "total_fur_coats": self.total_fur_coats,
            "active_lip_syncs": self.active_lip_syncs,
            "active_simulations": self.active_simulations,
        }


@dataclass
class AppearanceSnapshot:
    """An immutable point-in-time snapshot of the engine state."""

    rigs: List[FacialRig] = field(default_factory=list)
    expressions: List[ExpressionPreset] = field(default_factory=list)
    lip_sync_tracks: List[LipSyncTrack] = field(default_factory=list)
    hair_styles: List[HairStyle] = field(default_factory=list)
    fur_coats: List[FurCoat] = field(default_factory=list)
    stats: AppearanceStats = field(default_factory=AppearanceStats)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rigs": [r.to_dict() for r in self.rigs],
            "expressions": [e.to_dict() for e in self.expressions],
            "lip_sync_tracks": [t.to_dict() for t in self.lip_sync_tracks],
            "hair_styles": [h.to_dict() for h in self.hair_styles],
            "fur_coats": [f.to_dict() for f in self.fur_coats],
            "stats": self.stats.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class AppearanceEvent:
    """An audit-log entry recording a state change in the engine."""

    id: str = field(default_factory=lambda: _new_id("evt"))
    kind: AppearanceEventKind = AppearanceEventKind.FACE_REGISTERED
    timestamp: str = field(default_factory=_now_iso)
    data: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "data": dict(self.data),
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Character Appearance Engine (Singleton)
# ---------------------------------------------------------------------------

class CharacterAppearanceEngine:
    """Thread-safe character appearance engine.

    Manages facial rigs, expression presets, phoneme mappings, lip sync
    tracks, hair styles, fur coats, and global wind. All public methods
    are guarded by a reentrant lock.

    The engine is a singleton accessed via ``get_character_appearance_engine``.
    """

    _instance: Optional["CharacterAppearanceEngine"] = None
    _lock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton Construction
    # ------------------------------------------------------------------

    def __new__(cls) -> "CharacterAppearanceEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Facial rigs keyed by character_id.
            self._rigs: Dict[str, FacialRig] = {}
            # Expression presets keyed by preset_id.
            self._presets: Dict[str, ExpressionPreset] = {}
            # Phoneme mappings keyed by viseme.
            self._phoneme_mappings: Dict[VisemeType, PhonemeMapping] = {}
            # Lip sync tracks keyed by track_id.
            self._lip_sync_tracks: Dict[str, LipSyncTrack] = {}
            # Hair styles keyed by character_id.
            self._hair_styles: Dict[str, HairStyle] = {}
            # Fur coats keyed by character_id.
            self._fur_coats: Dict[str, FurCoat] = {}
            # Global wind configuration.
            self._wind: WindConfig = WindConfig()
            # Audit log of recent events (FIFO).
            self._events: List[AppearanceEvent] = []

            # Counters used for FIFO eviction of the various registries.
            self._total_rigs_registered: int = 0
            self._total_presets_created: int = 0
            self._total_lip_sync_generated: int = 0
            self._total_hair_registered: int = 0
            self._total_fur_registered: int = 0
            self._total_events_emitted: int = 0

            # Per-character expression blend state.
            # character_id -> {target_expression, start_weights, target_weights,
            #                   duration, elapsed, blend_mode}
            self._blend_state: Dict[str, Dict[str, Any]] = {}

            self._initialized = True

            # Populate seed data now that all fields exist.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "CharacterAppearanceEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        kind: AppearanceEventKind,
        data: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> AppearanceEvent:
        """Create, log, and record an appearance event (internal only).

        The event log is capped at ``_MAX_EVENTS``; oldest entries are
        evicted first (FIFO).
        """
        event = AppearanceEvent(
            kind=kind,
            data=data or {},
            description=description,
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            del self._events[: len(self._events) - _MAX_EVENTS]
        self._total_events_emitted += 1
        return event

    @staticmethod
    def _intensity_scale(intensity: EmotionIntensity) -> float:
        """Map an emotion intensity band to a 0..1 multiplier."""
        return {
            EmotionIntensity.SUBTLE: 0.25,
            EmotionIntensity.MILD: 0.45,
            EmotionIntensity.MODERATE: 0.65,
            EmotionIntensity.STRONG: 0.85,
            EmotionIntensity.EXTREME: 1.0,
        }.get(intensity, 0.65)

    @staticmethod
    def _apply_blend_easing(progress: float, mode: AnimationBlendMode) -> float:
        """Apply the easing curve for the given blend mode to progress in 0..1."""
        progress = _clamp(progress, 0.0, 1.0)
        if mode == AnimationBlendMode.LINEAR:
            return progress
        if mode == AnimationBlendMode.EASE_IN:
            return progress * progress
        if mode == AnimationBlendMode.EASE_OUT:
            return 1.0 - (1.0 - progress) * (1.0 - progress)
        if mode == AnimationBlendMode.EASE_IN_OUT:
            if progress < 0.5:
                return 2.0 * progress * progress
            return 1.0 - 2.0 * (1.0 - progress) * (1.0 - progress)
        if mode == AnimationBlendMode.SPLINE:
            # Smoothstep cubic interpolation.
            return progress * progress * (3.0 - 2.0 * progress)
        if mode == AnimationBlendMode.STEP:
            return 1.0 if progress >= 1.0 else 0.0
        return progress

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with default phoneme mappings, blend shapes,
        a hero facial rig, expression presets, a hero hair style, a wolf
        fur coat, and a default wind configuration.
        """
        # --- Phoneme mappings for the common visemes ------------------
        seed_mappings = [
            (VisemeType.A, ["a", "aa", "ah"], {"JawOpen": 0.8, "Smile": 0.0}),
            (VisemeType.E, ["e", "eh"], {"JawOpen": 0.5, "Smile": 0.3}),
            (VisemeType.I, ["i", "iy"], {"JawOpen": 0.3, "Smile": 0.5}),
            (VisemeType.O, ["o", "ow"], {"JawOpen": 0.6, "Smile": 0.0}),
            (VisemeType.U, ["u", "uw"], {"JawOpen": 0.3, "Smile": 0.0}),
            (VisemeType.M, ["m", "b", "p"], {"JawOpen": 0.0, "Smile": 0.0}),
            (VisemeType.L, ["l"], {"JawOpen": 0.4, "Smile": 0.1}),
            (VisemeType.S_Z, ["s", "z", "sh"], {"JawOpen": 0.2, "Smile": 0.2}),
        ]
        for viseme, phonemes, weights in seed_mappings:
            mapping = PhonemeMapping(
                viseme=viseme,
                phonemes=list(phonemes),
                blend_shape_weights=dict(weights),
            )
            self._phoneme_mappings[viseme] = mapping

        # --- Hero character facial rig --------------------------------
        hero_shapes = [
            BlendShape(name="Smile", weight=0.0, category="mouth"),
            BlendShape(name="Frown", weight=0.0, category="mouth"),
            BlendShape(name="EyebrowRaise", weight=0.0, category="eyes"),
            BlendShape(name="JawOpen", weight=0.0, category="jaw"),
        ]
        hero_rig = FacialRig(
            character_id="character_hero",
            blend_shapes=hero_shapes,
            current_expression=FacialExpression.NEUTRAL,
        )
        self._rigs["character_hero"] = hero_rig
        self._total_rigs_registered += 1
        self._emit_event(
            AppearanceEventKind.FACE_REGISTERED,
            {"character_id": "character_hero", "blend_shape_count": 4},
            "Seeded hero facial rig",
        )

        # --- Expression presets ---------------------------------------
        presets_data = [
            (
                "Happy Smile",
                FacialExpression.HAPPY,
                EmotionIntensity.MODERATE,
                {"Smile": 0.8, "JawOpen": 0.0, "Frown": 0.0, "EyebrowRaise": 0.3},
                "A warm, friendly smile",
            ),
            (
                "Sad Frown",
                FacialExpression.SAD,
                EmotionIntensity.MODERATE,
                {"Smile": 0.0, "Frown": 0.7, "JawOpen": 0.0, "EyebrowRaise": 0.0},
                "A downcast sad expression",
            ),
            (
                "Angry Glare",
                FacialExpression.ANGRY,
                EmotionIntensity.STRONG,
                {"Smile": 0.0, "Frown": 0.9, "JawOpen": 0.0, "EyebrowRaise": 0.0},
                "An intense angry glare",
            ),
            (
                "Surprised",
                FacialExpression.SURPRISED,
                EmotionIntensity.EXTREME,
                {"Smile": 0.0, "JawOpen": 0.8, "EyebrowRaise": 1.0, "Frown": 0.0},
                "A wide-eyed surprised reaction",
            ),
            (
                "Neutral",
                FacialExpression.NEUTRAL,
                EmotionIntensity.SUBTLE,
                {"Smile": 0.0, "Frown": 0.0, "EyebrowRaise": 0.0, "JawOpen": 0.0},
                "A resting neutral expression",
            ),
            (
                "Concentrating",
                FacialExpression.CONCENTRATING,
                EmotionIntensity.MILD,
                {"Smile": 0.0, "Frown": 0.4, "JawOpen": 0.0, "EyebrowRaise": 0.2},
                "A focused concentrating expression",
            ),
        ]
        for name, expression, intensity, weights, description in presets_data:
            preset = ExpressionPreset(
                name=name,
                expression=expression,
                intensity=intensity,
                blend_weights=dict(weights),
                description=description,
            )
            self._presets[preset.id] = preset
            self._total_presets_created += 1

        # --- Hero hair style -------------------------------------------
        hero_hair = HairStyle(
            character_id="character_hero",
            hair_type=HairType.STRAIGHT,
            color=(0.1, 0.05, 0.02),
            root_color=(0.08, 0.04, 0.02),
            tip_color=(0.15, 0.1, 0.05),
            simulation_method=HairSimulationMethod.STRAND_BASED,
            strand_count=1000,
            length=0.4,
            thickness=0.002,
            stiffness=0.6,
            damping=0.2,
            gravity_factor=1.0,
            wind_factor=1.0,
        )
        # Generate the underlying simulated strands for STRAND_BASED.
        hero_hair.strands = self._generate_strands(
            hero_hair.strand_count,
            hero_hair.length,
            hero_hair.stiffness,
            hero_hair.damping,
        )
        self._hair_styles["character_hero"] = hero_hair
        self._total_hair_registered += 1
        self._emit_event(
            AppearanceEventKind.HAIR_REGISTERED,
            {"character_id": "character_hero", "hair_type": HairType.STRAIGHT.value},
            "Seeded hero hair style",
        )

        # --- Wolf fur coat ---------------------------------------------
        wolf_fur = FurCoat(
            character_id="character_wolf",
            fur_type=FurType.MEDIUM,
            base_color=(0.4, 0.35, 0.3),
            tip_color=(0.6, 0.55, 0.5),
            density=0.8,
            length=0.05,
            thickness=0.001,
            simulation_method=HairSimulationMethod.POSITION_BASED_DYNAMICS,
        )
        # Generate shorter, denser fur strands for PBD simulation.
        fur_strand_count = max(int(50 * wolf_fur.density), 10)
        fur_strand_count = min(fur_strand_count, 500)
        wolf_fur.strands = self._generate_strands(
            fur_strand_count,
            wolf_fur.length,
            stiffness=0.7,
            damping=0.15,
        )
        self._fur_coats["character_wolf"] = wolf_fur
        self._total_fur_registered += 1
        self._emit_event(
            AppearanceEventKind.FUR_REGISTERED,
            {"character_id": "character_wolf", "fur_type": FurType.MEDIUM.value},
            "Seeded wolf fur coat",
        )

        # --- Wind configuration ---------------------------------------
        self._wind = WindConfig(
            direction=(1.0, 0.0, 0.0),
            strength=0.3,
            turbulence=0.1,
            frequency=2.0,
        )

    # ------------------------------------------------------------------
    # Facial Rig Management
    # ------------------------------------------------------------------

    def register_face(
        self,
        character_id: str,
        blend_shapes: List[BlendShape],
    ) -> FacialRig:
        """Register a facial rig for ``character_id``.

        Creates a new rig with the supplied blend shapes and a default
        NEUTRAL expression. If a rig already exists for the character it
        is replaced. FIFO eviction applies when ``_MAX_RIGS`` is exceeded.
        """
        with self._lock:
            if character_id in self._rigs:
                # Replace existing rig in place.
                rig = FacialRig(
                    character_id=character_id,
                    blend_shapes=list(blend_shapes),
                    current_expression=FacialExpression.NEUTRAL,
                )
                self._rigs[character_id] = rig
            else:
                if len(self._rigs) >= _MAX_RIGS:
                    # Evict the oldest entry (FIFO).
                    oldest_key = next(iter(self._rigs))
                    del self._rigs[oldest_key]
                rig = FacialRig(
                    character_id=character_id,
                    blend_shapes=list(blend_shapes),
                    current_expression=FacialExpression.NEUTRAL,
                )
                self._rigs[character_id] = rig
                self._total_rigs_registered += 1

            self._emit_event(
                AppearanceEventKind.FACE_REGISTERED,
                {
                    "character_id": character_id,
                    "blend_shape_count": len(blend_shapes),
                },
                f"Registered facial rig for {character_id}",
            )
            return rig

    def get_face(self, character_id: str) -> Optional[FacialRig]:
        """Return the facial rig for ``character_id`` if registered."""
        with self._lock:
            return self._rigs.get(character_id)

    def list_faces(self) -> List[FacialRig]:
        """Return all registered facial rigs."""
        with self._lock:
            return list(self._rigs.values())

    def set_expression(
        self,
        character_id: str,
        expression: FacialExpression,
        intensity: EmotionIntensity = EmotionIntensity.MODERATE,
        blend_weights: Optional[Dict[str, float]] = None,
    ) -> FacialRig:
        """Set the current expression for ``character_id``.

        Applies ``blend_weights`` (scaled by the intensity multiplier) to
        the rig's blend shapes. Any blend shapes not mentioned in
        ``blend_weights`` are reset to ``0.0``.
        """
        with self._lock:
            rig = self._rigs.get(character_id)
            if rig is None:
                raise KeyError(f"No facial rig registered for '{character_id}'")

            scale = self._intensity_scale(intensity)
            # Reset every shape to zero first.
            reset_weights = {shape.name: 0.0 for shape in rig.blend_shapes}
            rig.apply_weights(reset_weights)
            # Apply the requested weights scaled by intensity.
            if blend_weights:
                scaled = {
                    name: weight * scale for name, weight in blend_weights.items()
                }
                rig.apply_weights(scaled)
            rig.current_expression = expression
            rig.timestamp = _now_iso()

            # Cancel any in-flight blend for this character.
            self._blend_state.pop(character_id, None)

            self._emit_event(
                AppearanceEventKind.EXPRESSION_SET,
                {
                    "character_id": character_id,
                    "expression": expression.value,
                    "intensity": intensity.value,
                },
                f"Set expression {expression.value} for {character_id}",
            )
            return rig

    def blend_expression(
        self,
        character_id: str,
        target_expression: FacialExpression,
        duration: float = 0.5,
        blend_mode: AnimationBlendMode = AnimationBlendMode.EASE_IN_OUT,
    ) -> FacialRig:
        """Begin blending ``character_id`` toward ``target_expression``.

        Records the start weights and target weights so that
        ``tick_expression_blend`` can interpolate over ``duration`` seconds.
        The target weights are derived from the first matching preset
        (if any); otherwise a neutral weight map is used.
        """
        with self._lock:
            rig = self._rigs.get(character_id)
            if rig is None:
                raise KeyError(f"No facial rig registered for '{character_id}'")

            # Find target weights from a matching preset, if available.
            target_weights: Dict[str, float] = {}
            for preset in self._presets.values():
                if preset.expression == target_expression:
                    target_weights = dict(preset.blend_weights)
                    break
            # Ensure every shape has an entry (default 0.0).
            for shape in rig.blend_shapes:
                target_weights.setdefault(shape.name, 0.0)

            start_weights = {name: rig.current_weights.get(name, 0.0)
                             for name in target_weights}

            self._blend_state[character_id] = {
                "target_expression": target_expression,
                "start_weights": start_weights,
                "target_weights": target_weights,
                "duration": max(duration, 1e-6),
                "elapsed": 0.0,
                "blend_mode": blend_mode,
            }

            self._emit_event(
                AppearanceEventKind.EXPRESSION_BLEND,
                {
                    "character_id": character_id,
                    "target_expression": target_expression.value,
                    "duration": duration,
                    "blend_mode": blend_mode.value,
                },
                f"Begin blending {character_id} to {target_expression.value}",
            )
            return rig

    def tick_expression_blend(
        self,
        character_id: str,
        delta_time: float,
    ) -> FacialRig:
        """Advance an in-flight expression blend by ``delta_time`` seconds."""
        with self._lock:
            rig = self._rigs.get(character_id)
            if rig is None:
                raise KeyError(f"No facial rig registered for '{character_id}'")

            state = self._blend_state.get(character_id)
            if state is None:
                return rig

            state["elapsed"] += delta_time
            progress = state["elapsed"] / state["duration"]
            eased = self._apply_blend_easing(progress, state["blend_mode"])

            start_weights: Dict[str, float] = state["start_weights"]
            target_weights: Dict[str, float] = state["target_weights"]

            interpolated: Dict[str, float] = {}
            for name in target_weights:
                start_val = start_weights.get(name, 0.0)
                target_val = target_weights.get(name, 0.0)
                interpolated[name] = start_val + (target_val - start_val) * eased
            rig.apply_weights(interpolated)
            rig.timestamp = _now_iso()

            if progress >= 1.0:
                # Finalize: snap to target and update expression.
                rig.apply_weights(target_weights)
                rig.current_expression = state["target_expression"]
                self._blend_state.pop(character_id, None)
                self._emit_event(
                    AppearanceEventKind.BLEND_SHAPE_UPDATED,
                    {
                        "character_id": character_id,
                        "expression": rig.current_expression.value,
                    },
                    f"Blend completed for {character_id}",
                )

            return rig

    # ------------------------------------------------------------------
    # Expression Presets
    # ------------------------------------------------------------------

    def create_expression_preset(
        self,
        name: str,
        expression: FacialExpression,
        intensity: EmotionIntensity = EmotionIntensity.MODERATE,
        blend_weights: Optional[Dict[str, float]] = None,
        description: str = "",
    ) -> ExpressionPreset:
        """Create and store a new expression preset."""
        with self._lock:
            if len(self._presets) >= _MAX_PRESETS:
                # FIFO eviction.
                oldest_key = next(iter(self._presets))
                del self._presets[oldest_key]
            preset = ExpressionPreset(
                name=name,
                expression=expression,
                intensity=intensity,
                blend_weights=dict(blend_weights or {}),
                description=description,
            )
            self._presets[preset.id] = preset
            self._total_presets_created += 1
            return preset

    def list_expression_presets(
        self, expression: Optional[FacialExpression] = None
    ) -> List[ExpressionPreset]:
        """Return all presets, optionally filtered by expression."""
        with self._lock:
            presets = list(self._presets.values())
            if expression is not None:
                presets = [p for p in presets if p.expression == expression]
            return presets

    def get_expression_preset(self, preset_id: str) -> Optional[ExpressionPreset]:
        """Return the preset with the given id, if any."""
        with self._lock:
            return self._presets.get(preset_id)

    # ------------------------------------------------------------------
    # Phoneme Mappings
    # ------------------------------------------------------------------

    def register_phoneme_mapping(
        self,
        viseme: VisemeType,
        phonemes: List[str],
        blend_shape_weights: Optional[Dict[str, float]] = None,
    ) -> PhonemeMapping:
        """Register or replace a phoneme-to-viseme mapping."""
        with self._lock:
            if len(self._phoneme_mappings) >= _MAX_PHONEME_MAPPINGS:
                # FIFO eviction (visemes are unique keys; evict the oldest).
                oldest_key = next(iter(self._phoneme_mappings))
                del self._phoneme_mappings[oldest_key]
            mapping = PhonemeMapping(
                viseme=viseme,
                phonemes=list(phonemes),
                blend_shape_weights=dict(blend_shape_weights or {}),
            )
            self._phoneme_mappings[viseme] = mapping
            return mapping

    def list_phoneme_mappings(self) -> List[PhonemeMapping]:
        """Return all registered phoneme mappings."""
        with self._lock:
            return list(self._phoneme_mappings.values())

    def _phoneme_to_viseme(self, phoneme: str) -> VisemeType:
        """Look up the viseme for a single phoneme, defaulting to REST."""
        phoneme_lower = phoneme.lower()
        for viseme, mapping in self._phoneme_mappings.items():
            if phoneme_lower in [p.lower() for p in mapping.phonemes]:
                return viseme
        return VisemeType.REST

    # ------------------------------------------------------------------
    # Lip Sync
    # ------------------------------------------------------------------

    def generate_lip_sync(
        self,
        character_id: str,
        text: str,
        duration: float,
    ) -> LipSyncTrack:
        """Generate a lip sync track from ``text`` over ``duration`` seconds.

        The text is split into phonemes using simple vowel/consonant
        detection. Each phoneme is mapped to a viseme via the registered
        phoneme mappings, and visemes are laid out evenly across the
        requested duration.
        """
        with self._lock:
            if len(self._lip_sync_tracks) >= _MAX_LIP_SYNC_TRACKS:
                # FIFO eviction.
                oldest_key = next(iter(self._lip_sync_tracks))
                del self._lip_sync_tracks[oldest_key]

            phonemes = self._split_text_to_phonemes(text)
            # Build the viseme list with even timing across the duration.
            viseme_entries: List[Tuple[VisemeType, float, float, float]] = []
            if phonemes:
                segment_duration = duration / max(len(phonemes), 1)
                for index, phoneme in enumerate(phonemes):
                    viseme = self._phoneme_to_viseme(phoneme)
                    start = index * segment_duration
                    end = start + segment_duration
                    viseme_entries.append((viseme, start, end, 1.0))

            track = LipSyncTrack(
                character_id=character_id,
                text=text,
                duration=duration,
                visemes=viseme_entries,
                state=SyncState.IDLE,
            )
            self._lip_sync_tracks[track.id] = track
            self._total_lip_sync_generated += 1
            return track

    @staticmethod
    def _split_text_to_phonemes(text: str) -> List[str]:
        """Split text into a simple sequence of phonemes.

        Uses a basic vowel/consonant grouping: vowels become individual
        phonemes; consecutive consonants are grouped until a vowel is
        encountered. Whitespace and punctuation act as phoneme boundaries.
        """
        if not text:
            return []
        vowels = set("aeiouy")
        phonemes: List[str] = []
        current_consonants: List[str] = []
        for char in text.lower():
            if char.isalpha():
                if char in vowels:
                    if current_consonants:
                        phonemes.append("".join(current_consonants))
                        current_consonants = []
                    phonemes.append(char)
                else:
                    current_consonants.append(char)
            else:
                # Whitespace/punctuation: flush any pending consonants.
                if current_consonants:
                    phonemes.append("".join(current_consonants))
                    current_consonants = []
        if current_consonants:
            phonemes.append("".join(current_consonants))
        return phonemes

    def start_lip_sync(self, track_id: str) -> LipSyncTrack:
        """Begin playback of a lip sync track."""
        with self._lock:
            track = self._lip_sync_tracks.get(track_id)
            if track is None:
                raise KeyError(f"No lip sync track with id '{track_id}'")
            track.state = SyncState.PLAYING
            if track.current_time <= 0.0:
                track.start_time = 0.0
                track.current_time = 0.0
            self._emit_event(
                AppearanceEventKind.LIP_SYNC_STARTED,
                {"track_id": track_id, "character_id": track.character_id},
                f"Started lip sync track {track_id}",
            )
            return track

    def pause_lip_sync(self, track_id: str) -> LipSyncTrack:
        """Pause a playing lip sync track."""
        with self._lock:
            track = self._lip_sync_tracks.get(track_id)
            if track is None:
                raise KeyError(f"No lip sync track with id '{track_id}'")
            if track.state == SyncState.PLAYING:
                track.state = SyncState.PAUSED
            return track

    def stop_lip_sync(self, track_id: str) -> LipSyncTrack:
        """Stop a lip sync track and reset its playback position."""
        with self._lock:
            track = self._lip_sync_tracks.get(track_id)
            if track is None:
                raise KeyError(f"No lip sync track with id '{track_id}'")
            track.state = SyncState.IDLE
            track.current_time = 0.0
            self._emit_event(
                AppearanceEventKind.LIP_SYNC_STOPPED,
                {"track_id": track_id, "character_id": track.character_id},
                f"Stopped lip sync track {track_id}",
            )
            return track

    def tick_lip_sync(self, delta_time: float) -> List[LipSyncTrack]:
        """Advance all playing lip sync tracks by ``delta_time`` seconds.

        For each playing track:
          * advance ``current_time`` by ``delta_time``
          * find the current viseme based on time
          * apply that viseme's blend shape weights to the rig
          * mark the track COMPLETED when ``current_time`` >= ``duration``
        """
        with self._lock:
            updated: List[LipSyncTrack] = []
            for track in self._lip_sync_tracks.values():
                if track.state != SyncState.PLAYING:
                    continue
                track.current_time += delta_time

                # Find the current viseme based on time.
                current_viseme = VisemeType.REST
                for viseme, start, end, _weight in track.visemes:
                    if start <= track.current_time < end:
                        current_viseme = viseme
                        break

                # Apply the viseme's blend shape weights to the rig.
                mapping = self._phoneme_mappings.get(current_viseme)
                if mapping is not None:
                    rig = self._rigs.get(track.character_id)
                    if rig is not None:
                        rig.apply_weights(mapping.blend_shape_weights)
                        rig.timestamp = _now_iso()
                        self._emit_event(
                            AppearanceEventKind.PHONEME_REACHED,
                            {
                                "track_id": track.id,
                                "character_id": track.character_id,
                                "viseme": current_viseme.value,
                            },
                            description=(
                                f"Track {track.id} reached viseme "
                                f"{current_viseme.value}"
                            ),
                        )

                # Mark complete when the duration has elapsed.
                if track.current_time >= track.duration:
                    track.state = SyncState.COMPLETED
                    # Reset the rig's mouth-related shapes when done.
                    rig = self._rigs.get(track.character_id)
                    if rig is not None:
                        reset = {
                            name: 0.0
                            for name in rig.current_weights
                            if name in ("JawOpen", "Smile", "Frown")
                        }
                        rig.apply_weights(reset)

                updated.append(track)
            return updated

    def get_lip_sync(self, track_id: str) -> Optional[LipSyncTrack]:
        """Return the lip sync track with the given id, if any."""
        with self._lock:
            return self._lip_sync_tracks.get(track_id)

    def list_lip_sync_tracks(
        self, character_id: Optional[str] = None
    ) -> List[LipSyncTrack]:
        """Return all lip sync tracks, optionally filtered by character."""
        with self._lock:
            tracks = list(self._lip_sync_tracks.values())
            if character_id is not None:
                tracks = [t for t in tracks if t.character_id == character_id]
            return tracks

    # ------------------------------------------------------------------
    # Hair Management
    # ------------------------------------------------------------------

    def register_hair(
        self,
        character_id: str,
        hair_type: HairType = HairType.STRAIGHT,
        color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        simulation_method: HairSimulationMethod = HairSimulationMethod.NONE,
        strand_count: int = 100,
        length: float = 0.2,
        thickness: float = 0.001,
        stiffness: float = 0.5,
        damping: float = 0.1,
    ) -> HairStyle:
        """Register a hair style for ``character_id``.

        Generates the underlying simulated strands if the simulation
        method is not NONE. FIFO eviction applies at ``_MAX_HAIR_STYLES``.
        """
        with self._lock:
            if character_id in self._hair_styles:
                # Replace existing hair style.
                style = self._hair_styles[character_id]
            else:
                if len(self._hair_styles) >= _MAX_HAIR_STYLES:
                    oldest_key = next(iter(self._hair_styles))
                    del self._hair_styles[oldest_key]
                style = HairStyle(character_id=character_id)
                self._total_hair_registered += 1
                self._hair_styles[character_id] = style

            style.hair_type = hair_type
            style.color = color
            style.root_color = color
            style.tip_color = color
            style.simulation_method = simulation_method
            style.strand_count = strand_count
            style.length = length
            style.thickness = thickness
            style.stiffness = stiffness
            style.damping = damping
            style.timestamp = _now_iso()

            # Build the simulated strands if simulation is enabled.
            if simulation_method != HairSimulationMethod.NONE:
                style.strands = self._generate_strands(
                    strand_count, length, stiffness, damping
                )
            else:
                style.strands = []

            self._emit_event(
                AppearanceEventKind.HAIR_REGISTERED,
                {
                    "character_id": character_id,
                    "hair_type": hair_type.value,
                    "strand_count": strand_count,
                },
                f"Registered hair for {character_id}",
            )
            return style

    def get_hair(self, character_id: str) -> Optional[HairStyle]:
        """Return the hair style for ``character_id`` if registered."""
        with self._lock:
            return self._hair_styles.get(character_id)

    def list_hair_styles(self) -> List[HairStyle]:
        """Return all registered hair styles."""
        with self._lock:
            return list(self._hair_styles.values())

    def simulate_hair(
        self,
        character_id: str,
        delta_time: float,
        wind: Optional[WindConfig] = None,
    ) -> HairStyle:
        """Advance the hair simulation for ``character_id`` by one step."""
        with self._lock:
            style = self._hair_styles.get(character_id)
            if style is None:
                raise KeyError(f"No hair style registered for '{character_id}'")
            if style.simulation_method == HairSimulationMethod.NONE:
                return style

            wind_config = wind if wind is not None else self._wind
            gravity = _vec3_scale(_DEFAULT_GRAVITY, style.gravity_factor)
            wind_force = self._compute_wind_force(wind_config)

            for strand in style.strands:
                self._advance_strand(
                    strand,
                    delta_time,
                    gravity,
                    wind_force,
                    style.stiffness,
                    style.damping,
                    style.simulation_method,
                )

            style.timestamp = _now_iso()
            self._emit_event(
                AppearanceEventKind.HAIR_SIMULATED,
                {
                    "character_id": character_id,
                    "strand_count": len(style.strands),
                    "delta_time": delta_time,
                },
                f"Simulated hair for {character_id}",
            )
            return style

    # ------------------------------------------------------------------
    # Fur Management
    # ------------------------------------------------------------------

    def register_fur(
        self,
        character_id: str,
        fur_type: FurType = FurType.SHORT,
        base_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        tip_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        density: float = 0.5,
        length: float = 0.02,
        thickness: float = 0.0005,
        simulation_method: HairSimulationMethod = HairSimulationMethod.NONE,
    ) -> FurCoat:
        """Register a fur coat for ``character_id``.

        Generates the underlying simulated strands (shorter, denser)
        if the simulation method is not NONE. FIFO eviction applies at
        ``_MAX_FUR_COATS``.
        """
        with self._lock:
            if character_id in self._fur_coats:
                coat = self._fur_coats[character_id]
            else:
                if len(self._fur_coats) >= _MAX_FUR_COATS:
                    oldest_key = next(iter(self._fur_coats))
                    del self._fur_coats[oldest_key]
                coat = FurCoat(character_id=character_id)
                self._total_fur_registered += 1
                self._fur_coats[character_id] = coat

            coat.fur_type = fur_type
            coat.base_color = base_color
            coat.tip_color = tip_color
            coat.density = density
            coat.length = length
            coat.thickness = thickness
            coat.simulation_method = simulation_method
            coat.timestamp = _now_iso()

            # Fur uses more, shorter strands than hair.
            if simulation_method != HairSimulationMethod.NONE:
                fur_strand_count = max(int(50 * density), 10)
                fur_strand_count = min(fur_strand_count, 500)
                coat.strands = self._generate_strands(
                    fur_strand_count,
                    length,
                    stiffness=0.7,
                    damping=0.15,
                )
            else:
                coat.strands = []

            self._emit_event(
                AppearanceEventKind.FUR_REGISTERED,
                {
                    "character_id": character_id,
                    "fur_type": fur_type.value,
                    "density": density,
                },
                f"Registered fur for {character_id}",
            )
            return coat

    def get_fur(self, character_id: str) -> Optional[FurCoat]:
        """Return the fur coat for ``character_id`` if registered."""
        with self._lock:
            return self._fur_coats.get(character_id)

    def list_fur_coats(self) -> List[FurCoat]:
        """Return all registered fur coats."""
        with self._lock:
            return list(self._fur_coats.values())

    def simulate_fur(
        self,
        character_id: str,
        delta_time: float,
        wind: Optional[WindConfig] = None,
    ) -> FurCoat:
        """Advance the fur simulation for ``character_id`` by one step."""
        with self._lock:
            coat = self._fur_coats.get(character_id)
            if coat is None:
                raise KeyError(f"No fur coat registered for '{character_id}'")
            if coat.simulation_method == HairSimulationMethod.NONE:
                return coat

            wind_config = wind if wind is not None else self._wind
            gravity = _DEFAULT_GRAVITY
            wind_force = self._compute_wind_force(wind_config)

            for strand in coat.strands:
                self._advance_strand(
                    strand,
                    delta_time,
                    gravity,
                    wind_force,
                    stiffness=0.7,
                    damping=0.15,
                    method=coat.simulation_method,
                )

            coat.timestamp = _now_iso()
            self._emit_event(
                AppearanceEventKind.FUR_SIMULATED,
                {
                    "character_id": character_id,
                    "strand_count": len(coat.strands),
                    "delta_time": delta_time,
                },
                f"Simulated fur for {character_id}",
            )
            return coat

    # ------------------------------------------------------------------
    # Wind
    # ------------------------------------------------------------------

    def set_wind(
        self,
        direction: Tuple[float, float, float] = (1.0, 0.0, 0.0),
        strength: float = 0.0,
        turbulence: float = 0.0,
        frequency: float = 1.0,
    ) -> WindConfig:
        """Update the global wind configuration."""
        with self._lock:
            self._wind = WindConfig(
                direction=_vec3_normalize(direction),
                strength=strength,
                turbulence=turbulence,
                frequency=frequency,
            )
            self._emit_event(
                AppearanceEventKind.WIND_APPLIED,
                {
                    "direction": list(self._wind.direction),
                    "strength": strength,
                    "turbulence": turbulence,
                    "frequency": frequency,
                },
                "Updated global wind configuration",
            )
            return self._wind

    def get_wind(self) -> WindConfig:
        """Return the current global wind configuration."""
        with self._lock:
            return self._wind

    # ------------------------------------------------------------------
    # Simulation Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_strands(
        count: int,
        length: float,
        stiffness: float,
        damping: float,
    ) -> List[HairStrand]:
        """Generate ``count`` simulated hair/fur strands along the +Y axis.

        Each strand is a chain of segments starting at a slightly randomized
        root position on the XZ plane, hanging downward.
        """
        strands: List[HairStrand] = []
        segment_count = _DEFAULT_STRAND_SEGMENTS
        segment_length = length / max(segment_count, 1)
        for index in range(count):
            # Spread roots on a small grid around the origin.
            root_x = (index % 32) * 0.01 - 0.16
            root_z = (index // 32) * 0.01 - 0.16
            root = (root_x, 0.0, root_z)
            segments: List[Tuple[float, float, float]] = []
            for seg in range(segment_count):
                y = -segment_length * (seg + 1)
                segments.append((root_x, y, root_z))
            strand = HairStrand(
                root_position=root,
                segments=segments,
                stiffness=stiffness,
                damping=damping,
                rest_length=segment_length,
                mass=0.001,
            )
            # Initialize Verlet previous positions to current positions.
            strand._prev_segments = list(segments)
            strands.append(strand)
        return strands

    @staticmethod
    def _compute_wind_force(wind: WindConfig) -> Tuple[float, float, float]:
        """Convert a WindConfig into an acceleration vector."""
        direction = _vec3_normalize(wind.direction)
        return _vec3_scale(direction, wind.strength)

    def _advance_strand(
        self,
        strand: HairStrand,
        delta_time: float,
        gravity: Tuple[float, float, float],
        wind_force: Tuple[float, float, float],
        stiffness: float,
        damping: float,
        method: HairSimulationMethod,
    ) -> None:
        """Advance a single strand by one simulation step.

        Dispatches to the appropriate integrator based on ``method``.
        Keeps the root segment pinned at ``root_position``.
        """
        if not strand.segments:
            return

        if method == HairSimulationMethod.POSITION_BASED_DYNAMICS:
            self._simulate_strand_pbd(
                strand, delta_time, gravity, wind_force, stiffness, damping
            )
        elif method == HairSimulationMethod.VERLET_INTEGRATION:
            self._simulate_strand_verlet(
                strand, delta_time, gravity, wind_force, stiffness, damping
            )
        elif method == HairSimulationMethod.MASS_SPRING:
            self._simulate_strand_mass_spring(
                strand, delta_time, gravity, wind_force, stiffness, damping
            )
        elif method == HairSimulationMethod.STRAND_BASED:
            # Strand-based: per-strand stiffness verlet with stronger
            # constraint enforcement.
            self._simulate_strand_verlet(
                strand, delta_time, gravity, wind_force, stiffness, damping
            )
            # Apply an extra constraint pass for stiffness.
            self._enforce_distance_constraints(strand, stiffness)
        elif method == HairSimulationMethod.HYBRID:
            # Hybrid: verlet integration followed by a PBD constraint pass.
            self._simulate_strand_verlet(
                strand, delta_time, gravity, wind_force, stiffness, damping
            )
            self._enforce_distance_constraints(strand, stiffness)
        else:
            # No simulation; leave positions unchanged.
            return

    @staticmethod
    def _simulate_strand_pbd(
        strand: HairStrand,
        delta_time: float,
        gravity: Tuple[float, float, float],
        wind_force: Tuple[float, float, float],
        stiffness: float,
        damping: float,
    ) -> None:
        """Position-Based Dynamics strand integrator.

        Steps:
          1. Predict positions using external forces (gravity + wind).
          2. Iteratively enforce distance constraints between neighbors.
          3. Pin the root segment.
        """
        segments = strand.segments
        external = _vec3_add(gravity, wind_force)
        # Apply damping by reducing velocity-derived motion implicitly.
        # Predict positions.
        predicted: List[Tuple[float, float, float]] = []
        for index, pos in enumerate(segments):
            if index == 0:
                # Pin the first segment to the root offset.
                root = strand.root_position
                predicted.append((root[0], root[1] - strand.rest_length, root[2]))
                continue
            delta = _vec3_scale(external, delta_time * delta_time)
            predicted.append(_vec3_add(pos, delta))

        # Constraint passes (Gauss-Seidel).
        iterations = 4
        for _ in range(iterations):
            for index in range(1, len(predicted)):
                prev_pos = predicted[index - 1]
                cur_pos = predicted[index]
                diff = _vec3_sub(cur_pos, prev_pos)
                dist = _vec3_length(diff)
                if dist < 1e-9:
                    continue
                rest = strand.rest_length
                correction = (dist - rest) / dist
                correction *= stiffness * (1.0 - damping)
                # Move only the current point (root stays fixed).
                move = _vec3_scale(diff, -correction)
                predicted[index] = _vec3_add(cur_pos, move)

        # Write back, applying damping to velocity implicitly.
        for index, pos in enumerate(predicted):
            old = segments[index]
            damped = (
                old[0] + (pos[0] - old[0]) * (1.0 - damping),
                old[1] + (pos[1] - old[1]) * (1.0 - damping),
                old[2] + (pos[2] - old[2]) * (1.0 - damping),
            )
            segments[index] = damped

    @staticmethod
    def _simulate_strand_verlet(
        strand: HairStrand,
        delta_time: float,
        gravity: Tuple[float, float, float],
        wind_force: Tuple[float, float, float],
        stiffness: float,
        damping: float,
    ) -> None:
        """Verlet integration strand solver.

        Uses the standard Verlet formula:
            x_new = 2*x - x_prev + a*dt^2
        with damping applied to the velocity term.
        """
        segments = strand.segments
        prev_segments = strand._prev_segments
        # Ensure prev list matches segments length.
        while len(prev_segments) < len(segments):
            prev_segments.append(segments[len(prev_segments)])

        external = _vec3_add(gravity, wind_force)
        acceleration = _vec3_scale(external, delta_time * delta_time)
        damping_factor = 1.0 - damping

        new_positions: List[Tuple[float, float, float]] = []
        for index, pos in enumerate(segments):
            if index == 0:
                # Pin first segment relative to the root.
                root = strand.root_position
                new_pos = (root[0], root[1] - strand.rest_length, root[2])
            else:
                prev = prev_segments[index]
                velocity = _vec3_scale(
                    _vec3_sub(pos, prev), damping_factor
                )
                new_pos = _vec3_add(_vec3_add(pos, velocity), acceleration)
            new_positions.append(new_pos)

        # Update previous positions for the next step.
        strand._prev_segments = list(segments)
        for index, new_pos in enumerate(new_positions):
            segments[index] = new_pos

    @staticmethod
    def _simulate_strand_mass_spring(
        strand: HairStrand,
        delta_time: float,
        gravity: Tuple[float, float, float],
        wind_force: Tuple[float, float, float],
        stiffness: float,
        damping: float,
    ) -> None:
        """Mass-spring strand solver (explicit Euler).

        Treats each segment as a point mass connected by springs to its
        neighbors with rest length ``strand.rest_length``.
        """
        segments = strand.segments
        if not segments:
            return
        external = _vec3_add(gravity, wind_force)
        forces: List[Tuple[float, float, float]] = [
            _vec3_scale(external, strand.mass)
        ] * len(segments)

        # Spring forces between neighbors.
        for index in range(1, len(segments)):
            prev_pos = segments[index - 1]
            cur_pos = segments[index]
            diff = _vec3_sub(cur_pos, prev_pos)
            dist = _vec3_length(diff)
            if dist < 1e-9:
                continue
            direction = _vec3_scale(diff, 1.0 / dist)
            spring_force = _vec3_scale(
                direction, -stiffness * (dist - strand.rest_length)
            )
            forces[index] = _vec3_add(forces[index], spring_force)
            forces[index - 1] = _vec3_sub(forces[index - 1], spring_force)

        # Integrate.
        new_positions: List[Tuple[float, float, float]] = []
        for index, pos in enumerate(segments):
            if index == 0:
                root = strand.root_position
                new_pos = (root[0], root[1] - strand.rest_length, root[2])
            else:
                accel = _vec3_scale(forces[index], 1.0 / max(strand.mass, 1e-9))
                delta = _vec3_scale(accel, delta_time * delta_time)
                new_pos = _vec3_add(pos, delta)
                # Apply damping.
                new_pos = _vec3_lerp(pos, new_pos, 1.0 - damping)
            new_positions.append(new_pos)

        strand._prev_segments = list(segments)
        for index, new_pos in enumerate(new_positions):
            segments[index] = new_pos

    @staticmethod
    def _enforce_distance_constraints(strand: HairStrand, stiffness: float) -> None:
        """Enforce rest-length distance constraints between neighbors."""
        segments = strand.segments
        for index in range(1, len(segments)):
            prev_pos = segments[index - 1]
            cur_pos = segments[index]
            diff = _vec3_sub(cur_pos, prev_pos)
            dist = _vec3_length(diff)
            if dist < 1e-9:
                continue
            rest = strand.rest_length
            correction = (dist - rest) / dist * stiffness
            move = _vec3_scale(diff, -correction)
            segments[index] = _vec3_add(cur_pos, move)

    # ------------------------------------------------------------------
    # Tick All Simulations
    # ------------------------------------------------------------------

    def tick_simulation(self, delta_time: float) -> Dict[str, Any]:
        """Tick all active hair and fur simulations with the current wind.

        Returns a dict with ``hair_count`` and ``fur_count`` of the
        simulations advanced.
        """
        with self._lock:
            wind_config = self._wind
            hair_count = 0
            fur_count = 0
            for character_id, style in self._hair_styles.items():
                if style.simulation_method == HairSimulationMethod.NONE:
                    continue
                self.simulate_hair(character_id, delta_time, wind_config)
                hair_count += 1
            for character_id, coat in self._fur_coats.items():
                if coat.simulation_method == HairSimulationMethod.NONE:
                    continue
                self.simulate_fur(character_id, delta_time, wind_config)
                fur_count += 1
            return {"hair_count": hair_count, "fur_count": fur_count}

    # ------------------------------------------------------------------
    # Events & Stats
    # ------------------------------------------------------------------

    def list_events(
        self,
        kind: Optional[AppearanceEventKind] = None,
        limit: int = 100,
    ) -> List[AppearanceEvent]:
        """Return recent events, optionally filtered by kind."""
        with self._lock:
            events = list(self._events)
            if kind is not None:
                events = [e for e in events if e.kind == kind]
            if limit > 0:
                events = events[-limit:]
            return events

    def get_stats(self) -> AppearanceStats:
        """Return aggregate statistics about registered appearance assets."""
        with self._lock:
            active_lip_syncs = sum(
                1
                for track in self._lip_sync_tracks.values()
                if track.state == SyncState.PLAYING
            )
            active_simulations = sum(
                1
                for style in self._hair_styles.values()
                if style.simulation_method != HairSimulationMethod.NONE
            ) + sum(
                1
                for coat in self._fur_coats.values()
                if coat.simulation_method != HairSimulationMethod.NONE
            )
            return AppearanceStats(
                total_rigs=len(self._rigs),
                total_expressions=len(self._presets),
                total_lip_sync_tracks=len(self._lip_sync_tracks),
                total_hair_styles=len(self._hair_styles),
                total_fur_coats=len(self._fur_coats),
                active_lip_syncs=active_lip_syncs,
                active_simulations=active_simulations,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current engine state.

        The ``initialized`` flag is always the first key.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_rigs": len(self._rigs),
                "total_presets": len(self._presets),
                "total_phoneme_mappings": len(self._phoneme_mappings),
                "total_lip_sync_tracks": len(self._lip_sync_tracks),
                "total_hair_styles": len(self._hair_styles),
                "total_fur_coats": len(self._fur_coats),
                "total_events": len(self._events),
                "max_rigs": _MAX_RIGS,
                "max_presets": _MAX_PRESETS,
                "max_phoneme_mappings": _MAX_PHONEME_MAPPINGS,
                "max_lip_sync_tracks": _MAX_LIP_SYNC_TRACKS,
                "max_hair_styles": _MAX_HAIR_STYLES,
                "max_fur_coats": _MAX_FUR_COATS,
                "max_events": _MAX_EVENTS,
                "wind": self._wind.to_dict(),
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> AppearanceSnapshot:
        """Capture an immutable point-in-time snapshot of the engine state."""
        with self._lock:
            stats = self.get_stats()
            return AppearanceSnapshot(
                rigs=list(self._rigs.values()),
                expressions=list(self._presets.values()),
                lip_sync_tracks=list(self._lip_sync_tracks.values()),
                hair_styles=list(self._hair_styles.values()),
                fur_coats=list(self._fur_coats.values()),
                stats=stats,
                timestamp=_now_iso(),
            )

    def reset(self) -> None:
        """Reset the entire character appearance engine state.

        Clears all registries and re-seeds the default data. Does NOT
        reset the singleton instance itself.
        """
        with self._lock:
            self._rigs.clear()
            self._presets.clear()
            self._phoneme_mappings.clear()
            self._lip_sync_tracks.clear()
            self._hair_styles.clear()
            self._fur_coats.clear()
            self._events.clear()
            self._blend_state.clear()

            self._total_rigs_registered = 0
            self._total_presets_created = 0
            self._total_lip_sync_generated = 0
            self._total_hair_registered = 0
            self._total_fur_registered = 0
            self._total_events_emitted = 0

            # Re-seed default data.
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory Function
# ---------------------------------------------------------------------------

def get_character_appearance_engine() -> CharacterAppearanceEngine:
    """Get or create the singleton CharacterAppearanceEngine instance."""
    return CharacterAppearanceEngine.get_instance()
