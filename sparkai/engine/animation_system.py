"""
SparkLabs Engine - Animation System

Keyframe-based animation engine with tween interpolation, sprite sheet
animation, and property track evaluation. Implements AnimationPlayer
concepts: keyframe tracks spanning position, rotation, scale, color,
float, bool, and string properties; tween-based property animation;
and sprite sheet frame sequencing.

Architecture:
    AnimationSystem (singleton orchestrator)
    |-- Keyframe (single point on a track with value, easing, interpolation)
    |-- AnimationTrack (property path with ordered keyframes)
    |-- AnimationClip (collection of tracks played as a unit)
    |-- SpriteFrame (single frame rect and duration)
    |-- SpriteAnimation (frame sequence with loop control)
    |-- TweenState (active property interpolation at runtime)
    |-- EasingType / LoopMode / TrackType (domain enumerations)

Easing functions: linear, quad-in/out/in-out, cubic-in/out/in-out,
sine-in/out/in-out, bounce-out, elastic-out, back-out, expo-out.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class LoopMode(Enum):
    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"


class EasingType(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    BACK = "back"
    EXPO = "expo"


class TrackType(Enum):
    POSITION = "position"
    ROTATION = "rotation"
    SCALE = "scale"
    COLOR = "color"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Keyframe:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    time: float = 0.0
    value: Any = 0.0
    easing: str = "linear"
    interpolation: str = "linear"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "time": self.time,
            "value": self.value,
            "easing": self.easing,
            "interpolation": self.interpolation,
        }


@dataclass
class AnimationTrack:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    track_name: str = ""
    target_node_id: str = ""
    property_path: str = "position.x"
    keyframes: List[Keyframe] = field(default_factory=list)
    track_type: str = "float"

    @property
    def duration(self) -> float:
        if not self.keyframes:
            return 0.0
        return self.keyframes[-1].time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "track_name": self.track_name,
            "target_node_id": self.target_node_id,
            "property_path": self.property_path,
            "track_type": self.track_type,
            "keyframe_count": len(self.keyframes),
            "duration": self.duration,
        }


@dataclass
class AnimationClip:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tracks: List[AnimationTrack] = field(default_factory=list)
    duration: float = 0.0
    loop_mode: str = "once"
    playback_speed: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "track_count": len(self.tracks),
            "duration": self.duration,
            "loop_mode": self.loop_mode,
            "playback_speed": self.playback_speed,
            "created_at": self.created_at,
        }


@dataclass
class SpriteFrame:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    texture_region: str = "0,0,32,32"
    duration: float = 0.1

    @property
    def region(self) -> Tuple[int, int, int, int]:
        parts = self.texture_region.split(",")
        if len(parts) == 4:
            return (
                int(parts[0].strip()),
                int(parts[1].strip()),
                int(parts[2].strip()),
                int(parts[3].strip()),
            )
        return (0, 0, 32, 32)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "texture_region": self.texture_region,
            "duration": self.duration,
        }


@dataclass
class SpriteAnimation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    frames: List[SpriteFrame] = field(default_factory=list)
    loop_mode: str = "loop"
    playback_speed: float = 1.0
    created_at: float = field(default_factory=time.time)

    @property
    def total_duration(self) -> float:
        return sum(f.duration for f in self.frames) / max(self.playback_speed, 0.001)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "frame_count": len(self.frames),
            "loop_mode": self.loop_mode,
            "playback_speed": self.playback_speed,
            "total_duration": self.total_duration,
            "created_at": self.created_at,
        }


@dataclass
class TweenState:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_node_id: str = ""
    property_path: str = ""
    start_value: Any = 0.0
    end_value: Any = 1.0
    start_time: float = 0.0
    duration: float = 0.5
    easing: str = "linear"
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_node_id": self.target_node_id,
            "property_path": self.property_path,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "start_time": self.start_time,
            "duration": self.duration,
            "easing": self.easing,
            "is_active": self.is_active,
        }


# ---------------------------------------------------------------------------
# Easing Functions
# ---------------------------------------------------------------------------


def _apply_easing(t: float, easing: str) -> float:
    t = max(0.0, min(1.0, t))

    if easing == "linear":
        return t

    elif easing == "ease_in":
        return t * t

    elif easing == "ease_out":
        return 1.0 - (1.0 - t) * (1.0 - t)

    elif easing == "ease_in_out":
        if t < 0.5:
            return 2.0 * t * t
        return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0

    elif easing == "bounce":
        if t < 1.0 / 2.75:
            return 7.5625 * t * t
        elif t < 2.0 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375

    elif easing == "elastic":
        if t == 0.0 or t == 1.0:
            return t
        return math.pow(2.0, -10.0 * t) * math.sin((t - 0.075) * (2.0 * math.pi) / 0.3) + 1.0

    elif easing == "back":
        s = 1.70158
        t -= 1.0
        return t * t * ((s + 1.0) * t + s) + 1.0

    elif easing == "expo":
        if t == 0.0:
            return 0.0
        return math.pow(2.0, 10.0 * (t - 1.0))

    return t


# ---------------------------------------------------------------------------
# Interpolation Helpers
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
# Animation System (Singleton)
# ---------------------------------------------------------------------------


class AnimationSystem:
    _instance: Optional["AnimationSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._clips: Dict[str, AnimationClip] = {}
        self._sprite_animations: Dict[str, SpriteAnimation] = {}
        self._tweens: Dict[str, TweenState] = {}
        self._clip_count: int = 0
        self._sprite_count: int = 0
        self._tween_count: int = 0
        self._current_time: float = 0.0

    @classmethod
    def get_instance(cls) -> "AnimationSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Animation Clips
    # ------------------------------------------------------------------

    def create_clip(
        self,
        name: str,
        loop_mode: str = "once",
        playback_speed: float = 1.0,
    ) -> AnimationClip:
        with self._lock:
            clip = AnimationClip(
                name=name,
                loop_mode=loop_mode,
                playback_speed=playback_speed,
            )
            self._clips[clip.id] = clip
            self._clip_count += 1
            return clip

    def add_track(
        self,
        clip_id: str,
        track_name: str,
        target_node_id: str,
        property_path: str,
        track_type: str = "float",
    ) -> Optional[AnimationTrack]:
        with self._lock:
            clip = self._clips.get(clip_id)
            if not clip:
                return None
            track = AnimationTrack(
                track_name=track_name,
                target_node_id=target_node_id,
                property_path=property_path,
                track_type=track_type,
            )
            clip.tracks.append(track)
            clip.duration = max((t.duration for t in clip.tracks), default=0.0)
            return track

    def add_keyframe(
        self,
        clip_id: str,
        track_id: str,
        time: float,
        value: Any,
        easing: str = "linear",
        interpolation: str = "linear",
    ) -> Optional[Keyframe]:
        with self._lock:
            clip = self._clips.get(clip_id)
            if not clip:
                return None
            for track in clip.tracks:
                if track.id == track_id:
                    kf = Keyframe(
                        time=time,
                        value=value,
                        easing=easing,
                        interpolation=interpolation,
                    )
                    track.keyframes.append(kf)
                    track.keyframes.sort(key=lambda k: k.time)
                    clip.duration = max((t.duration for t in clip.tracks), default=0.0)
                    return kf
            return None

    def remove_keyframe(
        self,
        clip_id: str,
        track_id: str,
        keyframe_id: str,
    ) -> bool:
        with self._lock:
            clip = self._clips.get(clip_id)
            if not clip:
                return False
            for track in clip.tracks:
                if track.id == track_id:
                    for i, kf in enumerate(track.keyframes):
                        if kf.id == keyframe_id:
                            track.keyframes.pop(i)
                            clip.duration = max(
                                (t.duration for t in clip.tracks), default=0.0
                            )
                            return True
            return False

    def evaluate_clip(
        self, clip_id: str, time: float
    ) -> Dict[str, Any]:
        with self._lock:
            clip = self._clips.get(clip_id)
            if not clip:
                return {}

            result: Dict[str, Any] = {}
            for track in clip.tracks:
                value = self._evaluate_track(track, time)
                result[track.property_path] = value
            return result

    def _evaluate_track(
        self, track: AnimationTrack, time: float
    ) -> Any:
        kfs = track.keyframes
        if not kfs:
            return 0.0

        if len(kfs) == 1:
            return kfs[0].value

        if time <= kfs[0].time:
            return kfs[0].value

        if time >= kfs[-1].time:
            return kfs[-1].value

        for i in range(len(kfs) - 1):
            curr = kfs[i]
            next_kf = kfs[i + 1]
            if curr.time <= time <= next_kf.time:
                segment_duration = next_kf.time - curr.time
                if segment_duration <= 0.0:
                    return next_kf.value

                raw_t = (time - curr.time) / segment_duration

                if curr.interpolation == "step":
                    return curr.value

                eased = _apply_easing(raw_t, curr.easing)
                return self.interpolate_value(
                    curr.value,
                    next_kf.value,
                    eased,
                    curr.easing,
                    curr.interpolation,
                )

        return kfs[-1].value

    # ------------------------------------------------------------------
    # Value Interpolation
    # ------------------------------------------------------------------

    def interpolate_value(
        self,
        start: Any,
        end: Any,
        t: float,
        easing: str = "linear",
        interpolation: str = "linear",
    ) -> Any:
        effective_t = max(0.0, min(1.0, t))

        if interpolation == "step":
            return start if effective_t < 1.0 else end

        eased = _apply_easing(effective_t, easing)

        if interpolation == "cubic":
            eased = eased * eased * (3.0 - 2.0 * eased)

        return _lerp_value(start, end, eased)

    # ------------------------------------------------------------------
    # Sprite Animations
    # ------------------------------------------------------------------

    def create_sprite_animation(
        self,
        name: str,
        loop_mode: str = "loop",
        playback_speed: float = 1.0,
    ) -> SpriteAnimation:
        with self._lock:
            anim = SpriteAnimation(
                name=name,
                loop_mode=loop_mode,
                playback_speed=playback_speed,
            )
            self._sprite_animations[anim.id] = anim
            self._sprite_count += 1
            return anim

    def add_frame(
        self,
        animation_id: str,
        texture_region: str,
        duration: float = 0.1,
    ) -> Optional[SpriteFrame]:
        with self._lock:
            anim = self._sprite_animations.get(animation_id)
            if not anim:
                return None
            frame = SpriteFrame(
                texture_region=texture_region,
                duration=duration,
            )
            anim.frames.append(frame)
            return frame

    def get_current_frame(
        self, animation_id: str, time: float
    ) -> Optional[SpriteFrame]:
        with self._lock:
            anim = self._sprite_animations.get(animation_id)
            if not anim:
                return None

            frames = anim.frames
            if not frames:
                return None

            total = anim.total_duration
            if total <= 0.0:
                return frames[0]

            scaled_time = time * anim.playback_speed

            if anim.loop_mode == "once":
                elapsed = min(scaled_time, total)
            elif anim.loop_mode == "ping_pong":
                cycle = int(scaled_time / total)
                remainder = scaled_time % total
                elapsed = total - remainder if cycle % 2 == 1 else remainder
            else:
                elapsed = scaled_time % total

            accumulated = 0.0
            for frame in frames:
                accumulated += frame.duration
                if accumulated >= elapsed:
                    return frame

            return frames[-1]

    # ------------------------------------------------------------------
    # Tween System
    # ------------------------------------------------------------------

    def start_tween(
        self,
        target_node_id: str,
        property_path: str,
        start_value: Any,
        end_value: Any,
        duration: float = 0.5,
        easing: str = "linear",
    ) -> TweenState:
        with self._lock:
            tween = TweenState(
                target_node_id=target_node_id,
                property_path=property_path,
                start_value=start_value,
                end_value=end_value,
                start_time=self._current_time,
                duration=max(duration, 0.001),
                easing=easing,
            )
            self._tweens[tween.id] = tween
            self._tween_count += 1
            return tween

    def update_tweens(self, delta_time: float) -> List[TweenState]:
        with self._lock:
            self._current_time += delta_time
            completed: List[TweenState] = []

            for tween_id, tween in list(self._tweens.items()):
                if not tween.is_active:
                    continue

                elapsed = self._current_time - tween.start_time
                if elapsed >= tween.duration:
                    tween.is_active = False
                    completed.append(tween)
                    del self._tweens[tween_id]
                    continue

                # The actual value interpolation is available via evaluate_tween
                # which callers use externally; update_tweens just advances time
                # and completes expired tweens.

            return completed

    def cancel_tween(self, tween_id: str) -> bool:
        with self._lock:
            if tween_id in self._tweens:
                self._tweens[tween_id].is_active = False
                del self._tweens[tween_id]
                return True
            return False

    def get_tween_value(self, tween_id: str) -> Optional[Any]:
        with self._lock:
            tween = self._tweens.get(tween_id)
            if not tween or not tween.is_active:
                return None
            elapsed = self._current_time - tween.start_time
            t = min(1.0, elapsed / tween.duration)
            eased = _apply_easing(t, tween.easing)
            return _lerp_value(tween.start_value, tween.end_value, eased)

    def set_time(self, time: float) -> None:
        with self._lock:
            self._current_time = time

    def get_time(self) -> float:
        return self._current_time

    # ------------------------------------------------------------------
    # Preset Factories
    # ------------------------------------------------------------------

    def create_fire_preset(self) -> AnimationClip:
        clip = self.create_clip("Fire", loop_mode="loop", playback_speed=1.0)

        pos_track = self.add_track(
            clip.id, "FirePosition", "fire_emitter", "position",
            TrackType.POSITION.value,
        )
        if pos_track:
            self.add_keyframe(clip.id, pos_track.id, 0.0, (0.0, 0.0), "ease_out")
            self.add_keyframe(clip.id, pos_track.id, 1.0, (0.0, -120.0), "ease_out")

        scale_track = self.add_track(
            clip.id, "FireScale", "fire_emitter", "scale",
            TrackType.SCALE.value,
        )
        if scale_track:
            self.add_keyframe(clip.id, scale_track.id, 0.0, (1.0, 1.0), "ease_out")
            self.add_keyframe(clip.id, scale_track.id, 0.5, (1.8, 1.8), "ease_out")
            self.add_keyframe(clip.id, scale_track.id, 1.0, (0.2, 0.2), "ease_in")

        color_track = self.add_track(
            clip.id, "FireColor", "fire_emitter", "modulate",
            TrackType.COLOR.value,
        )
        if color_track:
            self.add_keyframe(clip.id, color_track.id, 0.0, (255, 200, 50, 255), "ease_out")
            self.add_keyframe(clip.id, color_track.id, 0.6, (255, 100, 10, 220), "ease_out")
            self.add_keyframe(clip.id, color_track.id, 1.0, (200, 30, 0, 0), "ease_in")

        alpha_track = self.add_track(
            clip.id, "FireAlpha", "fire_emitter", "opacity",
            TrackType.FLOAT.value,
        )
        if alpha_track:
            self.add_keyframe(clip.id, alpha_track.id, 0.0, 1.0, "ease_out")
            self.add_keyframe(clip.id, alpha_track.id, 0.7, 0.6, "linear")
            self.add_keyframe(clip.id, alpha_track.id, 1.0, 0.0, "ease_in")

        return clip

    def create_sparkle_preset(self) -> AnimationClip:
        clip = self.create_clip("Sparkle", loop_mode="loop", playback_speed=1.0)

        scale_track = self.add_track(
            clip.id, "SparkleScale", "sparkle_emitter", "scale",
            TrackType.SCALE.value,
        )
        if scale_track:
            self.add_keyframe(clip.id, scale_track.id, 0.0, (0.0, 0.0), "ease_out")
            self.add_keyframe(clip.id, scale_track.id, 0.3, (1.0, 1.0), "ease_out")
            self.add_keyframe(clip.id, scale_track.id, 1.0, (0.0, 0.0), "ease_in")

        color_track = self.add_track(
            clip.id, "SparkleColor", "sparkle_emitter", "modulate",
            TrackType.COLOR.value,
        )
        if color_track:
            self.add_keyframe(clip.id, color_track.id, 0.0, (255, 255, 200, 255), "ease_out")
            self.add_keyframe(clip.id, color_track.id, 0.5, (255, 255, 255, 200), "ease_out")
            self.add_keyframe(clip.id, color_track.id, 1.0, (255, 220, 100, 0), "ease_in")

        return clip

    def create_smoke_preset(self) -> AnimationClip:
        clip = self.create_clip("Smoke", loop_mode="loop", playback_speed=0.8)

        pos_track = self.add_track(
            clip.id, "SmokePosition", "smoke_emitter", "position",
            TrackType.POSITION.value,
        )
        if pos_track:
            self.add_keyframe(clip.id, pos_track.id, 0.0, (0.0, 0.0), "ease_out")
            self.add_keyframe(clip.id, pos_track.id, 1.0, (20.0, -60.0), "ease_in_out")

        scale_track = self.add_track(
            clip.id, "SmokeScale", "smoke_emitter", "scale",
            TrackType.SCALE.value,
        )
        if scale_track:
            self.add_keyframe(clip.id, scale_track.id, 0.0, (0.3, 0.3), "ease_out")
            self.add_keyframe(clip.id, scale_track.id, 1.0, (2.5, 2.5), "ease_in")

        alpha_track = self.add_track(
            clip.id, "SmokeAlpha", "smoke_emitter", "opacity",
            TrackType.FLOAT.value,
        )
        if alpha_track:
            self.add_keyframe(clip.id, alpha_track.id, 0.0, 0.5, "ease_out")
            self.add_keyframe(clip.id, alpha_track.id, 0.4, 0.3, "linear")
            self.add_keyframe(clip.id, alpha_track.id, 1.0, 0.0, "ease_in")

        return clip

    def create_rain_preset(self) -> AnimationClip:
        clip = self.create_clip("Rain", loop_mode="loop", playback_speed=1.5)

        pos_track = self.add_track(
            clip.id, "RainPosition", "rain_drop", "position",
            TrackType.POSITION.value,
        )
        if pos_track:
            self.add_keyframe(clip.id, pos_track.id, 0.0, (0.0, -200.0), "linear")
            self.add_keyframe(clip.id, pos_track.id, 1.0, (30.0, 600.0), "linear")

        alpha_track = self.add_track(
            clip.id, "RainAlpha", "rain_drop", "opacity",
            TrackType.FLOAT.value,
        )
        if alpha_track:
            self.add_keyframe(clip.id, alpha_track.id, 0.0, 0.8, "linear")
            self.add_keyframe(clip.id, alpha_track.id, 0.85, 0.6, "linear")
            self.add_keyframe(clip.id, alpha_track.id, 1.0, 0.0, "ease_in")

        return clip

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_keyframes = sum(
            len(t.keyframes) for c in self._clips.values() for t in c.tracks
        )
        active_tweens = sum(1 for t in self._tweens.values() if t.is_active)
        total_sprite_frames = sum(
            len(s.frames) for s in self._sprite_animations.values()
        )
        return {
            "clip_count": self._clip_count,
            "sprite_count": self._sprite_count,
            "tween_count": self._tween_count,
            "total_keyframes": total_keyframes,
            "active_tweens": active_tweens,
            "stored_clips": len(self._clips),
            "stored_sprite_animations": len(self._sprite_animations),
            "stored_tweens": len(self._tweens),
            "total_sprite_frames": total_sprite_frames,
            "current_time": round(self._current_time, 3),
        }


# ---------------------------------------------------------------------------
# Backward Compatible AnimationPlayer
# ---------------------------------------------------------------------------


class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


@dataclass
class _KeyframeCompat:
    time: float = 0.0
    value: float = 0.0
    easing: str = "linear"
    metadata: Dict[str, Any] = field(default_factory=dict)


class _AnimationTrackCompat:
    def __init__(self, target: str = "custom_float", keyframes=None):
        self._target = target
        self._keyframes: List[_KeyframeCompat] = sorted(
            keyframes or [], key=lambda k: k.time
        )

    @property
    def target(self) -> str:
        return self._target

    @property
    def keyframes(self) -> List[_KeyframeCompat]:
        return list(self._keyframes)

    @property
    def duration(self) -> float:
        if not self._keyframes:
            return 0.0
        return self._keyframes[-1].time

    def add_keyframe(self, time: float, value: float, easing: str = "linear") -> _KeyframeCompat:
        kf = _KeyframeCompat(time=time, value=value, easing=easing)
        self._keyframes.append(kf)
        self._keyframes.sort(key=lambda k: k.time)
        return kf

    def remove_keyframe(self, index: int) -> bool:
        if 0 <= index < len(self._keyframes):
            self._keyframes.pop(index)
            return True
        return False

    def get_value(self, time: float) -> float:
        if not self._keyframes:
            return 0.0
        if len(self._keyframes) == 1:
            return self._keyframes[0].value

        time = max(0.0, min(time, self.duration))

        for i in range(len(self._keyframes) - 1):
            curr = self._keyframes[i]
            next_kf = self._keyframes[i + 1]
            if curr.time <= time <= next_kf.time:
                seg = next_kf.time - curr.time
                if seg <= 0:
                    return next_kf.value
                t = (time - curr.time) / seg
                eased = _apply_easing(t, curr.easing)
                return curr.value + (next_kf.value - curr.value) * eased

        return self._keyframes[-1].value


class AnimationPlayer:
    """
    Animation playback controller for backward compatibility.

    Manages playback of legacy animation clips with play, pause, stop,
    seek, and speed control.
    """

    def __init__(self):
        self._clips: Dict[str, Any] = {}
        self._active_clip: Optional[Any] = None
        self._active_clip_name: str = ""
        self._current_time: float = 0.0
        self._state: PlaybackState = PlaybackState.STOPPED
        self._callbacks: Dict[str, List[Callable]] = {
            "started": [],
            "looped": [],
            "completed": [],
            "paused": [],
            "resumed": [],
            "stopped": [],
        }

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def current_time(self) -> float:
        return self._current_time

    @property
    def active_clip_name(self) -> str:
        return self._active_clip_name

    def add_clip(self, clip: Any) -> Any:
        self._clips[clip.name] = clip
        return clip

    def remove_clip(self, name: str) -> bool:
        if self._active_clip_name == name:
            self.stop()
        if name in self._clips:
            del self._clips[name]
            return True
        return False

    def get_clip(self, name: str) -> Optional[Any]:
        return self._clips.get(name)

    def list_clips(self) -> List[str]:
        return list(self._clips.keys())

    def on(self, event: str, callback: Callable) -> None:
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger(self, event: str) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb()
            except Exception:
                pass

    def play(self, clip_name: str, from_start: bool = True) -> bool:
        clip = self._clips.get(clip_name)
        if not clip:
            return False
        self._active_clip = clip
        self._active_clip_name = clip_name
        if from_start:
            self._current_time = 0.0
        self._state = PlaybackState.PLAYING
        self._trigger("started")
        return True

    def pause(self) -> None:
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.PAUSED
            self._trigger("paused")

    def resume(self) -> None:
        if self._state == PlaybackState.PAUSED:
            self._state = PlaybackState.PLAYING
            self._trigger("resumed")

    def stop(self) -> None:
        self._current_time = 0.0
        self._state = PlaybackState.STOPPED
        self._trigger("stopped")

    def seek(self, time: float) -> None:
        self._current_time = max(0.0, time)

    def update(self, delta_time: float) -> Optional[Dict[str, float]]:
        if self._state != PlaybackState.PLAYING:
            return None
        if not self._active_clip:
            return None

        dt = delta_time * getattr(self._active_clip, "speed", 1.0)
        self._current_time += dt

        if self._current_time >= getattr(self._active_clip, "duration", 0.0):
            if getattr(self._active_clip, "loop", False):
                overflow = self._current_time - getattr(self._active_clip, "duration", 0.0)
                self._current_time = overflow % max(getattr(self._active_clip, "duration", 1.0), 0.001)
                self._trigger("looped")
                return self._active_clip.sample(self._current_time)
            else:
                self._current_time = getattr(self._active_clip, "duration", 0.0)
                self._state = PlaybackState.FINISHED
                self._trigger("completed")
                return self._active_clip.sample(getattr(self._active_clip, "duration", 0.0))

        return self._active_clip.sample(self._current_time)

    def get_current_values(self) -> Optional[Dict[str, float]]:
        if not self._active_clip:
            return None
        return self._active_clip.sample(self._current_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "clip_count": len(self._clips),
            "active_clip": self._active_clip_name,
            "current_time": round(self._current_time, 3),
        }

    def get_status(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "state": self._state.value,
            "active": self._active_clip_name,
            "time": round(self._current_time, 3),
            "clips": len(self._clips),
        }
        if self._active_clip:
            result["duration"] = round(getattr(self._active_clip, "duration", 0.0), 3)
            result["loop"] = getattr(self._active_clip, "loop", False)
        return result


# ---------------------------------------------------------------------------
# Module-Level Accessors
# ---------------------------------------------------------------------------


_global_animation_player: Optional[AnimationPlayer] = None


def get_animation_player() -> AnimationPlayer:
    global _global_animation_player
    if _global_animation_player is None:
        _global_animation_player = AnimationPlayer()
    return _global_animation_player


def get_animation_system() -> AnimationSystem:
    return AnimationSystem.get_instance()