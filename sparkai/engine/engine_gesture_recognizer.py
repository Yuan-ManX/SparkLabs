"""
SparkLabs Engine - Gesture Recognizer System

Multi-touch gesture detection and pattern matching for game input.
Processes raw touch streams into recognized gesture events through a
configurable recognition pipeline. Supports tap, swipe, pinch, rotate,
pan, flick, and complex multi-step gesture sequences with per-type
sensitivity calibration.

Architecture:
  GestureRecognizerSystem
    |-- TouchBuffer (ring-buffered touch history per touch point)
    |-- PatternMatcher (template-based gesture pattern matching)
    |-- SequenceEngine (multi-step complex gesture sequence recognition)
    |-- SensitivityCalibrator (per-gesture-type parameter adjustment)
    |-- ActiveTouchTracker (live tracking of current touch points)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class GestureType(Enum):
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    PINCH = "pinch"
    ROTATE = "rotate"
    PAN = "pan"
    FLICK = "flick"


class GestureState(Enum):
    POSSIBLE = "possible"
    BEGAN = "began"
    CHANGED = "changed"
    ENDED = "ended"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TouchPhase(Enum):
    DOWN = "down"
    MOVE = "move"
    UP = "up"
    STATIONARY = "stationary"


@dataclass
class TouchPoint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    touch_id: int = 0
    x: float = 0.0
    y: float = 0.0
    phase: TouchPhase = TouchPhase.DOWN
    timestamp: float = 0.0
    pressure: float = 1.0
    radius: float = 0.0
    previous_x: float = 0.0
    previous_y: float = 0.0

    @property
    def delta_x(self) -> float:
        return self.x - self.previous_x

    @property
    def delta_y(self) -> float:
        return self.y - self.previous_y

    @property
    def velocity(self) -> float:
        return math.sqrt(self.delta_x ** 2 + self.delta_y ** 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "touch_id": self.touch_id,
            "x": self.x, "y": self.y,
            "phase": self.phase.value, "timestamp": self.timestamp,
            "pressure": self.pressure, "radius": self.radius,
            "previous_x": self.previous_x, "previous_y": self.previous_y,
            "delta_x": self.delta_x, "delta_y": self.delta_y,
            "velocity": self.velocity,
        }


@dataclass
class GesturePattern:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    gesture_type: GestureType = GestureType.TAP
    min_points: int = 1
    max_points: int = 10
    parameters: Dict[str, Any] = field(default_factory=dict)
    sequence: List[GestureType] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "gesture_type": self.gesture_type.value,
            "min_points": self.min_points, "max_points": self.max_points,
            "parameters": self.parameters,
            "sequence": [g.value for g in self.sequence],
            "created_at": self.created_at,
        }


@dataclass
class GestureEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pattern_id: str = ""
    gesture_type: GestureType = GestureType.TAP
    state: GestureState = GestureState.POSSIBLE
    position: Tuple[float, float] = (0.0, 0.0)
    delta: Tuple[float, float] = (0.0, 0.0)
    velocity: float = 0.0
    angle: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    duration_ms: float = 0.0
    touch_count: int = 0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    involved_touch_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "pattern_id": self.pattern_id,
            "gesture_type": self.gesture_type.value,
            "state": self.state.value,
            "position": list(self.position), "delta": list(self.delta),
            "velocity": self.velocity, "angle": self.angle,
            "scale": self.scale, "rotation": self.rotation,
            "duration_ms": self.duration_ms,
            "touch_count": self.touch_count, "confidence": self.confidence,
            "timestamp": self.timestamp,
            "involved_touch_ids": self.involved_touch_ids,
        }


@dataclass
class RecognizerConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tap_max_duration_ms: float = 300.0
    tap_max_movement: float = 20.0
    double_tap_interval_ms: float = 400.0
    long_press_min_duration_ms: float = 500.0
    swipe_min_distance: float = 50.0
    swipe_min_velocity: float = 200.0
    pinch_min_scale_delta: float = 0.05
    rotate_min_angle_degrees: float = 5.0
    pan_min_distance: float = 10.0
    flick_min_velocity: float = 800.0
    flick_max_duration_ms: float = 150.0
    max_touch_history: int = 120
    confidence_threshold: float = 0.6
    is_enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tap_max_duration_ms": self.tap_max_duration_ms,
            "tap_max_movement": self.tap_max_movement,
            "double_tap_interval_ms": self.double_tap_interval_ms,
            "long_press_min_duration_ms": self.long_press_min_duration_ms,
            "swipe_min_distance": self.swipe_min_distance,
            "swipe_min_velocity": self.swipe_min_velocity,
            "pinch_min_scale_delta": self.pinch_min_scale_delta,
            "rotate_min_angle_degrees": self.rotate_min_angle_degrees,
            "pan_min_distance": self.pan_min_distance,
            "flick_min_velocity": self.flick_min_velocity,
            "flick_max_duration_ms": self.flick_max_duration_ms,
            "max_touch_history": self.max_touch_history,
            "confidence_threshold": self.confidence_threshold,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at,
        }


class GestureRecognizerSystem:
    """
    Multi-touch gesture recognition and pattern matching for game input.

    Processes raw touch events through a configurable detection pipeline
    that identifies tap, swipe, pinch, rotate, pan, flick, double-tap,
    and long-press gestures. Supports custom gesture pattern registration
    with parameterized thresholds, complex multi-step gesture sequences,
    and per-gesture-type sensitivity calibration for precise input tuning.
    """

    _instance: Optional["GestureRecognizerSystem"] = None
    _lock = threading.RLock()

    MAX_PATTERNS = 200
    MAX_COMPLEX_SEQUENCES = 100
    MAX_SEQUENCE_DEPTH = 20
    MAX_TOUCH_POINTS = 20
    MAX_HISTORY_LENGTH = 500
    MAX_EVENTS_PER_FRAME = 50

    def __init__(self):
        self._patterns: Dict[str, GesturePattern] = {}
        self._complex_sequences: Dict[str, GesturePattern] = {}
        self._active_touches: Dict[int, TouchPoint] = {}
        self._touch_history: Dict[int, List[TouchPoint]] = {}
        self._gesture_history: List[GestureEvent] = []
        self._config = RecognizerConfig()
        self._last_tap_event: Optional[GestureEvent] = None
        self._last_tap_timestamp: float = 0.0
        self._sequence_state: Dict[str, int] = {}
        self._sequence_start_times: Dict[str, float] = {}
        self._total_touches_processed: int = 0
        self._total_gestures_recognized: int = 0
        self._sensitivity_multipliers: Dict[GestureType, float] = {}
        for gt in GestureType:
            self._sensitivity_multipliers[gt] = 1.0

    @classmethod
    def get_instance(cls) -> "GestureRecognizerSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Pattern Registration
    # ------------------------------------------------------------------

    def register_pattern(
        self,
        name: str,
        gesture_type: str,
        min_points: int = 1,
        max_points: int = 10,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[GesturePattern]:
        if len(self._patterns) >= self.MAX_PATTERNS:
            return None
        try:
            gt = GestureType(gesture_type.lower())
        except ValueError:
            return None

        pattern = GesturePattern(
            name=name, gesture_type=gt,
            min_points=max(1, min_points),
            max_points=max(min_points, min(max_points, self.MAX_TOUCH_POINTS)),
            parameters=parameters or {},
        )
        self._patterns[pattern.id] = pattern
        return pattern

    def define_complex_gesture(
        self,
        name: str,
        sequence: Optional[List[str]] = None,
    ) -> Optional[GesturePattern]:
        if len(self._complex_sequences) >= self.MAX_COMPLEX_SEQUENCES:
            return None

        resolved_sequence: List[GestureType] = []
        if sequence:
            for item in sequence[:self.MAX_SEQUENCE_DEPTH]:
                try:
                    resolved_sequence.append(GestureType(item.lower()))
                except ValueError:
                    continue

        if not resolved_sequence:
            return None

        pattern = GesturePattern(
            name=name,
            gesture_type=resolved_sequence[0],
            sequence=resolved_sequence,
        )
        self._complex_sequences[pattern.id] = pattern
        self._sequence_state[pattern.id] = 0
        self._sequence_start_times[pattern.id] = 0.0
        return pattern

    # ------------------------------------------------------------------
    # Touch Input
    # ------------------------------------------------------------------

    def feed_touch(
        self,
        touch_id: int,
        x: float,
        y: float,
        phase: str = "down",
        timestamp: float = 0.0,
    ) -> None:
        if len(self._active_touches) >= self.MAX_TOUCH_POINTS and touch_id not in self._active_touches:
            return

        try:
            tp = TouchPhase(phase.lower())
        except ValueError:
            tp = TouchPhase.DOWN

        ts = timestamp if timestamp > 0 else time.time() * 1000.0

        previous_point = self._active_touches.get(touch_id)

        point = TouchPoint(
            touch_id=touch_id, x=x, y=y, phase=tp, timestamp=ts,
            previous_x=previous_point.x if previous_point else x,
            previous_y=previous_point.y if previous_point else y,
        )

        if tp == TouchPhase.UP:
            self._active_touches.pop(touch_id, None)
            self._append_to_history(touch_id, point)
        else:
            self._active_touches[touch_id] = point
            self._append_to_history(touch_id, point)

        self._total_touches_processed += 1

    def _append_to_history(self, touch_id: int, point: TouchPoint) -> None:
        if touch_id not in self._touch_history:
            self._touch_history[touch_id] = []
        history = self._touch_history[touch_id]
        history.append(point)
        max_hist = self._config.max_touch_history
        if len(history) > max_hist:
            self._touch_history[touch_id] = history[-max_hist:]

    def get_active_touches(self) -> List[TouchPoint]:
        return list(self._active_touches.values())

    # ------------------------------------------------------------------
    # Frame Processing
    # ------------------------------------------------------------------

    def process_frame(self) -> List[GestureEvent]:
        if not self._config.is_enabled:
            return []

        events: List[GestureEvent] = []

        completed_touches = self._find_completed_touches()
        for touch_id, history in completed_touches:
            evt = self._detect_single_touch_gestures(touch_id, history)
            if evt is not None:
                events.append(evt)

        active_multi = self._prepare_multi_touch_data()
        multi_events = self._detect_multi_touch_gestures(active_multi)
        events.extend(multi_events)

        sequence_events = self._evaluate_complex_sequences(events)
        events.extend(sequence_events)

        for evt in events[:self.MAX_EVENTS_PER_FRAME]:
            self._gesture_history.append(evt)
            self._total_gestures_recognized += 1

        if len(self._gesture_history) > self.MAX_HISTORY_LENGTH:
            self._gesture_history = self._gesture_history[-self.MAX_HISTORY_LENGTH:]

        return events[:self.MAX_EVENTS_PER_FRAME]

    def _find_completed_touches(self) -> List[Tuple[int, List[TouchPoint]]]:
        result: List[Tuple[int, List[TouchPoint]]] = []
        for tid, history in list(self._touch_history.items()):
            if not history:
                continue
            last = history[-1]
            if last.phase == TouchPhase.UP:
                result.append((tid, list(history)))
        return result

    def _prepare_multi_touch_data(self) -> List[TouchPoint]:
        return [p for p in self._active_touches.values() if p.phase != TouchPhase.UP]

    # ------------------------------------------------------------------
    # Single-Touch Gesture Detection
    # ------------------------------------------------------------------

    def _detect_single_touch_gestures(
        self, touch_id: int, history: List[TouchPoint],
    ) -> Optional[GestureEvent]:
        if len(history) < 2:
            return None
        first, last = history[0], history[-1]
        duration_ms = last.timestamp - first.timestamp
        movement = math.sqrt((last.x - first.x) ** 2 + (last.y - first.y) ** 2)
        dx, dy = last.x - first.x, last.y - first.y
        cfg, sens = self._config, self._sensitivity_multipliers[GestureType.TAP]

        def _build(gt, vel, ang):
            return self._build_event(gt, (first.x, first.y), (dx, dy), vel, ang, duration_ms, 1, touch_id, history)

        # Flick
        if duration_ms <= cfg.flick_max_duration_ms * (2.0 - sens * 0.5):
            peak = self._compute_peak_velocity(history)
            if peak >= cfg.flick_min_velocity / max(sens, 0.1):
                return _build(GestureType.FLICK, peak, math.degrees(math.atan2(dy, dx)))

        # Swipe
        if movement >= cfg.swipe_min_distance / max(sens, 0.1):
            peak = self._compute_peak_velocity(history)
            if peak >= cfg.swipe_min_velocity / max(sens, 0.1):
                return _build(GestureType.SWIPE, peak, math.degrees(math.atan2(dy, dx)))

        # Tap / Double-tap
        if (duration_ms <= cfg.tap_max_duration_ms * (2.0 - sens * 0.5)
                and movement <= cfg.tap_max_movement / max(sens, 0.1)):
            if (self._last_tap_event is not None
                    and last.timestamp - self._last_tap_timestamp <= cfg.double_tap_interval_ms):
                self._last_tap_event, self._last_tap_timestamp = None, 0.0
                return GestureEvent(gesture_type=GestureType.DOUBLE_TAP, state=GestureState.ENDED,
                    position=(first.x, first.y), delta=(dx, dy),
                    velocity=self._compute_peak_velocity(history),
                    duration_ms=last.timestamp - self._last_tap_timestamp,
                    touch_count=1, confidence=0.95, involved_touch_ids=[touch_id])
            tap_evt = _build(GestureType.TAP, self._compute_peak_velocity(history), 0.0)
            self._last_tap_event, self._last_tap_timestamp = tap_evt, last.timestamp
            return tap_evt

        # Long press
        if (duration_ms >= cfg.long_press_min_duration_ms / max(sens, 0.1)
                and movement <= cfg.tap_max_movement):
            return _build(GestureType.LONG_PRESS, 0.0, 0.0)

        # Pan
        if movement >= cfg.pan_min_distance / max(sens, 0.1):
            peak = self._compute_peak_velocity(history)
            return _build(GestureType.PAN, peak, math.degrees(math.atan2(dy, dx)))

        return None

    # ------------------------------------------------------------------
    # Multi-Touch Gesture Detection
    # ------------------------------------------------------------------

    def _detect_multi_touch_gestures(
        self, active_touches: List[TouchPoint],
    ) -> List[GestureEvent]:
        if len(active_touches) < 2:
            return []
        events: List[GestureEvent] = []
        touch_ids = [t.touch_id for t in active_touches]
        a, b = active_touches[0], active_touches[1]
        cx, cy = (a.x + b.x) / 2.0, (a.y + b.y) / 2.0
        prev_dist = math.sqrt((a.previous_x - b.previous_x) ** 2 + (a.previous_y - b.previous_y) ** 2)
        cur_dist = math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)
        scale_delta = cur_dist / max(prev_dist, 0.001)
        cfg = self._config
        sp = self._sensitivity_multipliers[GestureType.PINCH]
        sr = self._sensitivity_multipliers[GestureType.ROTATE]

        if abs(1.0 - scale_delta) >= cfg.pinch_min_scale_delta / max(sp, 0.1):
            events.append(GestureEvent(gesture_type=GestureType.PINCH, state=GestureState.CHANGED,
                position=(cx, cy), scale=scale_delta, touch_count=2, confidence=0.85,
                involved_touch_ids=touch_ids))

        prev_ang = math.atan2(b.previous_y - a.previous_y, b.previous_x - a.previous_x)
        curr_ang = math.atan2(b.y - a.y, b.x - a.x)
        rotation_deg = math.degrees(curr_ang - prev_ang)
        if abs(rotation_deg) >= cfg.rotate_min_angle_degrees / max(sr, 0.1):
            events.append(GestureEvent(gesture_type=GestureType.ROTATE, state=GestureState.CHANGED,
                position=(cx, cy), rotation=rotation_deg, touch_count=2, confidence=0.85,
                involved_touch_ids=touch_ids))

        return events

    # ------------------------------------------------------------------
    # Complex Sequence Evaluation
    # ------------------------------------------------------------------

    def _evaluate_complex_sequences(
        self, frame_events: List[GestureEvent],
    ) -> List[GestureEvent]:
        results: List[GestureEvent] = []
        now = time.time() * 1000.0
        for seq_id, pattern in self._complex_sequences.items():
            step = self._sequence_state.get(seq_id, 0)
            if step >= len(pattern.sequence):
                continue
            matched = next((e for e in frame_events if e.gesture_type == pattern.sequence[step]), None)
            if matched is not None:
                if step == 0:
                    self._sequence_start_times[seq_id] = now
                self._sequence_state[seq_id] = step + 1
                if self._sequence_state[seq_id] >= len(pattern.sequence):
                    results.append(GestureEvent(
                        pattern_id=pattern.id, gesture_type=pattern.gesture_type,
                        state=GestureState.ENDED, position=matched.position,
                        delta=matched.delta, velocity=matched.velocity,
                        duration_ms=now - self._sequence_start_times.get(seq_id, 0.0),
                        touch_count=matched.touch_count, confidence=0.9,
                        involved_touch_ids=list(matched.involved_touch_ids)))
                    self._sequence_state[seq_id] = 0
                    self._sequence_start_times[seq_id] = 0.0
            else:
                start_ts = self._sequence_start_times.get(seq_id, 0.0)
                if start_ts > 0 and now - start_ts > 3000:
                    self._sequence_state[seq_id] = 0
                    self._sequence_start_times[seq_id] = 0.0
        return results

    # ------------------------------------------------------------------
    # Explicit Recognition
    # ------------------------------------------------------------------

    def recognize_gesture(
        self,
        gesture_type: str,
        touch_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[GestureEvent]:
        try:
            gt = GestureType(gesture_type.lower())
        except ValueError:
            return None

        if touch_history is None:
            active = self._prepare_multi_touch_data()
            if not active:
                return None
            if gt in (GestureType.PINCH, GestureType.ROTATE) and len(active) >= 2:
                multi = self._detect_multi_touch_gestures(active)
                for evt in multi:
                    if evt.gesture_type == gt:
                        return evt
            return None

        if len(touch_history) < 2:
            return None

        history_points: List[TouchPoint] = []
        for entry in touch_history:
            try:
                phase = TouchPhase(entry.get("phase", "move").lower())
            except ValueError:
                phase = TouchPhase.MOVE
            history_points.append(TouchPoint(
                touch_id=0, x=entry.get("x", 0.0), y=entry.get("y", 0.0),
                phase=phase, timestamp=entry.get("timestamp", 0.0),
            ))

        return self._detect_single_touch_gestures(0, history_points)

    # ------------------------------------------------------------------
    # Sensitivity Calibration
    # ------------------------------------------------------------------

    def calibrate_sensitivity(
        self, gesture_type: str, sensitivity: float = 1.0,
    ) -> bool:
        try:
            gt = GestureType(gesture_type.lower())
        except ValueError:
            return False

        clamped = max(0.1, min(5.0, sensitivity))
        self._sensitivity_multipliers[gt] = clamped
        return True

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_gesture_history(self, limit: int = 50) -> List[GestureEvent]:
        capped = min(limit, len(self._gesture_history))
        return list(self._gesture_history[-capped:])

    def get_stats(self) -> Dict[str, Any]:
        active_count = len(self._active_touches)
        history_touch_count = sum(len(h) for h in self._touch_history.values())
        complex_active = sum(
            1 for s in self._sequence_state.values() if s > 0
        )
        return {
            "total_patterns": len(self._patterns),
            "total_complex_sequences": len(self._complex_sequences),
            "active_touches": active_count,
            "total_touch_histories": len(self._touch_history),
            "total_history_points": history_touch_count,
            "total_touches_processed": self._total_touches_processed,
            "total_gestures_recognized": self._total_gestures_recognized,
            "gesture_history_size": len(self._gesture_history),
            "complex_sequences_active": complex_active,
            "is_enabled": self._config.is_enabled,
            "confidence_threshold": self._config.confidence_threshold,
            "sensitivity_multipliers": {
                gt.value: s for gt, s in self._sensitivity_multipliers.items()
            },
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self._active_touches.clear()
        self._touch_history.clear()
        self._gesture_history.clear()
        self._last_tap_event = None
        self._last_tap_timestamp = 0.0
        self._sequence_state.clear()
        self._sequence_start_times.clear()
        self._total_touches_processed = 0
        self._total_gestures_recognized = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _compute_peak_velocity(self, history: List[TouchPoint]) -> float:
        peak = 0.0
        for i in range(1, len(history)):
            dx = history[i].x - history[i - 1].x
            dy = history[i].y - history[i - 1].y
            dt = max(history[i].timestamp - history[i - 1].timestamp, 0.001)
            speed = math.sqrt(dx * dx + dy * dy) / (dt / 1000.0)
            if speed > peak:
                peak = speed
        return peak

    def _build_event(
        self,
        gesture_type: GestureType,
        position: Tuple[float, float],
        delta: Tuple[float, float],
        velocity: float,
        angle: float,
        duration_ms: float,
        touch_count: int,
        touch_id: int,
        history: List[TouchPoint],
    ) -> GestureEvent:
        confidence = self._compute_confidence(gesture_type, history)
        state = GestureState.ENDED if confidence >= self._config.confidence_threshold else GestureState.FAILED
        return GestureEvent(
            gesture_type=gesture_type, state=state,
            position=position, delta=delta,
            velocity=velocity, angle=angle,
            duration_ms=duration_ms, touch_count=touch_count,
            confidence=confidence,
            involved_touch_ids=[touch_id],
        )

    def _compute_confidence(
        self, gesture_type: GestureType, history: List[TouchPoint],
    ) -> float:
        cfg = self._config
        sens = self._sensitivity_multipliers.get(gesture_type, 1.0)
        base = 0.85
        if len(history) < 2:
            base *= 0.5
        duration = history[-1].timestamp - history[0].timestamp
        if gesture_type == GestureType.TAP:
            ratio = duration / max(cfg.tap_max_duration_ms * sens, 1.0)
            base *= max(0.4, 1.0 - ratio * 0.6)
        elif gesture_type == GestureType.SWIPE:
            dist = math.sqrt(
                (history[-1].x - history[0].x) ** 2
                + (history[-1].y - history[0].y) ** 2
            )
            ratio = dist / max(cfg.swipe_min_distance / max(sens, 0.1), 1.0)
            base *= min(1.0, ratio * 0.7 + 0.3)
        elif gesture_type == GestureType.FLICK:
            peak = self._compute_peak_velocity(history)
            ratio = peak / max(cfg.flick_min_velocity / max(sens, 0.1), 1.0)
            base *= min(1.0, ratio * 0.6 + 0.4)
        elif gesture_type == GestureType.LONG_PRESS:
            ratio = duration / max(cfg.long_press_min_duration_ms / max(sens, 0.1), 1.0)
            base *= min(1.0, ratio * 0.3 + 0.7)
        return min(1.0, max(0.0, base))


def get_gesture_recognizer() -> GestureRecognizerSystem:
    return GestureRecognizerSystem.get_instance()