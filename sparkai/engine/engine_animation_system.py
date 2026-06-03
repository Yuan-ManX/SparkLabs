"""
SparkLabs Engine - Animation System

Comprehensive sprite animation, tween, and keyframe system for 2D and
UI-driven animation workflows. Provides animation clip authoring with
frame sequencing, tween-based property interpolation with dozens of
easing functions, and keyframe sequence evaluation. Manages playback
state, blending, and sprite-sheet-based animation generation.

Architecture:
  EngineAnimationSystem (Singleton)
    |-- AnimationFrame       — single frame with texture region, transform, tint, events
    |-- AnimationClip        — ordered frame sequence with playback control
    |-- TweenDefinition      — property interpolation with easing, delay, yoyo, callbacks
    |-- SequenceKeyframe     — individual point on a keyframe sequence
    |-- KeyframeSequence     — ordered keyframes with interpolation mode
    |-- AnimationPlayMode    (enum) — once, loop, ping_pong, clamp_forward
    |-- EasingFunction       (enum) — 16 easing curves for tween/keyframe interpolation
    |-- InterpolationMode    (enum) — linear, step, bezier, catmull_rom, hermite

Easing Functions:
  LINEAR, QUAD_IN, QUAD_OUT, QUAD_IN_OUT, CUBIC_IN, CUBIC_OUT,
  CUBIC_IN_OUT, ELASTIC_IN, ELASTIC_OUT, BOUNCE_OUT, BACK_IN,
  BACK_OUT, SINE_IN, SINE_OUT, EXPO_IN, EXPO_OUT
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class AnimationPlayMode(Enum):
    """Controls how an animation clip advances through its frame sequence.

    ONCE:          Plays once from first frame to last and stops.
    LOOP:          Repeats continuously from first to last frame.
    PING_PONG:     Alternates between forward and reverse playback.
    CLAMP_FORWARD: Plays once then holds the last frame indefinitely.
    """

    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    CLAMP_FORWARD = "clamp_forward"


class EasingFunction(Enum):
    """Easing curves for tween and keyframe interpolation.

    Standard easing functions following the Penner easing equations.
    IN variants accelerate from zero, OUT variants decelerate to zero,
    and IN_OUT variants combine both for smooth transitions.
    """

    LINEAR = "linear"
    QUAD_IN = "quad_in"
    QUAD_OUT = "quad_out"
    QUAD_IN_OUT = "quad_in_out"
    CUBIC_IN = "cubic_in"
    CUBIC_OUT = "cubic_out"
    CUBIC_IN_OUT = "cubic_in_out"
    ELASTIC_IN = "elastic_in"
    ELASTIC_OUT = "elastic_out"
    BOUNCE_OUT = "bounce_out"
    BACK_IN = "back_in"
    BACK_OUT = "back_out"
    SINE_IN = "sine_in"
    SINE_OUT = "sine_out"
    EXPO_IN = "expo_in"
    EXPO_OUT = "expo_out"


class InterpolationMode(Enum):
    """Interpolation strategy for evaluating values between keyframes.

    LINEAR:       Straight linear interpolation between values.
    STEP:         Holds the starting value until the next keyframe.
    BEZIER:       Cubic bezier curve interpolation with tangent control.
    CATMULL_ROM:  Smooth spline interpolation through all keyframe points.
    HERMITE:      Hermite spline interpolation with tangent vectors.
    """

    LINEAR = "linear"
    STEP = "step"
    BEZIER = "bezier"
    CATMULL_ROM = "catmull_rom"
    HERMITE = "hermite"


# ---------------------------------------------------------------------------
# Easing Function Implementations
# ---------------------------------------------------------------------------


def _apply_easing(t: float, easing: EasingFunction) -> float:
    """Apply the specified easing function to normalized time t in [0, 1]."""
    t = max(0.0, min(1.0, t))

    if easing == EasingFunction.LINEAR:
        return t

    elif easing == EasingFunction.QUAD_IN:
        return t * t

    elif easing == EasingFunction.QUAD_OUT:
        return 1.0 - (1.0 - t) * (1.0 - t)

    elif easing == EasingFunction.QUAD_IN_OUT:
        if t < 0.5:
            return 2.0 * t * t
        return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0

    elif easing == EasingFunction.CUBIC_IN:
        return t * t * t

    elif easing == EasingFunction.CUBIC_OUT:
        return 1.0 - (1.0 - t) ** 3

    elif easing == EasingFunction.CUBIC_IN_OUT:
        if t < 0.5:
            return 4.0 * t * t * t
        return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0

    elif easing == EasingFunction.ELASTIC_IN:
        if t == 0.0 or t == 1.0:
            return t
        return -(2.0 ** (10.0 * (t - 1.0))) * math.sin(
            (t - 1.0) * (2.0 * math.pi) / 0.4
        )

    elif easing == EasingFunction.ELASTIC_OUT:
        if t == 0.0 or t == 1.0:
            return t
        return (2.0 ** (-10.0 * t)) * math.sin(
            (t - 0.075) * (2.0 * math.pi) / 0.3
        ) + 1.0

    elif easing == EasingFunction.BOUNCE_OUT:
        if t < 1.0 / 2.75:
            return 7.5625 * t * t
        elif t < 2.0 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375

    elif easing == EasingFunction.BACK_IN:
        s = 1.70158
        return t * t * ((s + 1.0) * t - s)

    elif easing == EasingFunction.BACK_OUT:
        s = 1.70158
        t -= 1.0
        return t * t * ((s + 1.0) * t + s) + 1.0

    elif easing == EasingFunction.SINE_IN:
        return 1.0 - math.cos(t * math.pi / 2.0)

    elif easing == EasingFunction.SINE_OUT:
        return math.sin(t * math.pi / 2.0)

    elif easing == EasingFunction.EXPO_IN:
        if t == 0.0:
            return 0.0
        return 2.0 ** (10.0 * (t - 1.0))

    elif easing == EasingFunction.EXPO_OUT:
        if t == 1.0:
            return 1.0
        return 1.0 - 2.0 ** (-10.0 * t)

    return t


# ---------------------------------------------------------------------------
# Value Interpolation Helpers
# ---------------------------------------------------------------------------


def _lerp_scalar(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_tuple(a: Tuple, b: Tuple, t: float) -> Tuple:
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(min(len(a), len(b))))


def _lerp_value(a: Any, b: Any, t: float) -> Any:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return _lerp_scalar(float(a), float(b), t)
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return _lerp_tuple(tuple(a), tuple(b), t)
    if isinstance(a, bool) and isinstance(b, bool):
        return a if t < 0.5 else b
    if isinstance(a, str) and isinstance(b, str):
        return a if t < 0.5 else b
    return b if t >= 1.0 else a


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AnimationFrame:
    """A single frame within an animation clip.

    Defines the texture region, display duration, transform properties,
    color tint, and event triggers for one frame of a sprite animation.
    """

    frame_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    texture_region: str = "0,0,32,32"
    duration: float = 0.1
    anchor_point: Tuple[float, float] = (0.5, 0.5)
    scale: Tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0
    tint: Tuple[int, int, int, int] = (255, 255, 255, 255)
    event_triggers: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "texture_region": self.texture_region,
            "duration": self.duration,
            "anchor_point": list(self.anchor_point),
            "scale": list(self.scale),
            "rotation": self.rotation,
            "tint": list(self.tint),
            "event_triggers": list(self.event_triggers),
            "created_at": self.created_at,
        }


@dataclass
class AnimationClip:
    """A complete animation composed of an ordered sequence of frames.

    Stores frame data, playback configuration, and metadata tags for
    sprite-sheet-based animations. Supports looping, ping-pong, and
    one-shot playback modes.
    """

    clip_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    frames: List[AnimationFrame] = field(default_factory=list)
    frame_rate: float = 30.0
    loop: bool = False
    ping_pong: bool = False
    total_duration: float = 0.0
    sprite_sheet_id: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "frames": [f.to_dict() for f in self.frames],
            "frame_rate": self.frame_rate,
            "loop": self.loop,
            "ping_pong": self.ping_pong,
            "total_duration": self.total_duration,
            "sprite_sheet_id": self.sprite_sheet_id,
            "tags": list(self.tags),
            "frame_count": len(self.frames),
            "created_at": self.created_at,
        }


@dataclass
class TweenDefinition:
    """A property interpolation descriptor for tween-based animation.

    Defines start and end values, duration, easing curve, delay, and
    looping behavior. Supports yoyo (reverse on completion) and an
    on_complete callback identifier.
    """

    tween_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_id: str = ""
    property_name: str = ""
    from_value: Any = 0.0
    to_value: Any = 1.0
    duration: float = 0.5
    easing: EasingFunction = EasingFunction.LINEAR
    delay: float = 0.0
    loop: bool = False
    yoyo: bool = False
    on_complete: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tween_id": self.tween_id,
            "target_id": self.target_id,
            "property_name": self.property_name,
            "from_value": self.from_value,
            "to_value": self.to_value,
            "duration": self.duration,
            "easing": self.easing.value,
            "delay": self.delay,
            "loop": self.loop,
            "yoyo": self.yoyo,
            "on_complete": self.on_complete,
            "created_at": self.created_at,
        }


@dataclass
class SequenceKeyframe:
    """A single keyframe point within a keyframe sequence.

    Holds a time position, value, and optional per-keyframe easing
    override for fine-grained control over the interpolation curve.
    """

    keyframe_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    time: float = 0.0
    value: Any = 0.0
    easing: EasingFunction = EasingFunction.LINEAR
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyframe_id": self.keyframe_id,
            "time": self.time,
            "value": self.value,
            "easing": self.easing.value,
            "created_at": self.created_at,
        }


@dataclass
class KeyframeSequence:
    """An ordered sequence of keyframes evaluated against a target property.

    Supports multiple interpolation modes (linear, step, bezier,
    catmull-rom, hermite) and aggregates per-keyframe easing overrides
    for complex animation curves.
    """

    sequence_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    keyframes: List[SequenceKeyframe] = field(default_factory=list)
    interpolation: InterpolationMode = InterpolationMode.LINEAR
    target_property: str = ""
    duration: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "name": self.name,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
            "interpolation": self.interpolation.value,
            "target_property": self.target_property,
            "duration": self.duration,
            "keyframe_count": len(self.keyframes),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Pre-defined Animation Presets
# ---------------------------------------------------------------------------

_ANIMATION_PRESETS: Dict[str, Dict[str, Any]] = {
    "idle": {
        "name": "Idle",
        "frame_rate": 12.0,
        "loop": True,
        "ping_pong": False,
        "description": "Standard idle animation with subtle breathing motion",
        "tags": ["idle", "default", "stationary"],
    },
    "walk": {
        "name": "Walk",
        "frame_rate": 24.0,
        "loop": True,
        "ping_pong": False,
        "description": "Walking cycle animation",
        "tags": ["walk", "movement", "locomotion"],
    },
    "run": {
        "name": "Run",
        "frame_rate": 30.0,
        "loop": True,
        "ping_pong": False,
        "description": "Running cycle animation at higher frame rate",
        "tags": ["run", "movement", "locomotion"],
    },
    "jump": {
        "name": "Jump",
        "frame_rate": 24.0,
        "loop": False,
        "ping_pong": False,
        "description": "One-shot jump animation",
        "tags": ["jump", "movement", "one_shot"],
    },
    "attack": {
        "name": "Attack",
        "frame_rate": 30.0,
        "loop": False,
        "ping_pong": False,
        "description": "One-shot attack animation with event triggers",
        "tags": ["attack", "combat", "one_shot"],
    },
    "hurt": {
        "name": "Hurt",
        "frame_rate": 20.0,
        "loop": False,
        "ping_pong": False,
        "description": "Damage reaction animation",
        "tags": ["hurt", "combat", "one_shot", "reaction"],
    },
    "death": {
        "name": "Death",
        "frame_rate": 15.0,
        "loop": False,
        "ping_pong": False,
        "description": "Death animation, clamps on last frame",
        "tags": ["death", "combat", "one_shot", "final"],
    },
    "interact": {
        "name": "Interact",
        "frame_rate": 20.0,
        "loop": False,
        "ping_pong": False,
        "description": "Interaction animation for picking up or using objects",
        "tags": ["interact", "one_shot"],
    },
    "spawn": {
        "name": "Spawn",
        "frame_rate": 24.0,
        "loop": False,
        "ping_pong": False,
        "description": "Entity spawn/appear animation",
        "tags": ["spawn", "one_shot", "intro"],
    },
    "despawn": {
        "name": "Despawn",
        "frame_rate": 24.0,
        "loop": False,
        "ping_pong": False,
        "description": "Entity despawn/disappear animation",
        "tags": ["despawn", "one_shot", "outro"],
    },
    "float": {
        "name": "Float",
        "frame_rate": 12.0,
        "loop": True,
        "ping_pong": True,
        "description": "Gentle floating/bobbing animation with ping-pong",
        "tags": ["float", "idle", "ambient", "ping_pong"],
    },
    "spin": {
        "name": "Spin",
        "frame_rate": 30.0,
        "loop": True,
        "ping_pong": False,
        "description": "Continuous spinning rotation animation",
        "tags": ["spin", "rotation", "ambient"],
    },
}

# ---------------------------------------------------------------------------
# Pre-defined Tween Presets
# ---------------------------------------------------------------------------

_TWEEN_PRESETS: Dict[str, Dict[str, Any]] = {
    "fade_in": {
        "property_name": "opacity",
        "from_value": 0.0,
        "to_value": 1.0,
        "duration": 0.5,
        "easing": EasingFunction.QUAD_OUT,
        "description": "Fade in from transparent to fully opaque",
    },
    "fade_out": {
        "property_name": "opacity",
        "from_value": 1.0,
        "to_value": 0.0,
        "duration": 0.5,
        "easing": EasingFunction.QUAD_IN,
        "description": "Fade out from fully opaque to transparent",
    },
    "scale_up": {
        "property_name": "scale",
        "from_value": (0.0, 0.0),
        "to_value": (1.0, 1.0),
        "duration": 0.4,
        "easing": EasingFunction.BACK_OUT,
        "description": "Scale up with overshoot bounce",
    },
    "scale_down": {
        "property_name": "scale",
        "from_value": (1.0, 1.0),
        "to_value": (0.0, 0.0),
        "duration": 0.3,
        "easing": EasingFunction.BACK_IN,
        "description": "Scale down to zero with overshoot",
    },
    "slide_in_left": {
        "property_name": "position",
        "from_value": (-200.0, 0.0),
        "to_value": (0.0, 0.0),
        "duration": 0.5,
        "easing": EasingFunction.QUAD_OUT,
        "description": "Slide in from the left",
    },
    "slide_in_right": {
        "property_name": "position",
        "from_value": (200.0, 0.0),
        "to_value": (0.0, 0.0),
        "duration": 0.5,
        "easing": EasingFunction.QUAD_OUT,
        "description": "Slide in from the right",
    },
    "slide_in_top": {
        "property_name": "position",
        "from_value": (0.0, -200.0),
        "to_value": (0.0, 0.0),
        "duration": 0.5,
        "easing": EasingFunction.QUAD_OUT,
        "description": "Slide in from the top",
    },
    "slide_in_bottom": {
        "property_name": "position",
        "from_value": (0.0, 200.0),
        "to_value": (0.0, 0.0),
        "duration": 0.5,
        "easing": EasingFunction.QUAD_OUT,
        "description": "Slide in from the bottom",
    },
    "bounce": {
        "property_name": "scale",
        "from_value": (1.0, 1.0),
        "to_value": (1.2, 1.2),
        "duration": 0.6,
        "easing": EasingFunction.BOUNCE_OUT,
        "yoyo": True,
        "description": "Bounce scale effect with yoyo return",
    },
    "wobble": {
        "property_name": "rotation",
        "from_value": -5.0,
        "to_value": 5.0,
        "duration": 0.3,
        "easing": EasingFunction.SINE_IN,
        "loop": True,
        "yoyo": True,
        "description": "Continuous wobbling rotation",
    },
    "pulse": {
        "property_name": "scale",
        "from_value": (1.0, 1.0),
        "to_value": (1.05, 1.05),
        "duration": 0.8,
        "easing": EasingFunction.SINE_IN,
        "loop": True,
        "yoyo": True,
        "description": "Continuous subtle pulsing scale",
    },
    "flash": {
        "property_name": "tint",
        "from_value": (255, 255, 255, 255),
        "to_value": (255, 100, 100, 255),
        "duration": 0.15,
        "easing": EasingFunction.LINEAR,
        "yoyo": True,
        "description": "Quick red flash effect",
    },
    "elastic_pop": {
        "property_name": "scale",
        "from_value": (0.5, 0.5),
        "to_value": (1.0, 1.0),
        "duration": 0.8,
        "easing": EasingFunction.ELASTIC_OUT,
        "description": "Elastic pop-in with oscillation",
    },
    "shake": {
        "property_name": "position",
        "from_value": (0.0, 0.0),
        "to_value": (6.0, 0.0),
        "duration": 0.5,
        "easing": EasingFunction.LINEAR,
        "loop": False,
        "yoyo": True,
        "description": "Horizontal shake effect",
    },
}


# ---------------------------------------------------------------------------
# EngineAnimationSystem (Singleton)
# ---------------------------------------------------------------------------


class EngineAnimationSystem:
    """Comprehensive sprite animation, tween, and keyframe system.

    Manages the full lifecycle of animation clips, tween interpolations,
    and keyframe sequences. Provides playback control, blending between
    clips, sprite-sheet-based animation generation, and real-time
    animation state tracking.

    Usage:
        anim_sys = get_animation_system()
        clip_id = anim_sys.create_animation_clip("walk", frame_rate=24.0, loop=True)
        anim_sys.add_frame_to_clip(clip_id, "0,0,32,32", 0.1)
        tween_id = anim_sys.create_tween("player", "position", (0,0), (100,0), 0.5,
                                         easing="quad_out")
        anim_sys.play_animation(clip_id, mode="loop")
        anim_sys.update_animations(0.016)
        state = anim_sys.get_animation_state(clip_id)
    """

    _instance: Optional["EngineAnimationSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_CLIPS: int = 2048
    MAX_TWEENS: int = 8192
    MAX_SEQUENCES: int = 1024
    MAX_FRAMES_PER_CLIP: int = 512
    MAX_KEYFRAMES_PER_SEQUENCE: int = 256

    def __new__(cls) -> "EngineAnimationSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._clips: Dict[str, AnimationClip] = {}
        self._tweens: Dict[str, TweenDefinition] = {}
        self._sequences: Dict[str, KeyframeSequence] = {}
        self._playback_states: Dict[str, Dict[str, Any]] = {}
        self._animation_presets: Dict[str, Dict[str, Any]] = dict(_ANIMATION_PRESETS)
        self._tween_presets: Dict[str, Dict[str, Any]] = dict(_TWEEN_PRESETS)
        self._total_clips_created: int = 0
        self._total_tweens_created: int = 0
        self._total_sequences_created: int = 0
        self._total_frames_added: int = 0
        self._global_time: float = 0.0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EngineAnimationSystem":
        return cls()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _get_clip(self, clip_id: str) -> AnimationClip:
        _time_module.sleep(0.001)
        if clip_id not in self._clips:
            raise KeyError(f"AnimationClip '{clip_id}' does not exist")
        return self._clips[clip_id]

    def _get_tween(self, tween_id: str) -> TweenDefinition:
        _time_module.sleep(0.001)
        if tween_id not in self._tweens:
            raise KeyError(f"TweenDefinition '{tween_id}' does not exist")
        return self._tweens[tween_id]

    def _get_sequence(self, sequence_id: str) -> KeyframeSequence:
        _time_module.sleep(0.001)
        if sequence_id not in self._sequences:
            raise KeyError(f"KeyframeSequence '{sequence_id}' does not exist")
        return self._sequences[sequence_id]

    def _ensure_playback_state(self, clip_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        if clip_id not in self._playback_states:
            self._playback_states[clip_id] = {
                "is_playing": False,
                "is_paused": False,
                "current_time": 0.0,
                "current_frame_index": 0,
                "play_mode": "once",
                "speed": 1.0,
                "direction": 1,
                "started_at": 0.0,
            }
        return self._playback_states[clip_id]

    def _resolve_easing(self, easing: Union[str, EasingFunction]) -> EasingFunction:
        _time_module.sleep(0.001)
        if isinstance(easing, EasingFunction):
            return easing
        try:
            return EasingFunction(easing.lower())
        except ValueError:
            return EasingFunction.LINEAR

    def _resolve_interpolation(
        self, interpolation: Union[str, InterpolationMode]
    ) -> InterpolationMode:
        _time_module.sleep(0.001)
        if isinstance(interpolation, InterpolationMode):
            return interpolation
        try:
            return InterpolationMode(interpolation.lower())
        except ValueError:
            return InterpolationMode.LINEAR

    def _resolve_play_mode(self, mode: Union[str, AnimationPlayMode]) -> AnimationPlayMode:
        _time_module.sleep(0.001)
        if isinstance(mode, AnimationPlayMode):
            return mode
        try:
            return AnimationPlayMode(mode.lower())
        except ValueError:
            return AnimationPlayMode.ONCE

    def _compute_total_duration(self, clip: AnimationClip) -> float:
        _time_module.sleep(0.001)
        if not clip.frames:
            return 0.0
        if clip.frame_rate > 0.0:
            return len(clip.frames) / clip.frame_rate
        return sum(f.duration for f in clip.frames)

    def _get_frame_at_time(self, clip: AnimationClip, time: float) -> int:
        _time_module.sleep(0.001)
        if not clip.frames:
            return -1
        total = self._compute_total_duration(clip)
        if total <= 0.0:
            return 0
        ratio = min(time / total, 1.0) if time >= 0 else 0.0
        return min(int(ratio * len(clip.frames)), len(clip.frames) - 1)

    # ------------------------------------------------------------------
    # Animation Clip Creation and Management
    # ------------------------------------------------------------------

    def create_animation_clip(
        self,
        name: str,
        frame_rate: float = 30.0,
        loop: bool = False,
        ping_pong: bool = False,
        sprite_sheet_id: str = "",
        tags: Optional[List[str]] = None,
    ) -> AnimationClip:
        """Create a new animation clip and register it in the system.

        Args:
            name: Human-readable name for the clip.
            frame_rate: Frames per second for playback timing.
            loop: Whether the clip repeats after reaching the end.
            ping_pong: Whether to reverse direction at boundaries.
            sprite_sheet_id: Associated sprite sheet resource identifier.
            tags: Optional list of semantic tags for filtering.

        Returns:
            The newly created AnimationClip dataclass instance.
        """
        _time_module.sleep(0.001)
        if len(self._clips) >= self.MAX_CLIPS:
            raise RuntimeError(f"AnimationClip limit reached ({self.MAX_CLIPS})")

        clip = AnimationClip(
            name=name,
            frame_rate=max(frame_rate, 0.01),
            loop=loop,
            ping_pong=ping_pong,
            sprite_sheet_id=sprite_sheet_id,
            tags=tags or [],
        )
        self._clips[clip.clip_id] = clip
        self._total_clips_created += 1
        return clip

    def add_frame_to_clip(
        self,
        clip_id: str,
        texture_region: str,
        duration: float = 0.1,
        anchor_point: Tuple[float, float] = (0.5, 0.5),
        scale: Tuple[float, float] = (1.0, 1.0),
        rotation: float = 0.0,
        tint: Tuple[int, int, int, int] = (255, 255, 255, 255),
        event_triggers: Optional[List[str]] = None,
    ) -> Optional[AnimationFrame]:
        """Add a frame to an existing animation clip.

        Args:
            clip_id: The target clip identifier.
            texture_region: String describing the texture sub-rectangle.
            duration: Display duration for this frame in seconds.
            anchor_point: Normalized anchor point (x, y).
            scale: Scale multipliers (x, y).
            rotation: Rotation in degrees.
            tint: RGBA color tint tuple.
            event_triggers: List of event names to fire when this frame activates.

        Returns:
            The created AnimationFrame, or None if the clip does not exist
            or the frame limit has been reached.
        """
        _time_module.sleep(0.001)
        clip = self._clips.get(clip_id)
        if clip is None:
            return None
        if len(clip.frames) >= self.MAX_FRAMES_PER_CLIP:
            return None

        frame = AnimationFrame(
            texture_region=texture_region,
            duration=max(duration, 0.001),
            anchor_point=anchor_point,
            scale=scale,
            rotation=rotation,
            tint=tint,
            event_triggers=event_triggers or [],
        )
        clip.frames.append(frame)
        clip.total_duration = self._compute_total_duration(clip)
        self._total_frames_added += 1
        return frame

    def remove_frame_from_clip(self, clip_id: str, frame_id: str) -> bool:
        """Remove a frame from an animation clip by frame identifier.

        Args:
            clip_id: The target clip identifier.
            frame_id: The frame identifier to remove.

        Returns:
            True if the frame was found and removed, False otherwise.
        """
        _time_module.sleep(0.001)
        clip = self._clips.get(clip_id)
        if clip is None:
            return False
        for i, frame in enumerate(clip.frames):
            if frame.frame_id == frame_id:
                clip.frames.pop(i)
                clip.total_duration = self._compute_total_duration(clip)
                return True
        return False

    def get_clip(self, clip_id: str) -> Optional[AnimationClip]:
        """Retrieve an animation clip by its identifier.

        Args:
            clip_id: The clip identifier.

        Returns:
            The AnimationClip if found, None otherwise.
        """
        _time_module.sleep(0.001)
        return self._clips.get(clip_id)

    def get_clip_by_name(self, name: str) -> Optional[AnimationClip]:
        """Retrieve the first animation clip matching the given name.

        Args:
            name: The clip name to search for.

        Returns:
            The first matching AnimationClip, or None.
        """
        _time_module.sleep(0.001)
        for clip in self._clips.values():
            if clip.name == name:
                return clip
        return None

    def list_clips(self) -> List[AnimationClip]:
        """Return all registered animation clips.

        Returns:
            A list of all AnimationClip instances.
        """
        _time_module.sleep(0.001)
        return list(self._clips.values())

    def remove_clip(self, clip_id: str) -> bool:
        """Remove an animation clip and its playback state.

        Args:
            clip_id: The clip identifier to remove.

        Returns:
            True if the clip was removed, False if not found.
        """
        _time_module.sleep(0.001)
        if clip_id in self._clips:
            del self._clips[clip_id]
            self._playback_states.pop(clip_id, None)
            return True
        return False

    # ------------------------------------------------------------------
    # Sprite Sheet Animation Generation
    # ------------------------------------------------------------------

    def create_sprite_sheet_animation(
        self,
        name: str,
        sprite_sheet_id: str,
        columns: int,
        rows: int,
        frame_width: int,
        frame_height: int,
        frame_duration: float = 0.1,
        frame_rate: float = 30.0,
        loop: bool = True,
        ping_pong: bool = False,
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> AnimationClip:
        """Create an animation clip by scanning a sprite sheet grid.

        Automatically generates an AnimationFrame for each cell in the
        sprite sheet grid layout, computing texture regions from the
        column/row positions and frame dimensions.

        Args:
            name: Human-readable name for the clip.
            sprite_sheet_id: Identifier of the source sprite sheet resource.
            columns: Number of columns in the sprite sheet grid.
            rows: Number of rows in the sprite sheet grid.
            frame_width: Width of each frame in pixels.
            frame_height: Height of each frame in pixels.
            frame_duration: Duration per frame in seconds.
            frame_rate: Target playback frame rate.
            loop: Whether the clip repeats.
            ping_pong: Whether to ping-pong at boundaries.
            start_frame: Index of the first frame to include (0-based).
            end_frame: Index of the last frame to include (exclusive),
                       or None to include all remaining frames.
            tags: Optional semantic tags for the clip.

        Returns:
            The generated AnimationClip with all frames populated.
        """
        _time_module.sleep(0.001)
        if len(self._clips) >= self.MAX_CLIPS:
            raise RuntimeError(f"AnimationClip limit reached ({self.MAX_CLIPS})")

        total_frames = columns * rows
        actual_end = end_frame if end_frame is not None else total_frames
        actual_end = min(actual_end, total_frames)
        start_frame = max(0, min(start_frame, actual_end - 1))

        clip = AnimationClip(
            name=name,
            frame_rate=max(frame_rate, 0.01),
            loop=loop,
            ping_pong=ping_pong,
            sprite_sheet_id=sprite_sheet_id,
            tags=tags or [],
        )

        frame_count = 0
        for idx in range(start_frame, actual_end):
            if frame_count >= self.MAX_FRAMES_PER_CLIP:
                break
            col = idx % columns
            row = idx // columns
            x = col * frame_width
            y = row * frame_height
            region = f"{x},{y},{frame_width},{frame_height}"
            frame = AnimationFrame(
                texture_region=region,
                duration=max(frame_duration, 0.001),
            )
            clip.frames.append(frame)
            frame_count += 1

        clip.total_duration = self._compute_total_duration(clip)
        self._clips[clip.clip_id] = clip
        self._total_clips_created += 1
        self._total_frames_added += frame_count
        return clip

    def create_animation_from_preset(
        self, preset_name: str
    ) -> Optional[AnimationClip]:
        """Create an animation clip from a named preset configuration.

        Args:
            preset_name: The preset key (e.g. 'idle', 'walk', 'run').

        Returns:
            The created AnimationClip, or None if the preset is not found.
        """
        _time_module.sleep(0.001)
        preset = self._animation_presets.get(preset_name)
        if preset is None:
            return None
        return self.create_animation_clip(
            name=preset["name"],
            frame_rate=preset["frame_rate"],
            loop=preset["loop"],
            ping_pong=preset["ping_pong"],
            tags=preset.get("tags", []),
        )

    def list_animation_presets(self) -> List[str]:
        """Return the list of available animation preset names.

        Returns:
            Sorted list of preset key strings.
        """
        _time_module.sleep(0.001)
        return sorted(self._animation_presets.keys())

    # ------------------------------------------------------------------
    # Animation Playback Control
    # ------------------------------------------------------------------

    def play_animation(
        self,
        clip_id: str,
        mode: Union[str, AnimationPlayMode] = "once",
        speed: float = 1.0,
        start_time: float = 0.0,
    ) -> bool:
        """Start or restart playback of an animation clip.

        Args:
            clip_id: The clip to play.
            mode: Playback mode ('once', 'loop', 'ping_pong', 'clamp_forward').
            speed: Playback speed multiplier (1.0 = normal).
            start_time: Time offset in seconds to start playback from.

        Returns:
            True if playback started successfully, False if clip not found.
        """
        _time_module.sleep(0.001)
        clip = self._clips.get(clip_id)
        if clip is None:
            return False

        resolved_mode = self._resolve_play_mode(mode)
        state = self._ensure_playback_state(clip_id)
        state["is_playing"] = True
        state["is_paused"] = False
        state["current_time"] = max(0.0, start_time)
        state["current_frame_index"] = self._get_frame_at_time(clip, start_time)
        state["play_mode"] = resolved_mode.value
        state["speed"] = max(speed, 0.001)
        state["direction"] = 1
        state["started_at"] = self._global_time
        return True

    def stop_animation(self, clip_id: str) -> bool:
        """Stop playback of an animation clip and reset to the first frame.

        Args:
            clip_id: The clip to stop.

        Returns:
            True if the clip exists, False otherwise.
        """
        _time_module.sleep(0.001)
        if clip_id not in self._clips:
            return False
        state = self._ensure_playback_state(clip_id)
        state["is_playing"] = False
        state["is_paused"] = False
        state["current_time"] = 0.0
        state["current_frame_index"] = 0
        state["direction"] = 1
        return True

    def pause_animation(self, clip_id: str) -> bool:
        """Pause playback of an animation clip without resetting position.

        Args:
            clip_id: The clip to pause.

        Returns:
            True if the clip exists, False otherwise.
        """
        _time_module.sleep(0.001)
        if clip_id not in self._clips:
            return False
        state = self._ensure_playback_state(clip_id)
        if state["is_playing"]:
            state["is_paused"] = True
            state["is_playing"] = False
        return True

    def resume_animation(self, clip_id: str) -> bool:
        """Resume a paused animation clip from its current position.

        Args:
            clip_id: The clip to resume.

        Returns:
            True if the clip exists, False otherwise.
        """
        _time_module.sleep(0.001)
        if clip_id not in self._clips:
            return False
        state = self._ensure_playback_state(clip_id)
        if state["is_paused"]:
            state["is_paused"] = False
            state["is_playing"] = True
        return True

    def seek_animation(self, clip_id: str, time: float) -> bool:
        """Seek to a specific time position in the animation clip.

        Args:
            clip_id: The target clip.
            time: Time in seconds to seek to.

        Returns:
            True if the clip exists, False otherwise.
        """
        _time_module.sleep(0.001)
        clip = self._clips.get(clip_id)
        if clip is None:
            return False
        state = self._ensure_playback_state(clip_id)
        total = self._compute_total_duration(clip)
        state["current_time"] = max(0.0, min(time, total))
        state["current_frame_index"] = self._get_frame_at_time(
            clip, state["current_time"]
        )
        return True

    def set_animation_speed(self, clip_id: str, speed: float) -> bool:
        """Set the playback speed multiplier for an animation clip.

        Args:
            clip_id: The target clip.
            speed: New speed multiplier (1.0 = normal).

        Returns:
            True if the clip exists, False otherwise.
        """
        _time_module.sleep(0.001)
        if clip_id not in self._clips:
            return False
        state = self._ensure_playback_state(clip_id)
        state["speed"] = max(speed, 0.001)
        return True

    def get_animation_state(self, clip_id: str) -> Dict[str, Any]:
        """Return the current playback state of an animation clip.

        Args:
            clip_id: The target clip.

        Returns:
            A dictionary with playback state including current time,
            frame index, playing status, mode, and speed.
        """
        _time_module.sleep(0.001)
        clip = self._clips.get(clip_id)
        if clip is None:
            return {
                "exists": False,
                "clip_id": clip_id,
                "is_playing": False,
                "is_paused": False,
                "current_time": 0.0,
                "current_frame_index": 0,
                "total_duration": 0.0,
                "frame_count": 0,
                "play_mode": "once",
                "speed": 1.0,
                "direction": 1,
            }

        state = self._ensure_playback_state(clip_id)
        total = self._compute_total_duration(clip)
        return {
            "exists": True,
            "clip_id": clip_id,
            "name": clip.name,
            "is_playing": state["is_playing"],
            "is_paused": state["is_paused"],
            "current_time": round(state["current_time"], 4),
            "current_frame_index": state["current_frame_index"],
            "total_duration": round(total, 4),
            "frame_count": len(clip.frames),
            "play_mode": state["play_mode"],
            "speed": state["speed"],
            "direction": state["direction"],
            "loop": clip.loop,
            "ping_pong": clip.ping_pong,
            "frame_rate": clip.frame_rate,
            "tags": list(clip.tags),
        }

    def get_current_frame(self, clip_id: str) -> Optional[AnimationFrame]:
        """Get the current active frame of a playing animation clip.

        Args:
            clip_id: The target clip.

        Returns:
            The current AnimationFrame, or None if the clip has no frames
            or does not exist.
        """
        _time_module.sleep(0.001)
        clip = self._clips.get(clip_id)
        if clip is None or not clip.frames:
            return None
        state = self._ensure_playback_state(clip_id)
        idx = state["current_frame_index"]
        if 0 <= idx < len(clip.frames):
            return clip.frames[idx]
        return None

    # ------------------------------------------------------------------
    # Animation Update
    # ------------------------------------------------------------------

    def update_animations(self, delta_time: float) -> Dict[str, List[str]]:
        """Advance all playing animations by the given delta time.

        Evaluates each active animation clip's playback state, advances
        the current time, handles looping and ping-pong boundaries, and
        fires frame-level event triggers.

        Args:
            delta_time: Time elapsed since last update in seconds.

        Returns:
            A dictionary mapping clip_id to a list of event trigger
            names that fired during this update tick.
        """
        _time_module.sleep(0.001)
        self._global_time += delta_time
        triggered_events: Dict[str, List[str]] = {}

        for clip_id, clip in list(self._clips.items()):
            state = self._playback_states.get(clip_id)
            if state is None or not state["is_playing"]:
                continue
            if state["is_paused"]:
                continue

            total = self._compute_total_duration(clip)
            if total <= 0.0:
                state["is_playing"] = False
                continue

            dt = delta_time * state["speed"]
            state["current_time"] += dt * state["direction"]

            previous_frame = state["current_frame_index"]
            mode = state["play_mode"]

            if mode == AnimationPlayMode.ONCE.value:
                if state["current_time"] >= total:
                    state["current_time"] = total
                    state["current_frame_index"] = len(clip.frames) - 1
                    state["is_playing"] = False
                elif state["current_time"] < 0.0:
                    state["current_time"] = 0.0
                    state["current_frame_index"] = 0
                else:
                    state["current_frame_index"] = self._get_frame_at_time(
                        clip, state["current_time"]
                    )

            elif mode == AnimationPlayMode.LOOP.value:
                while state["current_time"] >= total:
                    state["current_time"] -= total
                while state["current_time"] < 0.0:
                    state["current_time"] += total
                state["current_frame_index"] = self._get_frame_at_time(
                    clip, state["current_time"]
                )

            elif mode == AnimationPlayMode.PING_PONG.value:
                if state["current_time"] >= total:
                    state["current_time"] = total
                    state["direction"] = -1
                elif state["current_time"] <= 0.0:
                    state["current_time"] = 0.0
                    if clip.loop:
                        state["direction"] = 1
                    else:
                        state["is_playing"] = False
                state["current_frame_index"] = self._get_frame_at_time(
                    clip, state["current_time"]
                )

            elif mode == AnimationPlayMode.CLAMP_FORWARD.value:
                if state["current_time"] >= total:
                    state["current_time"] = total
                    state["current_frame_index"] = len(clip.frames) - 1
                    state["is_playing"] = False
                elif state["current_time"] < 0.0:
                    state["current_time"] = 0.0
                    state["current_frame_index"] = 0
                else:
                    state["current_frame_index"] = self._get_frame_at_time(
                        clip, state["current_time"]
                    )

            if state["current_frame_index"] != previous_frame:
                frame = clip.frames[state["current_frame_index"]] if 0 <= state["current_frame_index"] < len(clip.frames) else None
                if frame and frame.event_triggers:
                    triggered_events[clip_id] = list(frame.event_triggers)

        return triggered_events

    # ------------------------------------------------------------------
    # Tween System
    # ------------------------------------------------------------------

    def create_tween(
        self,
        target_id: str,
        property_name: str,
        from_value: Any,
        to_value: Any,
        duration: float = 0.5,
        easing: Union[str, EasingFunction] = "linear",
        delay: float = 0.0,
        loop: bool = False,
        yoyo: bool = False,
        on_complete: str = "",
    ) -> TweenDefinition:
        """Create a new tween definition for property interpolation.

        Args:
            target_id: Identifier of the target entity or object.
            property_name: Name of the property to animate.
            from_value: Starting value of the interpolation.
            to_value: Ending value of the interpolation.
            duration: Total duration of the tween in seconds.
            easing: Easing function name or enum value.
            delay: Delay before the tween starts in seconds.
            loop: Whether the tween repeats after completion.
            yoyo: Whether to reverse direction on completion.
            on_complete: Callback identifier string to invoke on completion.

        Returns:
            The newly created TweenDefinition.
        """
        _time_module.sleep(0.001)
        if len(self._tweens) >= self.MAX_TWEENS:
            raise RuntimeError(f"Tween limit reached ({self.MAX_TWEENS})")

        resolved_easing = self._resolve_easing(easing)
        tween = TweenDefinition(
            target_id=target_id,
            property_name=property_name,
            from_value=from_value,
            to_value=to_value,
            duration=max(duration, 0.001),
            easing=resolved_easing,
            delay=max(delay, 0.0),
            loop=loop,
            yoyo=yoyo,
            on_complete=on_complete,
        )
        self._tweens[tween.tween_id] = tween
        self._total_tweens_created += 1
        return tween

    def create_tween_from_preset(
        self,
        target_id: str,
        preset_name: str,
        from_value: Optional[Any] = None,
        to_value: Optional[Any] = None,
    ) -> Optional[TweenDefinition]:
        """Create a tween from a named preset configuration.

        Args:
            target_id: Identifier of the target entity or object.
            preset_name: The preset key (e.g. 'fade_in', 'scale_up').
            from_value: Optional override for the starting value.
            to_value: Optional override for the ending value.

        Returns:
            The created TweenDefinition, or None if preset not found.
        """
        _time_module.sleep(0.001)
        preset = self._tween_presets.get(preset_name)
        if preset is None:
            return None
        return self.create_tween(
            target_id=target_id,
            property_name=preset["property_name"],
            from_value=from_value if from_value is not None else preset["from_value"],
            to_value=to_value if to_value is not None else preset["to_value"],
            duration=preset["duration"],
            easing=preset["easing"],
            loop=preset.get("loop", False),
            yoyo=preset.get("yoyo", False),
        )

    def get_tween(self, tween_id: str) -> Optional[TweenDefinition]:
        """Retrieve a tween definition by its identifier.

        Args:
            tween_id: The tween identifier.

        Returns:
            The TweenDefinition if found, None otherwise.
        """
        _time_module.sleep(0.001)
        return self._tweens.get(tween_id)

    def evaluate_tween(
        self, tween_id: str, elapsed_time: float
    ) -> Optional[Any]:
        """Evaluate a tween at the given elapsed time and return the interpolated value.

        Args:
            tween_id: The tween to evaluate.
            elapsed_time: Time elapsed since the tween started in seconds.

        Returns:
            The interpolated value, or None if the tween does not exist.
        """
        _time_module.sleep(0.001)
        tween = self._tweens.get(tween_id)
        if tween is None:
            return None

        effective_time = elapsed_time - tween.delay
        if effective_time < 0.0:
            return tween.from_value

        cycle_duration = tween.duration
        if cycle_duration <= 0.0:
            return tween.to_value

        if tween.loop:
            full_cycles = int(effective_time / cycle_duration)
            remainder = effective_time % cycle_duration
            if tween.yoyo and full_cycles % 2 == 1:
                remainder = cycle_duration - remainder
            t = max(0.0, min(1.0, remainder / cycle_duration))
        else:
            if effective_time >= cycle_duration:
                if tween.yoyo:
                    t = 0.0
                else:
                    return tween.to_value
            else:
                t = effective_time / cycle_duration

        eased = _apply_easing(t, tween.easing)
        if tween.yoyo and not tween.loop and effective_time >= cycle_duration:
            return _lerp_value(tween.to_value, tween.from_value, eased)
        return _lerp_value(tween.from_value, tween.to_value, eased)

    def remove_tween(self, tween_id: str) -> bool:
        """Remove a tween definition from the system.

        Args:
            tween_id: The tween to remove.

        Returns:
            True if removed, False if not found.
        """
        _time_module.sleep(0.001)
        if tween_id in self._tweens:
            del self._tweens[tween_id]
            return True
        return False

    def list_tweens(self) -> List[TweenDefinition]:
        """Return all registered tween definitions.

        Returns:
            A list of all TweenDefinition instances.
        """
        _time_module.sleep(0.001)
        return list(self._tweens.values())

    def list_tween_presets(self) -> List[str]:
        """Return the list of available tween preset names.

        Returns:
            Sorted list of preset key strings.
        """
        _time_module.sleep(0.001)
        return sorted(self._tween_presets.keys())

    # ------------------------------------------------------------------
    # Keyframe Sequence System
    # ------------------------------------------------------------------

    def create_keyframe_sequence(
        self,
        name: str,
        target_property: str = "",
        interpolation: Union[str, InterpolationMode] = "linear",
    ) -> KeyframeSequence:
        """Create a new keyframe sequence for property animation.

        Args:
            name: Human-readable name for the sequence.
            target_property: Name of the property the sequence targets.
            interpolation: Default interpolation mode for the sequence.

        Returns:
            The newly created KeyframeSequence.
        """
        _time_module.sleep(0.001)
        if len(self._sequences) >= self.MAX_SEQUENCES:
            raise RuntimeError(
                f"KeyframeSequence limit reached ({self.MAX_SEQUENCES})"
            )

        resolved_interp = self._resolve_interpolation(interpolation)
        sequence = KeyframeSequence(
            name=name,
            target_property=target_property,
            interpolation=resolved_interp,
        )
        self._sequences[sequence.sequence_id] = sequence
        self._total_sequences_created += 1
        return sequence

    def add_keyframe_to_sequence(
        self,
        sequence_id: str,
        time: float,
        value: Any,
        easing: Union[str, EasingFunction] = "linear",
    ) -> Optional[SequenceKeyframe]:
        """Add a keyframe point to an existing keyframe sequence.

        Args:
            sequence_id: The target sequence identifier.
            time: Time position of the keyframe in seconds.
            value: Value at this keyframe.
            easing: Per-keyframe easing override.

        Returns:
            The created SequenceKeyframe, or None if the sequence
            does not exist or the keyframe limit is reached.
        """
        _time_module.sleep(0.001)
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return None
        if len(sequence.keyframes) >= self.MAX_KEYFRAMES_PER_SEQUENCE:
            return None

        resolved_easing = self._resolve_easing(easing)
        kf = SequenceKeyframe(
            time=time,
            value=value,
            easing=resolved_easing,
        )
        sequence.keyframes.append(kf)
        sequence.keyframes.sort(key=lambda k: k.time)
        sequence.duration = (
            sequence.keyframes[-1].time if sequence.keyframes else 0.0
        )
        return kf

    def remove_keyframe_from_sequence(
        self, sequence_id: str, keyframe_id: str
    ) -> bool:
        """Remove a keyframe from a sequence by its identifier.

        Args:
            sequence_id: The target sequence identifier.
            keyframe_id: The keyframe identifier to remove.

        Returns:
            True if removed, False otherwise.
        """
        _time_module.sleep(0.001)
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return False
        for i, kf in enumerate(sequence.keyframes):
            if kf.keyframe_id == keyframe_id:
                sequence.keyframes.pop(i)
                sequence.duration = (
                    sequence.keyframes[-1].time if sequence.keyframes else 0.0
                )
                return True
        return False

    def evaluate_sequence(
        self, sequence_id: str, time: float
    ) -> Optional[Any]:
        """Evaluate a keyframe sequence at the given time.

        Args:
            sequence_id: The sequence to evaluate.
            time: Time in seconds to evaluate at.

        Returns:
            The interpolated value, or None if the sequence is not found
            or has no keyframes.
        """
        _time_module.sleep(0.001)
        sequence = self._sequences.get(sequence_id)
        if sequence is None or not sequence.keyframes:
            return None

        kfs = sequence.keyframes
        if len(kfs) == 1:
            return kfs[0].value

        if time <= kfs[0].time:
            return kfs[0].value

        if time >= kfs[-1].time:
            return kfs[-1].value

        for i in range(len(kfs) - 1):
            curr = kfs[i]
            nxt = kfs[i + 1]
            if curr.time <= time <= nxt.time:
                seg_duration = nxt.time - curr.time
                if seg_duration <= 0.0:
                    return nxt.value

                raw_t = (time - curr.time) / seg_duration

                if sequence.interpolation == InterpolationMode.STEP:
                    return curr.value

                if sequence.interpolation == InterpolationMode.BEZIER:
                    eased = raw_t * raw_t * (3.0 - 2.0 * raw_t)
                else:
                    eased = _apply_easing(raw_t, curr.easing)

                return _lerp_value(curr.value, nxt.value, eased)

        return kfs[-1].value

    def evaluate_sequence_normalized(
        self, sequence_id: str, t: float
    ) -> Optional[Any]:
        """Evaluate a keyframe sequence using normalized time [0, 1].

        Args:
            sequence_id: The sequence to evaluate.
            t: Normalized time in range [0, 1].

        Returns:
            The interpolated value, or None if not found.
        """
        _time_module.sleep(0.001)
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return None
        return self.evaluate_sequence(sequence_id, t * max(sequence.duration, 0.0001))

    def get_sequence(self, sequence_id: str) -> Optional[KeyframeSequence]:
        """Retrieve a keyframe sequence by its identifier.

        Args:
            sequence_id: The sequence identifier.

        Returns:
            The KeyframeSequence if found, None otherwise.
        """
        _time_module.sleep(0.001)
        return self._sequences.get(sequence_id)

    def remove_sequence(self, sequence_id: str) -> bool:
        """Remove a keyframe sequence from the system.

        Args:
            sequence_id: The sequence to remove.

        Returns:
            True if removed, False otherwise.
        """
        _time_module.sleep(0.001)
        if sequence_id in self._sequences:
            del self._sequences[sequence_id]
            return True
        return False

    def list_sequences(self) -> List[KeyframeSequence]:
        """Return all registered keyframe sequences.

        Returns:
            A list of all KeyframeSequence instances.
        """
        _time_module.sleep(0.001)
        return list(self._sequences.values())

    # ------------------------------------------------------------------
    # Animation Blending
    # ------------------------------------------------------------------

    def blend_animations(
        self,
        clip_id_a: str,
        clip_id_b: str,
        blend_factor: float,
        blend_name: Optional[str] = None,
    ) -> Optional[AnimationClip]:
        """Create a new animation clip by blending two source clips.

        Interpolates frame properties (scale, rotation, tint, anchor_point)
        between corresponding frames of the two source clips. The resulting
        clip uses the frame count and timing of the longer clip.

        Args:
            clip_id_a: First source clip identifier.
            clip_id_b: Second source clip identifier.
            blend_factor: Blend weight in [0, 1]. 0.0 = fully clip_a,
                          1.0 = fully clip_b.
            blend_name: Optional name for the blended clip.

        Returns:
            The blended AnimationClip, or None if either source clip
            is not found or has no frames.
        """
        _time_module.sleep(0.001)
        if len(self._clips) >= self.MAX_CLIPS:
            raise RuntimeError(f"AnimationClip limit reached ({self.MAX_CLIPS})")

        clip_a = self._clips.get(clip_id_a)
        clip_b = self._clips.get(clip_id_b)
        if clip_a is None or clip_b is None:
            return None
        if not clip_a.frames and not clip_b.frames:
            return None

        factor = max(0.0, min(1.0, blend_factor))
        max_frames = max(len(clip_a.frames), len(clip_b.frames))
        if max_frames == 0:
            return None

        name = blend_name or f"{clip_a.name}_blend_{clip_b.name}"
        blended = AnimationClip(
            name=name,
            frame_rate=max(clip_a.frame_rate, clip_b.frame_rate),
            loop=clip_a.loop or clip_b.loop,
            ping_pong=clip_a.ping_pong or clip_b.ping_pong,
            sprite_sheet_id=clip_a.sprite_sheet_id or clip_b.sprite_sheet_id,
            tags=list(set(clip_a.tags + clip_b.tags)),
        )

        for i in range(max_frames):
            frame_a = clip_a.frames[i] if i < len(clip_a.frames) else clip_a.frames[-1]
            frame_b = clip_b.frames[i] if i < len(clip_b.frames) else clip_b.frames[-1]

            texture_region = frame_a.texture_region if factor < 0.5 else frame_b.texture_region
            duration = _lerp_scalar(frame_a.duration, frame_b.duration, factor)
            anchor = _lerp_tuple(frame_a.anchor_point, frame_b.anchor_point, factor)
            scale = _lerp_tuple(frame_a.scale, frame_b.scale, factor)
            rotation = _lerp_scalar(frame_a.rotation, frame_b.rotation, factor)
            tint = tuple(
                int(_lerp_scalar(frame_a.tint[j], frame_b.tint[j], factor))
                for j in range(4)
            )
            events = list(set(frame_a.event_triggers + frame_b.event_triggers))

            frame = AnimationFrame(
                texture_region=texture_region,
                duration=max(duration, 0.001),
                anchor_point=anchor,
                scale=scale,
                rotation=rotation,
                tint=tint,
                event_triggers=events,
            )
            blended.frames.append(frame)

        blended.total_duration = self._compute_total_duration(blended)
        self._clips[blended.clip_id] = blended
        self._total_clips_created += 1
        self._total_frames_added += len(blended.frames)
        return blended

    # ------------------------------------------------------------------
    # Statistics and Lifecycle
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics about the animation system.

        Returns:
            A dictionary with clip, tween, sequence, and playback counts.
        """
        _time_module.sleep(0.001)
        total_frames = sum(len(c.frames) for c in self._clips.values())
        total_keyframes = sum(len(s.keyframes) for s in self._sequences.values())
        playing_count = sum(
            1 for s in self._playback_states.values() if s.get("is_playing")
        )
        paused_count = sum(
            1 for s in self._playback_states.values() if s.get("is_paused")
        )

        play_mode_counts: Dict[str, int] = {}
        for s in self._playback_states.values():
            mode = s.get("play_mode", "once")
            play_mode_counts[mode] = play_mode_counts.get(mode, 0) + 1

        easing_counts: Dict[str, int] = {}
        for t in self._tweens.values():
            e = t.easing.value
            easing_counts[e] = easing_counts.get(e, 0) + 1

        return {
            "total_clips": len(self._clips),
            "total_clips_created": self._total_clips_created,
            "total_frames": total_frames,
            "total_tweens": len(self._tweens),
            "total_tweens_created": self._total_tweens_created,
            "total_sequences": len(self._sequences),
            "total_sequences_created": self._total_sequences_created,
            "total_keyframes": total_keyframes,
            "playing_clips": playing_count,
            "paused_clips": paused_count,
            "play_mode_distribution": play_mode_counts,
            "easing_distribution": easing_counts,
            "animation_presets": len(self._animation_presets),
            "tween_presets": len(self._tween_presets),
            "global_time": round(self._global_time, 4),
            "max_clips": self.MAX_CLIPS,
            "max_tweens": self.MAX_TWEENS,
            "max_sequences": self.MAX_SEQUENCES,
            "max_frames_per_clip": self.MAX_FRAMES_PER_CLIP,
            "max_keyframes_per_sequence": self.MAX_KEYFRAMES_PER_SEQUENCE,
        }

    def reset(self) -> None:
        """Reset the entire animation system to its initial state."""
        _time_module.sleep(0.001)
        with self._lock:
            self._clips.clear()
            self._tweens.clear()
            self._sequences.clear()
            self._playback_states.clear()
            self._total_clips_created = 0
            self._total_tweens_created = 0
            self._total_sequences_created = 0
            self._total_frames_added = 0
            self._global_time = 0.0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_animation_system() -> EngineAnimationSystem:
    """Return the global EngineAnimationSystem singleton instance."""
    return EngineAnimationSystem.get_instance()