"""
SparkLabs Engine - Animation Curve Editor

Bezier curve-based animation interpolation with keyframe editing,
easing functions, and curve evaluation. Provides a full-featured
curve editing system with multiple interpolation modes, automatic
curve fitting, optimization, and sequence playback.

Architecture:
  AnimationCurveEditor
    |-- Keyframe (time, value, in/out tangents, interpolation)
    |-- AnimationCurve (curve with keyframes, easing, wrap mode)
    |-- CurveTrack (entity property bound to an animation curve)
    |-- CurveSequence (multiple tracks with playback control)
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class CurveType(Enum):
    LINEAR = "linear"
    BEZIER = "bezier"
    CATMULL_ROM = "catmull_rom"
    STEP = "step"
    HERMITE = "hermite"
    BOUNCE = "bounce"
    ELASTIC = "elastic"


class EasingFunction(Enum):
    LINEAR = "linear"
    EASE_IN_QUAD = "ease_in_quad"
    EASE_OUT_QUAD = "ease_out_quad"
    EASE_IN_OUT_QUAD = "ease_in_out_quad"
    EASE_IN_CUBIC = "ease_in_cubic"
    EASE_OUT_CUBIC = "ease_out_cubic"
    EASE_IN_OUT_CUBIC = "ease_in_out_cubic"
    EASE_IN_ELASTIC = "ease_in_elastic"
    EASE_OUT_ELASTIC = "ease_out_elastic"
    EASE_IN_BOUNCE = "ease_in_bounce"
    EASE_OUT_BOUNCE = "ease_out_bounce"
    EASE_IN_BACK = "ease_in_back"
    EASE_OUT_BACK = "ease_out_back"


class KeyframeInterpolation(Enum):
    CONSTANT = "constant"
    LINEAR = "linear"
    BEZIER = "bezier"
    AUTO = "auto"


class WrapMode(Enum):
    CLAMP = "clamp"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    ONCE = "once"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Keyframe:
    """Single keyframe with time, value, tangents, and interpolation mode."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    time: float = 0.0
    value: float = 0.0
    in_tangent: Tuple[float, float] = (0.0, 0.0)
    out_tangent: Tuple[float, float] = (0.0, 0.0)
    interpolation: KeyframeInterpolation = KeyframeInterpolation.LINEAR
    broken_tangents: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "time": self.time,
            "value": self.value,
            "in_tangent": list(self.in_tangent),
            "out_tangent": list(self.out_tangent),
            "interpolation": self.interpolation.value,
            "broken_tangents": self.broken_tangents,
            "created_at": self.created_at,
        }


@dataclass
class AnimationCurve:
    """Animation curve with keyframes, easing, and wrap mode."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    curve_type: CurveType = CurveType.LINEAR
    keyframes: List[Keyframe] = field(default_factory=list)
    easing: EasingFunction = EasingFunction.LINEAR
    wrap_mode: WrapMode = WrapMode.CLAMP
    min_value: float = 0.0
    max_value: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "curve_type": self.curve_type.value,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
            "easing": self.easing.value,
            "wrap_mode": self.wrap_mode.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "created_at": self.created_at,
        }

    @property
    def duration(self) -> float:
        if not self.keyframes:
            return 0.0
        return max(kf.time for kf in self.keyframes)


@dataclass
class CurveTrack:
    """Curve bound to a specific entity property for animation."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    target_entity: str = ""
    target_property: str = ""
    curve: AnimationCurve = field(default_factory=lambda: AnimationCurve())
    enabled: bool = True
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "target_entity": self.target_entity,
            "target_property": self.target_property,
            "curve": self.curve.to_dict(),
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


@dataclass
class CurveSequence:
    """Sequence of multiple animation curves playing together."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tracks: List[str] = field(default_factory=list)
    duration: float = 1.0
    loop: bool = False
    playback_speed: float = 1.0
    current_time: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "track_ids": list(self.tracks),
            "duration": self.duration,
            "loop": self.loop,
            "playback_speed": self.playback_speed,
            "current_time": self.current_time,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Animation Curve Editor (Singleton)
# ---------------------------------------------------------------------------


class AnimationCurveEditor:
    """Bezier curve-based animation interpolation editor and evaluator."""

    _instance: Optional["AnimationCurveEditor"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._curves: Dict[str, AnimationCurve] = {}
        self._tracks: Dict[str, CurveTrack] = {}
        self._sequences: Dict[str, CurveSequence] = {}

    @classmethod
    def get_instance(cls) -> "AnimationCurveEditor":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Curve Creation and Management
    # ------------------------------------------------------------------

    def create_curve(
        self,
        name: str = "",
        curve_type: CurveType = CurveType.BEZIER,
        easing: EasingFunction = EasingFunction.LINEAR,
    ) -> AnimationCurve:
        """Create and register a new animation curve."""
        curve = AnimationCurve(
            name=name,
            curve_type=curve_type,
            easing=easing,
        )
        self._curves[curve.id] = curve
        return curve

    def get_curve(self, curve_id: str) -> Optional[AnimationCurve]:
        """Retrieve a curve by id."""
        return self._curves.get(curve_id)

    def delete_curve(self, curve_id: str) -> bool:
        """Delete a curve from the editor."""
        if curve_id not in self._curves:
            return False
        for track_id, track in list(self._tracks.items()):
            if track.curve.id == curve_id:
                del self._tracks[track_id]
        del self._curves[curve_id]
        return True

    # ------------------------------------------------------------------
    # Keyframe Management
    # ------------------------------------------------------------------

    def add_keyframe(
        self,
        curve_id: str,
        time: float,
        value: float,
        in_tangent: Optional[Tuple[float, float]] = None,
        out_tangent: Optional[Tuple[float, float]] = None,
    ) -> Optional[Keyframe]:
        """Add a keyframe to a curve at the specified time and value."""
        curve = self._curves.get(curve_id)
        if curve is None:
            return None
        if in_tangent is None:
            in_tangent = (-0.2, 0.0)
        if out_tangent is None:
            out_tangent = (0.2, 0.0)
        keyframe = Keyframe(
            time=time,
            value=value,
            in_tangent=in_tangent,
            out_tangent=out_tangent,
        )
        curve.keyframes.append(keyframe)
        curve.keyframes.sort(key=lambda k: k.time)
        self._auto_adjust_tangents(curve)
        self._update_min_max(curve)
        return keyframe

    def remove_keyframe(self, curve_id: str, keyframe_id: str) -> bool:
        """Remove a keyframe from a curve."""
        curve = self._curves.get(curve_id)
        if curve is None:
            return False
        original_count = len(curve.keyframes)
        curve.keyframes = [kf for kf in curve.keyframes if kf.id != keyframe_id]
        if len(curve.keyframes) == original_count:
            return False
        self._update_min_max(curve)
        return True

    def update_keyframe(
        self,
        curve_id: str,
        keyframe_id: str,
        time: Optional[float] = None,
        value: Optional[float] = None,
        in_tangent: Optional[Tuple[float, float]] = None,
        out_tangent: Optional[Tuple[float, float]] = None,
        broken_tangents: Optional[bool] = None,
    ) -> bool:
        """Update keyframe properties."""
        curve = self._curves.get(curve_id)
        if curve is None:
            return False
        for kf in curve.keyframes:
            if kf.id == keyframe_id:
                if time is not None:
                    kf.time = time
                if value is not None:
                    kf.value = value
                if in_tangent is not None:
                    kf.in_tangent = in_tangent
                if out_tangent is not None:
                    kf.out_tangent = out_tangent
                if broken_tangents is not None:
                    kf.broken_tangents = broken_tangents
                curve.keyframes.sort(key=lambda k: k.time)
                self._update_min_max(curve)
                return True
        return False

    # ------------------------------------------------------------------
    # Curve Evaluation
    # ------------------------------------------------------------------

    def evaluate_curve(self, curve_id: str, time: float) -> float:
        """Evaluate a curve at the given time and return the interpolated value."""
        curve = self._curves.get(curve_id)
        if curve is None or not curve.keyframes:
            return 0.0
        duration = curve.duration
        if duration <= 0:
            return curve.keyframes[0].value if curve.keyframes else 0.0
        wrapped_time = self._wrap_time(time, curve.wrap_mode, duration)
        return self._evaluate_unwrapped(curve, wrapped_time)

    def evaluate_curve_normalized(self, curve_id: str, t: float) -> float:
        """Evaluate a curve using normalized time in [0, 1] range."""
        curve = self._curves.get(curve_id)
        if curve is None:
            return 0.0
        duration = max(curve.duration, 0.0001)
        return self.evaluate_curve(curve_id, t * duration)

    def _wrap_time(self, time: float, wrap_mode: WrapMode, duration: float) -> float:
        """Apply the wrap mode to the given time."""
        if duration <= 0:
            return 0.0
        if time < 0:
            if wrap_mode == WrapMode.LOOP:
                while time < 0:
                    time += duration
            elif wrap_mode == WrapMode.PING_PONG:
                if duration > 0:
                    cycles = abs(int(time / duration))
                    if cycles % 2 == 1:
                        time = -(time % duration)
                    else:
                        time = duration - (time % duration)
            return max(0.0, time)
        if time > duration:
            if wrap_mode == WrapMode.LOOP:
                time = time % duration
            elif wrap_mode == WrapMode.PING_PONG:
                full_cycles = int(time / duration)
                remainder = time % duration
                if full_cycles % 2 == 1:
                    time = duration - remainder
                else:
                    time = remainder
            else:
                time = duration
        return time

    def _evaluate_unwrapped(self, curve: AnimationCurve, time: float) -> float:
        """Evaluate the curve at an unwrapped time within [0, duration]."""
        if len(curve.keyframes) == 0:
            return 0.0
        if len(curve.keyframes) == 1:
            return curve.keyframes[0].value
        for i in range(len(curve.keyframes) - 1):
            kf_a = curve.keyframes[i]
            kf_b = curve.keyframes[i + 1]
            if time >= kf_a.time and time <= kf_b.time:
                t_segment = (time - kf_a.time) / (kf_b.time - kf_a.time)
                t_eased = self._apply_easing(t_segment, curve.easing)
                return self._interpolate_segment(kf_a, kf_b, t_eased, curve.curve_type)
        if time <= curve.keyframes[0].time:
            return curve.keyframes[0].value
        return curve.keyframes[-1].value

    def _interpolate_segment(
        self,
        kf_a: Keyframe,
        kf_b: Keyframe,
        t: float,
        curve_type: CurveType,
    ) -> float:
        """Interpolate between two keyframes using the specified curve type."""
        interp = kf_a.interpolation
        if interp == KeyframeInterpolation.CONSTANT:
            return kf_a.value
        elif interp == KeyframeInterpolation.LINEAR:
            return kf_a.value + (kf_b.value - kf_a.value) * t
        elif interp == KeyframeInterpolation.BEZIER:
            return self._interpolate_bezier(kf_a, kf_b, t)
        elif curve_type == CurveType.BEZIER:
            return self._interpolate_bezier(kf_a, kf_b, t)
        elif curve_type == CurveType.CATMULL_ROM:
            return self._interpolate_catmull_rom(kf_a, kf_b, t)
        elif curve_type == CurveType.HERMITE:
            return self._hermite_interpolation(kf_a, kf_b, t)
        else:
            return kf_a.value + (kf_b.value - kf_a.value) * t

    # ------------------------------------------------------------------
    # Internal Interpolation Methods
    # ------------------------------------------------------------------

    def _interpolate_bezier(self, kf_a: Keyframe, kf_b: Keyframe, t: float) -> float:
        """Cubic bezier interpolation between two keyframes."""
        p0 = (kf_a.time, kf_a.value)
        p3 = (kf_b.time, kf_b.value)
        segment_duration = p3[0] - p0[0]
        p1 = (
            p0[0] + kf_a.out_tangent[0] * segment_duration,
            p0[1] + kf_a.out_tangent[1] * (p3[1] - p0[1]),
        )
        p2 = (
            p3[0] + kf_b.in_tangent[0] * segment_duration,
            p3[1] + kf_b.in_tangent[1] * (p3[1] - p0[1]),
        )
        u = 1.0 - t
        result = (
            (u ** 3) * p0[1] +
            3 * (u ** 2) * t * p1[1] +
            3 * u * (t ** 2) * p2[1] +
            (t ** 3) * p3[1]
        )
        return result

    def _interpolate_catmull_rom(
        self,
        p0: Keyframe,
        p1: Keyframe,
        p2: Keyframe,
        p3: Keyframe,
        t: float,
    ) -> float:
        """Catmull-Rom spline interpolation between four points."""
        t2 = t * t
        t3 = t2 * t
        v0 = (p2.value - p0.value) * 0.5
        v1 = (p3.value - p1.value) * 0.5
        return (
            (2 * p1.value) +
            (-v0 + v1) * t +
            (2 * v0 - 3 * p1.value + 3 * p2.value - v1) * t2 +
            (-v0 + 2 * p1.value - 2 * p2.value + v1) * t3
        )

    def _hermite_interpolation(self, kf_a: Keyframe, kf_b: Keyframe, t: float) -> float:
        """Hermite spline interpolation between two keyframes."""
        t2 = t * t
        t3 = t2 * t
        m0 = kf_a.out_tangent[1] * (kf_b.value - kf_a.value)
        m1 = kf_b.in_tangent[1] * (kf_b.value - kf_a.value)
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        return h00 * kf_a.value + h10 * m0 + h01 * kf_b.value + h11 * m1

    def _apply_easing(self, t: float, easing_function: EasingFunction) -> float:
        """Apply the specified easing function to the input t."""
        if easing_function == EasingFunction.LINEAR:
            return t
        elif easing_function == EasingFunction.EASE_IN_QUAD:
            return t * t
        elif easing_function == EasingFunction.EASE_OUT_QUAD:
            return t * (2.0 - t)
        elif easing_function == EasingFunction.EASE_IN_OUT_QUAD:
            if t < 0.5:
                return 2 * t * t
            else:
                return -1 + (4 - 2 * t) * t
        elif easing_function == EasingFunction.EASE_IN_CUBIC:
            return t * t * t
        elif easing_function == EasingFunction.EASE_OUT_CUBIC:
            return (t - 1) ** 3 + 1
        elif easing_function == EasingFunction.EASE_IN_OUT_CUBIC:
            if t < 0.5:
                return 4 * t ** 3
            else:
                return 1 - ((-2 * t + 2) ** 3) / 2
        elif easing_function == EasingFunction.EASE_IN_ELASTIC:
            return self._ease_in_elastic(t)
        elif easing_function == EasingFunction.EASE_OUT_ELASTIC:
            return self._ease_out_elastic(t)
        elif easing_function == EasingFunction.EASE_IN_BOUNCE:
            return 1.0 - self._ease_out_bounce(1.0 - t)
        elif easing_function == EasingFunction.EASE_OUT_BOUNCE:
            return self._ease_out_bounce(t)
        elif easing_function == EasingFunction.EASE_IN_BACK:
            return self._ease_in_back(t)
        elif easing_function == EasingFunction.EASE_OUT_BACK:
            return self._ease_out_back(t)
        return t

    def _ease_in_elastic(self, t: float) -> float:
        if t == 0:
            return 0
        if t == 1:
            return 1
        return -(2 ** (10 * (t - 1))) * math.sin((t - 1.1) * math.pi * 2)

    def _ease_out_elastic(self, t: float) -> float:
        if t == 0:
            return 0
        if t == 1:
            return 1
        return 2 ** (-10 * t) * math.sin((t - 0.1) * math.pi * 2) + 1

    def _ease_out_bounce(self, t: float) -> float:
        n1 = 7.5625
        d1 = 1.0 / 2.75
        if t < 1 / d1:
            return n1 * t * t
        elif t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        elif t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        else:
            t -= 2.625 / d1
            return n1 * t * t + 0.984375

    def _ease_in_back(self, t: float) -> float:
        c = 1.70158
        return t * t * ((c + 1) * t - c)

    def _ease_out_back(self, t: float) -> float:
        c = 1.70158
        t = t - 1
        return t * t * ((c + 1) * t + c) + 1

    # ------------------------------------------------------------------
    # Curve Fitting and Optimization
    # ------------------------------------------------------------------

    def fit_to_points(
        self,
        curve_id: str,
        data_points: List[Tuple[float, float]],
    ) -> Optional[AnimationCurve]:
        """Fit the curve to a list of (time, value) data points."""
        curve = self._curves.get(curve_id)
        if curve is None:
            return None
        if len(data_points) < 2:
            return curve
        sorted_points = sorted(data_points, key=lambda p: p[0])
        curve.keyframes.clear()
        for time, value in sorted_points:
            kf = Keyframe(time=time, value=value)
            curve.keyframes.append(kf)
        self._auto_adjust_tangents(curve)
        self._update_min_max(curve)
        return curve

    def optimize_curve(self, curve_id: str, tolerance: float) -> Optional[AnimationCurve]:
        """Remove redundant keyframes that are within tolerance of the interpolated line."""
        curve = self._curves.get(curve_id)
        if curve is None or len(curve.keyframes) <= 2:
            return curve
        keyframes = curve.keyframes
        optimized = [keyframes[0], keyframes[-1]]
        start = 0
        end = len(keyframes) - 1
        self._douglas_peucker(keyframes, start, end, tolerance, optimized)
        optimized.sort(key=lambda k: k.time)
        curve.keyframes = optimized
        self._update_min_max(curve)
        return curve

    def _douglas_peucker(
        self,
        keyframes: List[Keyframe],
        start: int,
        end: int,
        epsilon: float,
        result: List[Keyframe],
    ) -> None:
        """Recursive Douglas-Peucker algorithm for curve simplification."""
        if end - start <= 1:
            return
        max_dist = 0.0
        farthest_index = start
        for i in range(start + 1, end):
            dist = self._distance_to_segment(
                keyframes[i].value,
                keyframes[start].value,
                keyframes[end].value,
            )
            if dist > max_dist:
                max_dist = dist
                farthest_index = i
        if max_dist > epsilon:
            self._douglas_peucker(keyframes, start, farthest_index, epsilon, result)
            result.append(keyframes[farthest_index])
            self._douglas_peucker(keyframes, farthest_index, end, epsilon, result)

    def _distance_to_segment(self, p: float, a: float, b: float) -> float:
        """Calculate vertical distance from a point to a line segment in 1D."""
        return abs(p - (a + (b - a) * 0.5))

    # ------------------------------------------------------------------
    # Track and Sequence Management
    # ------------------------------------------------------------------

    def create_track(
        self,
        name: str,
        target_entity: str,
        target_property: str,
        curve_id: str,
    ) -> Optional[CurveTrack]:
        """Create a curve track bound to a specific entity property."""
        curve = self._curves.get(curve_id)
        if curve is None:
            return None
        track = CurveTrack(
            name=name,
            target_entity=target_entity,
            target_property=target_property,
            curve=curve,
        )
        self._tracks[track.id] = track
        return track

    def get_track(self, track_id: str) -> Optional[CurveTrack]:
        """Get a track by id."""
        return self._tracks.get(track_id)

    def create_sequence(
        self,
        name: str,
        track_ids: List[str],
        duration: float,
        loop: bool = False,
        playback_speed: float = 1.0,
    ) -> CurveSequence:
        """Create a sequence from multiple tracks."""
        valid_tracks = [tid for tid in track_ids if tid in self._tracks]
        sequence = CurveSequence(
            name=name,
            tracks=valid_tracks,
            duration=duration,
            loop=loop,
            playback_speed=playback_speed,
        )
        self._sequences[sequence.id] = sequence
        return sequence

    def update_track(
        self,
        sequence_id: str,
        elapsed_time: float,
    ) -> Dict[str, float]:
        """Update all tracks in a sequence with elapsed time and return evaluated values."""
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return {}
        results: Dict[str, float] = {}
        dt = elapsed_time * sequence.playback_speed
        sequence.current_time += dt
        if sequence.loop and sequence.current_time > sequence.duration:
            while sequence.current_time > sequence.duration:
                sequence.current_time -= sequence.duration
        elif not sequence.loop and sequence.current_time > sequence.duration:
            sequence.current_time = sequence.duration
        for track_id in sequence.tracks:
            track = self._tracks.get(track_id)
            if track is not None and track.enabled:
                value = self.evaluate_curve(track.curve.id, sequence.current_time)
                results[f"{track.target_entity}.{track.target_property}"] = value
        return results

    def reset_sequence(self, sequence_id: str) -> bool:
        """Reset a sequence's playback time to zero."""
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return False
        sequence.current_time = 0.0
        return True

    # ------------------------------------------------------------------
    # Copy and Export
    # ------------------------------------------------------------------

    def copy_curve(self, curve_id: str, new_name: str) -> Optional[AnimationCurve]:
        """Create a copy of an existing curve."""
        source = self._curves.get(curve_id)
        if source is None:
            return None
        cloned_keyframes: List[Keyframe] = []
        for kf in source.keyframes:
            cloned = Keyframe(
                time=kf.time,
                value=kf.value,
                in_tangent=kf.in_tangent,
                out_tangent=kf.out_tangent,
                interpolation=kf.interpolation,
                broken_tangents=kf.broken_tangents,
            )
            cloned_keyframes.append(cloned)
        curve = AnimationCurve(
            name=new_name,
            curve_type=source.curve_type,
            keyframes=cloned_keyframes,
            easing=source.easing,
            wrap_mode=source.wrap_mode,
            min_value=source.min_value,
            max_value=source.max_value,
        )
        self._curves[curve.id] = curve
        return curve

    def export_curve(self, curve_id: str) -> Dict[str, Any]:
        """Serialize a curve to a dictionary for export."""
        curve = self._curves.get(curve_id)
        if curve is None:
            return {}
        return {
            "version": 1,
            "curve": curve.to_dict(),
        }

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    def _auto_adjust_tangents(self, curve: AnimationCurve) -> None:
        """Automatically calculate smooth tangents for auto-interpolation keyframes."""
        if len(curve.keyframes) < 2:
            return
        for i in range(len(curve.keyframes)):
            kf = curve.keyframes[i]
            if not kf.broken_tangents:
                prev = curve.keyframes[i - 1] if i > 0 else None
                next_kf = curve.keyframes[i + 1] if i < len(curve.keyframes) - 1 else None
                if prev and next_kf:
                    delta_val = next_kf.value - prev.value
                    delta_time = next_kf.time - prev.time
                    if delta_time > 0:
                        tangent_slope = delta_val / (3.0 * delta_time)
                        kf.in_tangent = (-0.333, tangent_slope)
                        kf.out_tangent = (0.333, tangent_slope)
                elif prev:
                    tangent_slope = (kf.value - prev.value) / (3.0 * (kf.time - prev.time))
                    kf.in_tangent = (-0.333, tangent_slope)
                    kf.out_tangent = (0.333, tangent_slope)
                elif next_kf:
                    tangent_slope = (next_kf.value - kf.value) / (3.0 * (next_kf.time - kf.time))
                    kf.in_tangent = (-0.333, tangent_slope)
                    kf.out_tangent = (0.333, tangent_slope)

    def _update_min_max(self, curve: AnimationCurve) -> None:
        """Update the min and max value cache for the curve."""
        if not curve.keyframes:
            curve.min_value = 0.0
            curve.max_value = 1.0
            return
        values = [kf.value for kf in curve.keyframes]
        curve.min_value = min(values)
        curve.max_value = max(values)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about the current state of the editor."""
        total_keyframes = sum(len(c.keyframes) for c in self._curves.values())
        type_counts: Dict[str, int] = {}
        for c in self._curves.values():
            k = c.curve_type.value
            type_counts[k] = type_counts.get(k, 0) + 1
        return {
            "total_curves": len(self._curves),
            "total_keyframes": total_keyframes,
            "total_tracks": len(self._tracks),
            "total_sequences": len(self._sequences),
            "average_keyframes_per_curve": (
                total_keyframes / len(self._curves) if self._curves else 0
            ),
            "curve_type_distribution": type_counts,
        }


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_animation_curve() -> AnimationCurveEditor:
    """Return the singleton AnimationCurveEditor instance."""
    return AnimationCurveEditor.get_instance()