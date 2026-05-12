"""
Timeline System - Cutscene sequencing, keyframe animation, and cinematic orchestration.

Architecture:
    TimelineSystem/
    |-- TrackType (timeline track classification)
    |-- KeyframeInterpolation (value blending techniques)
    |-- TimelineKeyframe (single point-in-time value with interpolation)
    |-- TimelineTrack (sorted collection of keyframes per property/object)
    |-- TimelineDefinition (full cinematic timeline with multiple tracks)
    |-- TimelineSystem (unified timeline playback and evaluation orchestrator)

Manages cinematic timelines with multi-track support for animation, audio, camera,
dialogue, events, property animation, scripts, and markers. Supports looping,
playback speed control, and precise seeking with interpolation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class TrackType(Enum):
    ANIMATION = "animation"
    AUDIO = "audio"
    CAMERA = "camera"
    EVENT = "event"
    DIALOGUE = "dialogue"
    PROPERTY = "property"
    SCRIPT = "script"
    MARKER = "marker"


class KeyframeInterpolation(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    STEP = "step"
    CUBIC_BEZIER = "cubic_bezier"


@dataclass
class TimelineKeyframe:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    track_id: str = ""
    time_seconds: float = 0.0
    value: Any = None
    interpolation: KeyframeInterpolation = KeyframeInterpolation.LINEAR
    easing_params: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id[:12],
            "track_id": self.track_id[:12] if self.track_id else "",
            "time_seconds": self.time_seconds,
            "value": self.value,
            "interpolation": self.interpolation.value,
            "tags": self.tags,
        }


@dataclass
class TimelineTrack:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Track"
    track_type: TrackType = TrackType.ANIMATION
    keyframes: List[TimelineKeyframe] = field(default_factory=list)
    is_muted: bool = False
    is_locked: bool = False
    color_hex: str = "#3b82f6"

    def add_keyframe(self, keyframe: TimelineKeyframe) -> None:
        keyframe.track_id = self.id
        self.keyframes.append(keyframe)
        self.keyframes.sort(key=lambda k: k.time_seconds)

    def remove_keyframe(self, keyframe_id: str) -> bool:
        for i, kf in enumerate(self.keyframes):
            if kf.id == keyframe_id:
                self.keyframes.pop(i)
                return True
        return False

    def get_keyframe_at(self, time_seconds: float) -> Optional[TimelineKeyframe]:
        for kf in self.keyframes:
            if abs(kf.time_seconds - time_seconds) < 0.001:
                return kf
        return None

    def get_surrounding_keyframes(
        self,
        time_seconds: float,
    ) -> Tuple[Optional[TimelineKeyframe], Optional[TimelineKeyframe]]:
        prev_kf: Optional[TimelineKeyframe] = None
        next_kf: Optional[TimelineKeyframe] = None

        for kf in self.keyframes:
            if kf.time_seconds <= time_seconds:
                prev_kf = kf
            if kf.time_seconds >= time_seconds and next_kf is None:
                next_kf = kf

        return (prev_kf, next_kf)

    def keyframe_count(self) -> int:
        return len(self.keyframes)

    def duration(self) -> float:
        if not self.keyframes:
            return 0.0
        return max(kf.time_seconds for kf in self.keyframes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id[:12],
            "name": self.name,
            "track_type": self.track_type.value,
            "keyframe_count": self.keyframe_count(),
            "duration": self.duration(),
            "is_muted": self.is_muted,
            "is_locked": self.is_locked,
            "color_hex": self.color_hex,
        }


@dataclass
class TimelineDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Timeline"
    duration_seconds: float = 30.0
    tracks: List[TimelineTrack] = field(default_factory=list)
    loop_enabled: bool = False
    playback_speed: float = 1.0
    markers: Dict[str, float] = field(default_factory=dict)

    def add_track(self, track: TimelineTrack) -> None:
        self.tracks.append(track)

    def remove_track(self, track_id: str) -> bool:
        for i, track in enumerate(self.tracks):
            if track.id == track_id:
                self.tracks.pop(i)
                return True
        return False

    def get_track(self, track_id: str) -> Optional[TimelineTrack]:
        for track in self.tracks:
            if track.id == track_id:
                return track
        return None

    def add_marker(self, name: str, time_seconds: float) -> None:
        self.markers[name] = time_seconds

    def remove_marker(self, name: str) -> bool:
        if name in self.markers:
            del self.markers[name]
            return True
        return False

    def actual_duration(self) -> float:
        if not self.tracks:
            return self.duration_seconds
        return max(
            self.duration_seconds,
            max((t.duration() for t in self.tracks), default=0.0),
        )

    def track_count(self) -> int:
        return len(self.tracks)

    def total_keyframes(self) -> int:
        return sum(t.keyframe_count() for t in self.tracks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id[:12],
            "name": self.name,
            "duration_seconds": self.duration_seconds,
            "actual_duration": self.actual_duration(),
            "track_count": self.track_count(),
            "total_keyframes": self.total_keyframes(),
            "loop_enabled": self.loop_enabled,
            "playback_speed": self.playback_speed,
            "markers": self.markers,
        }


class TimelineSystem:
    """Unified timeline creation, playback, and evaluation orchestration."""

    _instance: Optional["TimelineSystem"] = None

    def __init__(self):
        self._timelines: Dict[str, TimelineDefinition] = {}
        self._playback_state: Dict[str, Dict[str, Any]] = {}
        self._timeline_count: int = 0
        self._total_keyframes_added: int = 0
        self._total_keyframes_removed: int = 0
        self._playback_listeners: List[Callable] = []

    @classmethod
    def get_instance(cls) -> "TimelineSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_timeline(
        self,
        name: str,
        duration_seconds: float = 30.0,
        loop_enabled: bool = False,
        playback_speed: float = 1.0,
    ) -> TimelineDefinition:
        timeline = TimelineDefinition(
            name=name,
            duration_seconds=duration_seconds,
            loop_enabled=loop_enabled,
            playback_speed=playback_speed,
        )
        self._timelines[timeline.id] = timeline
        self._timeline_count += 1
        return timeline

    def add_track(
        self,
        timeline_id: str,
        name: str,
        track_type: TrackType,
        color_hex: str = "#3b82f6",
    ) -> Optional[TimelineTrack]:
        timeline = self._timelines.get(timeline_id)
        if not timeline:
            return None

        track = TimelineTrack(
            name=name,
            track_type=track_type,
            color_hex=color_hex,
        )
        timeline.add_track(track)
        return track

    def add_keyframe(
        self,
        track_id: str,
        time_seconds: float,
        value: Any,
        interpolation: KeyframeInterpolation = KeyframeInterpolation.LINEAR,
        easing_params: Optional[List[float]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[TimelineKeyframe]:
        keyframe = TimelineKeyframe(
            track_id=track_id,
            time_seconds=time_seconds,
            value=value,
            interpolation=interpolation,
            easing_params=easing_params or [],
            tags=tags or [],
        )

        for timeline in self._timelines.values():
            track = timeline.get_track(track_id)
            if track:
                track.add_keyframe(keyframe)
                self._total_keyframes_added += 1
                return keyframe

        return None

    def remove_keyframe(self, keyframe_id: str) -> bool:
        for timeline in self._timelines.values():
            for track in timeline.tracks:
                if track.remove_keyframe(keyframe_id):
                    self._total_keyframes_removed += 1
                    return True
        return False

    def evaluate_at(
        self,
        timeline_id: str,
        time_seconds: float,
    ) -> Dict[str, Any]:
        timeline = self._timelines.get(timeline_id)
        if not timeline:
            return {"error": "Timeline not found"}

        result: Dict[str, Any] = {
            "timeline_id": timeline_id[:12],
            "timeline_name": timeline.name,
            "time_seconds": time_seconds,
            "tracks": {},
        }

        for track in timeline.tracks:
            if track.is_muted:
                continue

            prev_kf, next_kf = track.get_surrounding_keyframes(time_seconds)

            if prev_kf is None and next_kf is None:
                result["tracks"][track.id[:12]] = {
                    "track_name": track.name,
                    "track_type": track.track_type.value,
                    "value": None,
                    "state": "no_keyframes",
                }
                continue

            if prev_kf is None:
                result["tracks"][track.id[:12]] = {
                    "track_name": track.name,
                    "track_type": track.track_type.value,
                    "value": next_kf.value,
                    "state": "before_first",
                }
                continue

            if next_kf is None or prev_kf.id == next_kf.id:
                result["tracks"][track.id[:12]] = {
                    "track_name": track.name,
                    "track_type": track.track_type.value,
                    "value": prev_kf.value,
                    "state": "at_keyframe" if abs(prev_kf.time_seconds - time_seconds) < 0.001 else "after_last",
                }
                continue

            t_range = next_kf.time_seconds - prev_kf.time_seconds
            if t_range <= 0:
                result["tracks"][track.id[:12]] = {
                    "track_name": track.name,
                    "track_type": track.track_type.value,
                    "value": prev_kf.value,
                    "state": "zero_range",
                }
                continue

            t_param = (time_seconds - prev_kf.time_seconds) / t_range
            t_clamped = max(0.0, min(1.0, t_param))

            if prev_kf.interpolation == KeyframeInterpolation.STEP:
                t_blend = 0.0 if t_param < 1.0 else 1.0
            elif prev_kf.interpolation == KeyframeInterpolation.EASE_IN:
                t_blend = t_clamped ** 2
            elif prev_kf.interpolation == KeyframeInterpolation.EASE_OUT:
                t_blend = 1.0 - (1.0 - t_clamped) ** 2
            elif prev_kf.interpolation == KeyframeInterpolation.EASE_IN_OUT:
                t_blend = t_clamped ** 2 / (t_clamped ** 2 + (1.0 - t_clamped) ** 2)
            elif prev_kf.interpolation == KeyframeInterpolation.CUBIC_BEZIER:
                p1x = prev_kf.easing_params[0] if len(prev_kf.easing_params) > 0 else 0.42
                p1y = prev_kf.easing_params[1] if len(prev_kf.easing_params) > 1 else 0.0
                p2x = prev_kf.easing_params[2] if len(prev_kf.easing_params) > 2 else 0.58
                p2y = prev_kf.easing_params[3] if len(prev_kf.easing_params) > 3 else 1.0
                t_blend = _bezier_curve(t_clamped, p1x, p1y, p2x, p2y)
            else:
                t_blend = t_clamped

            blended_value = _interpolate_value(prev_kf.value, next_kf.value, t_blend)

            result["tracks"][track.id[:12]] = {
                "track_name": track.name,
                "track_type": track.track_type.value,
                "value": blended_value,
                "state": "interpolated",
                "blend_factor": round(t_blend, 4),
                "prev_keyframe_time": prev_kf.time_seconds,
                "next_keyframe_time": next_kf.time_seconds,
            }

        return result

    def play(self, timeline_id: str) -> Dict[str, Any]:
        timeline = self._timelines.get(timeline_id)
        if not timeline:
            return {"success": False, "error": "Timeline not found"}

        state = {
            "is_playing": True,
            "current_time": 0.0,
            "started_at": time.time(),
            "paused_at": None,
            "timeline_id": timeline_id,
        }
        self._playback_state[timeline_id] = state

        self._notify_playback(timeline_id, "play", 0.0)

        return {"success": True, "action": "play", "timeline_name": timeline.name}

    def pause(self, timeline_id: str) -> Dict[str, Any]:
        state = self._playback_state.get(timeline_id)
        if not state:
            return {"success": False, "error": "Timeline not playing"}

        state["is_playing"] = False
        state["paused_at"] = state["current_time"]

        self._notify_playback(timeline_id, "pause", state["current_time"])

        return {"success": True, "action": "pause", "time": state["current_time"]}

    def seek(self, timeline_id: str, time_seconds: float) -> Dict[str, Any]:
        timeline = self._timelines.get(timeline_id)
        if not timeline:
            return {"success": False, "error": "Timeline not found"}

        actual_duration = timeline.actual_duration()
        clamped_time = max(0.0, min(time_seconds, actual_duration))

        if timeline_id not in self._playback_state:
            self._playback_state[timeline_id] = {
                "is_playing": False,
                "current_time": 0.0,
                "started_at": 0.0,
                "paused_at": None,
                "timeline_id": timeline_id,
            }

        self._playback_state[timeline_id]["current_time"] = clamped_time
        self._playback_state[timeline_id]["paused_at"] = clamped_time

        evaluation = self.evaluate_at(timeline_id, clamped_time)

        self._notify_playback(timeline_id, "seek", clamped_time)

        return {"success": True, "action": "seek", "time": clamped_time, "evaluation": evaluation}

    def get_timeline(self, timeline_id: str) -> Optional[TimelineDefinition]:
        return self._timelines.get(timeline_id)

    def list_timelines(self) -> List[TimelineDefinition]:
        return list(self._timelines.values())

    def delete_timeline(self, timeline_id: str) -> bool:
        if timeline_id in self._timelines:
            del self._timelines[timeline_id]
            self._playback_state.pop(timeline_id, None)
            self._timeline_count = max(0, self._timeline_count - 1)
            return True
        return False

    def on_playback_event(self, callback: Callable) -> None:
        self._playback_listeners.append(callback)

    def _notify_playback(self, timeline_id: str, event: str, time_seconds: float) -> None:
        for listener in self._playback_listeners:
            try:
                listener(timeline_id, event, time_seconds)
            except Exception:
                pass

    def get_playback_state(self, timeline_id: str) -> Optional[Dict[str, Any]]:
        return self._playback_state.get(timeline_id)

    def get_playing_timelines(self) -> List[str]:
        return [
            tid for tid, state in self._playback_state.items()
            if state.get("is_playing")
        ]

    def stop_all(self) -> None:
        for tid in list(self._playback_state.keys()):
            self._playback_state[tid] = {
                "is_playing": False,
                "current_time": 0.0,
                "started_at": 0.0,
                "paused_at": None,
                "timeline_id": tid,
            }

    def get_stats(self) -> Dict[str, Any]:
        active_playbacks = len(self.get_playing_timelines())
        return {
            "total_timelines": len(self._timelines),
            "timeline_count": self._timeline_count,
            "active_playbacks": active_playbacks,
            "total_tracks": sum(t.track_count() for t in self._timelines.values()),
            "total_keyframes": sum(t.total_keyframes() for t in self._timelines.values()),
            "keyframes_added": self._total_keyframes_added,
            "keyframes_removed": self._total_keyframes_removed,
            "avg_duration": (
                sum(t.actual_duration() for t in self._timelines.values()) / max(1, len(self._timelines))
            ),
            "playback_states": len(self._playback_state),
        }


def _interpolate_value(a: Any, b: Any, t: float) -> Any:
    """Blend between two values based on their types."""
    if a is None or b is None:
        return b if t > 0.5 else a

    try:
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a + (b - a) * t
        if isinstance(a, list) and isinstance(b, list):
            return [
                _interpolate_value(ai, bi, t)
                for ai, bi in zip(a[:len(b)], b[:len(a)])
            ]
        if isinstance(a, dict) and isinstance(b, dict):
            result = {}
            for key in set(a.keys()) | set(b.keys()):
                result[key] = _interpolate_value(a.get(key), b.get(key), t)
            return result
        if isinstance(a, str) and isinstance(b, str):
            return b if t > 0.5 else a
        if isinstance(a, bool) and isinstance(b, bool):
            return b if t > 0.5 else a
    except (TypeError, ValueError):
        pass

    return b if t > 0.5 else a


def _bezier_curve(t: float, p1x: float, p1y: float, p2x: float, p2y: float) -> float:
    """Approximate cubic bezier y-value for a given t using de Casteljau algorithm."""
    # Newton-Raphson root finding for bezier x(t) - target = 0
    guess = t
    for _ in range(8):
        x = _bezier_sample(guess, 0.0, p1x, p2x, 1.0) - t
        if abs(x) < 1e-7:
            break
        dx = _bezier_derivative(guess, 0.0, p1x, p2x, 1.0)
        if abs(dx) < 1e-7:
            break
        guess -= x / dx
        guess = max(0.0, min(1.0, guess))

    return _bezier_sample(guess, 0.0, p1y, p2y, 1.0)


def _bezier_sample(t: float, a: float, b: float, c: float, d: float) -> float:
    return (
        a * (1 - t) ** 3 +
        b * 3 * t * (1 - t) ** 2 +
        c * 3 * t ** 2 * (1 - t) +
        d * t ** 3
    )


def _bezier_derivative(t: float, a: float, b: float, c: float, d: float) -> float:
    return (
        3 * (1 - t) ** 2 * (b - a) +
        6 * (1 - t) * t * (c - b) +
        3 * t ** 2 * (d - c)
    )


def get_timeline_system() -> TimelineSystem:
    return TimelineSystem.get_instance()