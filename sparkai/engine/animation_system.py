"""
SparkLabs Engine - Animation System

Keyframe-based animation engine with tweening, timeline management,
and event triggers. Drives property interpolation across position,
rotation, scale, color, and custom float/int values. Supports
multiple tracks per animation player and concurrent animation layers.

Architecture:
  AnimationSystem
    |-- AnimationTrack (interpolates a single property over time)
    |-- AnimationClip (collection of tracks played together)
    |-- AnimationPlayer (controls playback: play, pause, stop, seek)
    |-- TweenEngine (easing functions and interpolation)

Tween Easing Functions:
  - LINEAR: uniform speed
  - EASE_IN: accelerate from start
  - EASE_OUT: decelerate to end
  - EASE_IN_OUT: smooth acceleration and deceleration
  - BOUNCE: overshoot and bounce
  - ELASTIC: spring-like oscillation
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class EasingType(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    CUBIC_IN = "cubic_in"
    CUBIC_OUT = "cubic_out"
    QUINT_IN_OUT = "quint_in_out"


class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


class TrackTarget(Enum):
    POSITION_X = "position_x"
    POSITION_Y = "position_y"
    POSITION_Z = "position_z"
    ROTATION_X = "rotation_x"
    ROTATION_Y = "rotation_y"
    ROTATION_Z = "rotation_z"
    SCALE_X = "scale_x"
    SCALE_Y = "scale_y"
    SCALE_Z = "scale_z"
    COLOR_R = "color_r"
    COLOR_G = "color_g"
    COLOR_B = "color_b"
    COLOR_A = "color_a"
    CUSTOM_FLOAT = "custom_float"
    CUSTOM_INT = "custom_int"


@dataclass
class Keyframe:
    time: float = 0.0
    value: float = 0.0
    easing: EasingType = EasingType.LINEAR
    metadata: Dict[str, Any] = field(default_factory=dict)


def _apply_easing(t: float, easing: EasingType) -> float:
    t = max(0.0, min(1.0, t))
    if easing == EasingType.LINEAR:
        return t
    elif easing == EasingType.EASE_IN:
        return t * t * t
    elif easing == EasingType.EASE_OUT:
        return 1.0 - (1.0 - t) ** 3
    elif easing == EasingType.EASE_IN_OUT:
        if t < 0.5:
            return 4.0 * t * t * t
        return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0
    elif easing == EasingType.BOUNCE:
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
    elif easing == EasingType.ELASTIC:
        if t == 0 or t == 1:
            return t
        return -(2.0 ** (10.0 * t - 10.0)) * math.sin((t * 10.0 - 10.75) * (2.0 * math.pi / 3.0))
    elif easing == EasingType.CUBIC_IN:
        return t * t * t
    elif easing == EasingType.CUBIC_OUT:
        return 1.0 - (1.0 - t) ** 3
    elif easing == EasingType.QUINT_IN_OUT:
        if t < 0.5:
            return 16.0 * t * t * t * t * t
        return 1.0 - ((-2.0 * t + 2.0) ** 5) / 2.0
    return t


class AnimationTrack:
    """
    Single property animation track with keyframe interpolation.

    Stores keyframes for a specific property and interpolates
    between them using the specified easing function.
    """

    def __init__(
        self,
        target: TrackTarget = TrackTarget.CUSTOM_FLOAT,
        keyframes: Optional[List[Keyframe]] = None,
    ):
        self._target = target
        self._keyframes: List[Keyframe] = sorted(keyframes or [], key=lambda k: k.time)

    @property
    def target(self) -> TrackTarget:
        return self._target

    @property
    def keyframes(self) -> List[Keyframe]:
        return list(self._keyframes)

    @property
    def duration(self) -> float:
        if not self._keyframes:
            return 0.0
        return self._keyframes[-1].time

    def add_keyframe(self, time: float, value: float, easing: EasingType = EasingType.LINEAR) -> Keyframe:
        kf = Keyframe(time=time, value=value, easing=easing)
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
                segment_duration = next_kf.time - curr.time
                if segment_duration <= 0:
                    return next_kf.value
                t = (time - curr.time) / segment_duration
                eased = _apply_easing(t, curr.easing)
                return curr.value + (next_kf.value - curr.value) * eased

        return self._keyframes[-1].value


class AnimationClip:
    """
    Collection of animation tracks played as a single unit.

    Groups properties that animate together (e.g. a walk cycle
    animating both position and rotation). Tracks can be added
    dynamically and queried at any playback time.
    """

    def __init__(self, name: str = "clip", loop: bool = False, speed: float = 1.0):
        self.clip_id: str = str(uuid.uuid4())[:8]
        self.name: str = name
        self.loop: bool = loop
        self.speed: float = speed
        self._tracks: Dict[TrackTarget, AnimationTrack] = {}
        self._duration: float = 0.0

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def tracks(self) -> Dict[TrackTarget, AnimationTrack]:
        return dict(self._tracks)

    def add_track(self, target: TrackTarget, keyframes: Optional[List[Keyframe]] = None) -> AnimationTrack:
        track = AnimationTrack(target=target, keyframes=keyframes)
        self._tracks[target] = track
        self._recalculate_duration()
        return track

    def remove_track(self, target: TrackTarget) -> bool:
        if target in self._tracks:
            del self._tracks[target]
            self._recalculate_duration()
            return True
        return False

    def get_track(self, target: TrackTarget) -> Optional[AnimationTrack]:
        return self._tracks.get(target)

    def _recalculate_duration(self) -> None:
        self._duration = max(
            (track.duration for track in self._tracks.values()), default=0.0
        )

    def sample(self, time: float) -> Dict[TrackTarget, float]:
        result: Dict[TrackTarget, float] = {}
        for target, track in self._tracks.items():
            result[target] = track.get_value(time)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "loop": self.loop,
            "speed": self.speed,
            "duration": round(self._duration, 3),
            "track_count": len(self._tracks),
            "targets": [t.value for t in self._tracks.keys()],
            "tracks": {
                t.value: {
                    "keyframe_count": len(self._tracks[t].keyframes),
                    "duration": round(self._tracks[t].duration, 3),
                }
                for t in self._tracks
            },
        }


class AnimationPlayer:
    """
    Animation playback controller.

    Manages playback of animation clips with play, pause, stop,
    seek, and speed control. Tracks current time and state,
    and can emit signals at animation milestones (start, loop,
    complete).

    Usage:
        player = AnimationPlayer()
        player.add_clip(walk_clip)
        player.play("walk_clip")
        while player.state == PlaybackState.PLAYING:
            values = player.update(delta_time)
            apply_to_entity(entity, values)
    """

    def __init__(self):
        self._clips: Dict[str, AnimationClip] = {}
        self._active_clip: Optional[AnimationClip] = None
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

    def add_clip(self, clip: AnimationClip) -> AnimationClip:
        self._clips[clip.name] = clip
        return clip

    def remove_clip(self, name: str) -> bool:
        if self._active_clip_name == name:
            self.stop()
        if name in self._clips:
            del self._clips[name]
            return True
        return False

    def get_clip(self, name: str) -> Optional[AnimationClip]:
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

    def update(self, delta_time: float) -> Optional[Dict[TrackTarget, float]]:
        if self._state != PlaybackState.PLAYING:
            return None
        if not self._active_clip:
            return None

        dt = delta_time * self._active_clip.speed
        self._current_time += dt

        if self._current_time >= self._active_clip.duration:
            if self._active_clip.loop:
                overflow = self._current_time - self._active_clip.duration
                self._current_time = overflow % self._active_clip.duration
                self._trigger("looped")
                return self._active_clip.sample(self._current_time)
            else:
                self._current_time = self._active_clip.duration
                self._state = PlaybackState.FINISHED
                self._trigger("completed")
                return self._active_clip.sample(self._active_clip.duration)

        return self._active_clip.sample(self._current_time)

    def get_current_values(self) -> Optional[Dict[TrackTarget, float]]:
        if not self._active_clip:
            return None
        return self._active_clip.sample(self._current_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "clip_count": len(self._clips),
            "active_clip": self._active_clip_name,
            "current_time": round(self._current_time, 3),
            "clips": [c.to_dict() for c in self._clips.values()],
        }

    def get_status(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "state": self._state.value,
            "active": self._active_clip_name,
            "time": round(self._current_time, 3),
            "clips": len(self._clips),
        }
        if self._active_clip:
            result["duration"] = round(self._active_clip.duration, 3)
            result["loop"] = self._active_clip.loop
        return result


_global_animation_player: Optional[AnimationPlayer] = None


def get_animation_player() -> AnimationPlayer:
    global _global_animation_player
    if _global_animation_player is None:
        _global_animation_player = AnimationPlayer()
    return _global_animation_player
