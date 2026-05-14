"""
SparkLabs Engine - Input Gesture System

Multi-touch gesture recognition engine subsystem. Processes raw
touch input into structured gesture events through a priority-based
recognition pipeline with simultaneous and mutually-exclusive
recognition support.

Architecture:
  InputGestureSystem
    |-- GestureRecognizer (per-type state machine with configurable thresholds)
    |-- TouchTracker (raw touch point lifecycle management)
    |-- RecognitionPipeline (priority-sorted recognizer evaluation)
    |-- GestureHistoryRing (bounded event history for analysis)
    |-- ListenerRegistry (typed callback dispatch per gesture type)

Gesture State Machine:
  POSSIBLE → BEGAN → CHANGED → ENDED
     ↓         ↓                  ↑
  FAILED   CANCELLED ←───────────┘

Recognition Rules:
  - Simultaneous gestures allowed via GestureConfig.simultaneous_with
  - Failure dependencies enforced via GestureConfig.require_failure_of
  - Higher-priority gestures block lower-priority ones by default
  - Edge gestures require touch origin within configured margin
"""

from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class GestureType(Enum):
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    PINCH = "pinch"
    ROTATE = "rotate"
    PAN = "pan"
    EDGE_SWIPE = "edge_swipe"
    FORCE_TOUCH = "force_touch"
    SHAKE = "shake"


class GestureState(Enum):
    POSSIBLE = "possible"
    BEGAN = "began"
    CHANGED = "changed"
    ENDED = "ended"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TouchPoint:
    touch_id: int = 0
    position_x: float = 0.0
    position_y: float = 0.0
    force: float = 1.0
    timestamp: float = field(default_factory=time.time)
    phase: str = "began"

    def is_active(self) -> bool:
        return self.phase in ("began", "moved", "stationary")

    def is_ending(self) -> bool:
        return self.phase in ("ended", "cancelled")


@dataclass
class GestureConfig:
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    gesture_type: GestureType = GestureType.TAP
    min_touches: int = 1
    max_touches: int = 1
    min_duration_ms: float = 0.0
    max_duration_ms: float = 500.0
    min_distance_px: float = 10.0
    min_scale_delta: float = 0.05
    min_rotation_degrees: float = 5.0
    taps_required: int = 1
    max_tap_gap_ms: float = 350.0
    edge_margin_px: float = 30.0
    priority: int = 50
    simultaneous_with: List[GestureType] = field(default_factory=list)
    require_failure_of: List[GestureType] = field(default_factory=list)


@dataclass
class GestureEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    gesture_type: GestureType = GestureType.TAP
    state: GestureState = GestureState.POSSIBLE
    touch_points: List[TouchPoint] = field(default_factory=list)
    centroid_x: float = 0.0
    centroid_y: float = 0.0
    scale: float = 1.0
    rotation_degrees: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class _GestureRecognizerState:
    config: GestureConfig
    current_state: GestureState = GestureState.POSSIBLE
    tracked_touch_ids: Set[int] = field(default_factory=set)
    touch_history: List[TouchPoint] = field(default_factory=list)
    start_time: float = 0.0
    last_event_time: float = 0.0
    start_centroid_x: float = 0.0
    start_centroid_y: float = 0.0
    last_centroid_x: float = 0.0
    last_centroid_y: float = 0.0
    start_touch_distance: float = 0.0
    start_touch_angle: float = 0.0
    tap_count: int = 0
    last_tap_time: float = 0.0
    enabled: bool = True


class InputGestureSystem:
    """
    Multi-touch gesture recognition engine.

    Processes raw touch point streams through configurable gesture
    recognizers using a priority-based pipeline. Supports simultaneous
    recognition, failure delegation, and history tracking.

    Usage:
        igs = InputGestureSystem()
        igs.register_gesture(GestureConfig(
            gesture_type=GestureType.TAP,
            max_duration_ms=300.0,
        ))
        events = igs.process_touch(TouchPoint(
            touch_id=0, position_x=120, position_y=340,
            phase="began",
        ))
        for evt in events:
            if evt.state == GestureState.ENDED:
                handle_tap(evt)
    """

    _instance: Optional["InputGestureSystem"] = None

    @classmethod
    def get_instance(cls) -> "InputGestureSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._recognizers: Dict[str, _GestureRecognizerState] = {}
        self._configs: Dict[str, GestureConfig] = {}
        self._type_to_configs: Dict[GestureType, List[str]] = defaultdict(list)
        self._listeners: Dict[GestureType, Dict[str, Callable[[GestureEvent], None]]] = defaultdict(dict)
        self._history: deque = deque(maxlen=200)
        self._event_history: deque = deque(maxlen=200)
        self._total_gestures_recognized: int = 0
        self._by_type_counts: Dict[GestureType, int] = defaultdict(int)
        self._disabled_types: Set[GestureType] = set()
        self._builtin_recognizers_installed: bool = False

    def register_gesture(self, config: GestureConfig) -> GestureConfig:
        self._configs[config.config_id] = config
        self._type_to_configs[config.gesture_type].append(config.config_id)

        state = _GestureRecognizerState(config=config)
        self._recognizers[config.config_id] = state

        return config

    def unregister_gesture(self, config_id: str) -> bool:
        if config_id not in self._configs:
            return False
        config = self._configs.pop(config_id)
        self._type_to_configs[config.gesture_type].remove(config_id)
        self._recognizers.pop(config_id, None)
        return True

    def set_gesture_enabled(self, gesture_type: GestureType, enabled: bool) -> None:
        if not enabled:
            self._disabled_types.add(gesture_type)
        else:
            self._disabled_types.discard(gesture_type)
        for config_id in self._type_to_configs.get(gesture_type, []):
            state = self._recognizers.get(config_id)
            if state:
                state.enabled = enabled

    def is_gesture_enabled(self, gesture_type: GestureType) -> bool:
        return gesture_type not in self._disabled_types

    def process_touch(self, touch_point: TouchPoint) -> List[GestureEvent]:
        return self.process_touches([touch_point])

    def process_touches(self, touch_points: List[TouchPoint]) -> List[GestureEvent]:
        if not self._builtin_recognizers_installed:
            self._install_builtin_recognizers()

        events: List[GestureEvent] = []
        active_touches = self._update_touch_tracker(touch_points)

        configs_by_priority = sorted(
            self._configs.values(),
            key=lambda c: -c.priority,
        )

        for touch in touch_points:
            self._history.append(touch)

        failed_configs: Set[str] = set()
        for config in configs_by_priority:
            state = self._recognizers.get(config.config_id)
            if not state or not state.enabled:
                continue
            if config.gesture_type in self._disabled_types:
                continue

            require_failure_ids = self._get_config_ids_for_types(config.require_failure_of)
            if require_failure_ids and not require_failure_ids.issubset(failed_configs):
                continue

            evt = self._evaluate_recognizer(state, touch_points, active_touches)
            if evt is not None:
                events.append(evt)
                self._event_history.append(evt)

                if evt.state == GestureState.FAILED:
                    failed_configs.add(config.config_id)

                    for other_config in configs_by_priority:
                        if other_config.config_id == config.config_id:
                            continue
                        if other_config.priority > config.priority:
                            continue
                        if config.config_id in _get_dependency_ids(other_config):
                            failed_configs.add(config.config_id)

                if evt.state == GestureState.ENDED:
                    self._total_gestures_recognized += 1
                    self._by_type_counts[evt.gesture_type] += 1

                if evt.state in (GestureState.BEGAN, GestureState.CHANGED, GestureState.ENDED):
                    self._notify_listeners(evt)

        return events

    def _evaluate_recognizer(
        self,
        state: _GestureRecognizerState,
        incoming_touches: List[TouchPoint],
        active_touches: Dict[int, TouchPoint],
    ) -> Optional[GestureEvent]:

        config = state.config
        relevant_touches = self._get_relevant_touches(state, incoming_touches, active_touches)

        if not relevant_touches and state.current_state not in (
            GestureState.BEGAN, GestureState.CHANGED, GestureState.ENDED
        ):
            return None

        touch_count = len(relevant_touches)

        if state.current_state == GestureState.POSSIBLE:
            return self._evaluate_possible(state, relevant_touches, touch_count)

        elif state.current_state == GestureState.BEGAN:
            return self._evaluate_began(state, relevant_touches, touch_count)

        elif state.current_state == GestureState.CHANGED:
            return self._evaluate_changed(state, relevant_touches, touch_count)

        return None

    def _evaluate_possible(
        self, state: _GestureRecognizerState, touches: List[TouchPoint], touch_count: int
    ) -> Optional[GestureEvent]:
        config = state.config

        if touch_count < config.min_touches:
            return None

        can_begin = False
        for touch in touches:
            if touch.phase == "began":
                if touch_count >= config.min_touches:
                    can_begin = True
                    state.tracked_touch_ids.add(touch.touch_id)
                    state.touch_history.append(touch)
                break

        if can_begin or len(state.tracked_touch_ids) >= config.min_touches:
            state.current_state = GestureState.BEGAN
            state.start_time = time.time()
            state.last_event_time = state.start_time

            centroid = self._compute_centroid(touches)
            state.start_centroid_x = centroid[0]
            state.start_centroid_y = centroid[1]
            state.last_centroid_x = centroid[0]
            state.last_centroid_y = centroid[1]

            if len(touches) >= 2:
                state.start_touch_distance = self._compute_touch_distance(touches)
                state.start_touch_angle = self._compute_touch_angle(touches)

            return self._make_event(state, touches, GestureState.BEGAN)

        return None

    def _evaluate_began(
        self, state: _GestureRecognizerState, touches: List[TouchPoint], touch_count: int
    ) -> Optional[GestureEvent]:
        config = state.config
        now = time.time()
        elapsed_ms = (now - state.start_time) * 1000.0

        all_ended = all(t.phase in ("ended", "cancelled") for t in touches)

        if all_ended:
            if config.gesture_type == GestureType.TAP:
                if elapsed_ms < config.max_duration_ms:
                    return self._finalize_gesture(state, touches, GestureState.ENDED)
                else:
                    return self._finalize_gesture(state, touches, GestureState.FAILED)
            elif config.gesture_type == GestureType.LONG_PRESS:
                if elapsed_ms >= config.min_duration_ms:
                    return self._finalize_gesture(state, touches, GestureState.ENDED)
                else:
                    return self._finalize_gesture(state, touches, GestureState.FAILED)
            elif config.gesture_type == GestureType.SWIPE:
                distance = self._compute_distance_from_start(state, touches)
                if distance >= config.min_distance_px:
                    return self._finalize_gesture(state, touches, GestureState.ENDED)
                else:
                    return self._finalize_gesture(state, touches, GestureState.FAILED)
            elif config.gesture_type == GestureType.PAN:
                distance = self._compute_distance_from_start(state, touches)
                if distance >= config.min_distance_px:
                    return self._finalize_gesture(state, touches, GestureState.ENDED)
                else:
                    return self._finalize_gesture(state, touches, GestureState.FAILED)
            elif config.gesture_type == GestureType.FORCE_TOUCH:
                for t in touches:
                    if t.force >= 0.8:
                        return self._finalize_gesture(state, touches, GestureState.ENDED)
                return self._finalize_gesture(state, touches, GestureState.FAILED)
            else:
                return self._finalize_gesture(state, touches, GestureState.ENDED)

        if config.gesture_type == GestureType.LONG_PRESS:
            if elapsed_ms >= config.min_duration_ms and touch_count >= config.min_touches:
                return self._make_event(state, touches, GestureState.CHANGED)

        if config.gesture_type in (GestureType.SWIPE, GestureType.PAN):
            distance = self._compute_distance_from_start(state, touches)
            if distance >= config.min_distance_px:
                state.current_state = GestureState.CHANGED
                return self._make_event(state, touches, GestureState.CHANGED)

        if config.gesture_type in (GestureType.PINCH, GestureType.ROTATE):
            if touch_count >= 2:
                state.current_state = GestureState.CHANGED
                return self._make_event(state, touches, GestureState.CHANGED)

        if elapsed_ms > config.max_duration_ms > 0:
            return self._finalize_gesture(state, touches, GestureState.FAILED)

        for touch in touches:
            if touch.phase in ("moved", "stationary"):
                state.touch_history.append(touch)

        return self._make_event(state, touches, GestureState.CHANGED)

    def _evaluate_changed(
        self, state: _GestureRecognizerState, touches: List[TouchPoint], touch_count: int
    ) -> Optional[GestureEvent]:
        config = state.config
        now = time.time()
        elapsed_ms = (now - state.start_time) * 1000.0

        all_ended = all(t.phase in ("ended", "cancelled") for t in touches)

        if all_ended:
            return self._finalize_gesture(state, touches, GestureState.ENDED)

        if touch_count < config.min_touches and config.gesture_type not in (
            GestureType.TAP, GestureType.DOUBLE_TAP, GestureType.LONG_PRESS,
        ):
            return self._finalize_gesture(state, touches, GestureState.CANCELLED)

        if elapsed_ms > config.max_duration_ms > 0 and config.gesture_type not in (
            GestureType.PINCH, GestureType.ROTATE, GestureType.PAN,
        ):
            return self._finalize_gesture(state, touches, GestureState.FAILED)

        for touch in touches:
            if touch.phase in ("moved", "stationary"):
                state.touch_history.append(touch)

        return self._make_event(state, touches, GestureState.CHANGED)

    def _finalize_gesture(
        self, state: _GestureRecognizerState, touches: List[TouchPoint],
        final_state: GestureState
    ) -> GestureEvent:
        evt = self._make_event(state, touches, final_state)
        state.current_state = GestureState.POSSIBLE
        state.tracked_touch_ids.clear()
        state.touch_history.clear()
        state.start_time = 0.0
        state.start_centroid_x = 0.0
        state.start_centroid_y = 0.0
        return evt

    def _make_event(
        self, state: _GestureRecognizerState, touches: List[TouchPoint],
        gesture_state: GestureState,
    ) -> GestureEvent:
        now = time.time()
        centroid = self._compute_centroid(touches)
        velocity = self._compute_velocity(state, centroid, now)
        duration_ms = (now - state.start_time) * 1000.0 if state.start_time > 0 else 0.0

        scale = 1.0
        rotation = 0.0
        if len(touches) >= 2 and state.start_touch_distance > 0:
            current_distance = self._compute_touch_distance(touches)
            scale = current_distance / state.start_touch_distance
            current_angle = self._compute_touch_angle(touches)
            rotation = current_angle - state.start_touch_angle

        state.last_centroid_x = centroid[0]
        state.last_centroid_y = centroid[1]
        state.last_event_time = now

        return GestureEvent(
            gesture_type=state.config.gesture_type,
            state=gesture_state,
            touch_points=list(touches),
            centroid_x=centroid[0],
            centroid_y=centroid[1],
            scale=scale,
            rotation_degrees=rotation,
            velocity_x=velocity[0],
            velocity_y=velocity[1],
            duration_ms=duration_ms,
            timestamp=now,
        )

    def _compute_centroid(self, touches: List[TouchPoint]) -> Tuple[float, float]:
        if not touches:
            return (0.0, 0.0)
        cx = sum(t.position_x for t in touches) / len(touches)
        cy = sum(t.position_y for t in touches) / len(touches)
        return (cx, cy)

    def _compute_touch_distance(self, touches: List[TouchPoint]) -> float:
        if len(touches) < 2:
            return 0.0
        t0, t1 = touches[0], touches[1]
        return math.sqrt(
            (t1.position_x - t0.position_x) ** 2 +
            (t1.position_y - t0.position_y) ** 2
        )

    def _compute_touch_angle(self, touches: List[TouchPoint]) -> float:
        if len(touches) < 2:
            return 0.0
        t0, t1 = touches[0], touches[1]
        return math.degrees(math.atan2(
            t1.position_y - t0.position_y,
            t1.position_x - t0.position_x,
        ))

    def _compute_distance_from_start(
        self, state: _GestureRecognizerState, touches: List[TouchPoint]
    ) -> float:
        centroid = self._compute_centroid(touches)
        return math.sqrt(
            (centroid[0] - state.start_centroid_x) ** 2 +
            (centroid[1] - state.start_centroid_y) ** 2
        )

    def _compute_velocity(
        self, state: _GestureRecognizerState, centroid: Tuple[float, float], now: float
    ) -> Tuple[float, float]:
        dt = now - state.last_event_time
        if dt <= 0:
            return (0.0, 0.0)
        vx = (centroid[0] - state.last_centroid_x) / dt
        vy = (centroid[1] - state.last_centroid_y) / dt
        return (vx, vy)

    def _update_touch_tracker(
        self, touch_points: List[TouchPoint]
    ) -> Dict[int, TouchPoint]:
        active: Dict[int, TouchPoint] = {}
        for tp in self._history:
            if tp.is_active():
                active[tp.touch_id] = tp
        for tp in touch_points:
            if tp.is_active():
                active[tp.touch_id] = tp
            else:
                active.pop(tp.touch_id, None)
        return active

    def _get_relevant_touches(
        self,
        state: _GestureRecognizerState,
        incoming_touches: List[TouchPoint],
        active_touches: Dict[int, TouchPoint],
    ) -> List[TouchPoint]:
        if state.current_state == GestureState.POSSIBLE:
            return incoming_touches

        relevant: List[TouchPoint] = []
        for tid in list(state.tracked_touch_ids):
            tp = active_touches.get(tid)
            if tp:
                relevant.append(tp)
            else:
                for it in incoming_touches:
                    if it.touch_id == tid:
                        relevant.append(it)
                        break

        for tp in incoming_touches:
            if tp.touch_id not in state.tracked_touch_ids and tp.phase == "began":
                relevant.append(tp)

        return relevant

    def _get_config_ids_for_types(self, types: List[GestureType]) -> Set[str]:
        ids: Set[str] = set()
        for t in types:
            ids.update(self._type_to_configs.get(t, []))
        return ids

    def _notify_listeners(self, event: GestureEvent) -> None:
        listeners = self._listeners.get(event.gesture_type, {})
        for callback in list(listeners.values()):
            try:
                callback(event)
            except Exception:
                pass

    def add_gesture_listener(
        self, gesture_type: GestureType, callback: Callable[[GestureEvent], None]
    ) -> str:
        listener_id = uuid.uuid4().hex
        self._listeners[gesture_type][listener_id] = callback
        return listener_id

    def remove_gesture_listener(self, listener_id: str) -> None:
        for listeners in self._listeners.values():
            listeners.pop(listener_id, None)

    def get_active_gestures(self) -> List[GestureEvent]:
        active: List[GestureEvent] = []
        now = time.time()
        for config_id, state in self._recognizers.items():
            if state.current_state in (GestureState.BEGAN, GestureState.CHANGED):
                relevant = [
                    tp for tp in self._history
                    if tp.touch_id in state.tracked_touch_ids and tp.is_active()
                ]
                if relevant:
                    centroid = self._compute_centroid(relevant)
                    scale = 1.0
                    rotation = 0.0
                    if len(relevant) >= 2 and state.start_touch_distance > 0:
                        current_dist = self._compute_touch_distance(relevant)
                        scale = current_dist / state.start_touch_distance
                        current_angle = self._compute_touch_angle(relevant)
                        rotation = current_angle - state.start_touch_angle
                    velocity = self._compute_velocity(state, centroid, now)
                    duration_ms = (now - state.start_time) * 1000.0 if state.start_time > 0 else 0.0

                    active.append(GestureEvent(
                        gesture_type=state.config.gesture_type,
                        state=state.current_state,
                        touch_points=list(relevant),
                        centroid_x=centroid[0],
                        centroid_y=centroid[1],
                        scale=scale,
                        rotation_degrees=rotation,
                        velocity_x=velocity[0],
                        velocity_y=velocity[1],
                        duration_ms=duration_ms,
                        timestamp=now,
                    ))
        return active

    def get_gesture_history(
        self, gesture_type: Optional[GestureType] = None, limit: int = 50
    ) -> List[GestureEvent]:
        events = list(self._event_history)
        if gesture_type is not None:
            events = [e for e in events if e.gesture_type == gesture_type]
        return list(reversed(events))[:limit]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_gestures_recognized": self._total_gestures_recognized,
            "by_type": {
                gt.value: self._by_type_counts.get(gt, 0)
                for gt in GestureType
            },
            "active_recognizers": sum(
                1 for s in self._recognizers.values()
                if s.current_state != GestureState.POSSIBLE
            ),
            "total_registered_configs": len(self._configs),
            "listeners": {
                gt.value: len(listeners)
                for gt, listeners in self._listeners.items()
            },
            "history_size": len(self._event_history),
            "disabled_types": [gt.value for gt in self._disabled_types],
        }

    def reset(self) -> None:
        self._recognizers.clear()
        self._configs.clear()
        self._type_to_configs.clear()
        self._listeners.clear()
        self._history.clear()
        self._event_history.clear()
        self._total_gestures_recognized = 0
        self._by_type_counts.clear()
        self._disabled_types.clear()
        self._builtin_recognizers_installed = False

    def _install_builtin_recognizers(self) -> None:
        """Register default gesture recognizers with sensible thresholds."""
        self._builtin_recognizers_installed = True

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.TAP,
            min_touches=1, max_touches=1,
            min_distance_px=0.0,
            max_duration_ms=300.0,
            priority=100,
            simultaneous_with=[GestureType.PAN],
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.DOUBLE_TAP,
            min_touches=1, max_touches=1,
            taps_required=2,
            max_tap_gap_ms=350.0,
            max_duration_ms=300.0,
            min_distance_px=0.0,
            priority=90,
            require_failure_of=[GestureType.TAP],
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.LONG_PRESS,
            min_touches=1, max_touches=1,
            min_duration_ms=500.0,
            max_duration_ms=2000.0,
            min_distance_px=30.0,
            priority=80,
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.SWIPE,
            min_touches=1, max_touches=1,
            min_distance_px=50.0,
            max_duration_ms=600.0,
            priority=70,
            require_failure_of=[GestureType.PAN],
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.PINCH,
            min_touches=2, max_touches=2,
            min_scale_delta=0.05,
            min_rotation_degrees=0.0,
            priority=60,
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.ROTATE,
            min_touches=2, max_touches=2,
            min_rotation_degrees=5.0,
            priority=55,
            simultaneous_with=[GestureType.PINCH],
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.PAN,
            min_touches=1, max_touches=5,
            min_distance_px=10.0,
            max_duration_ms=5000.0,
            priority=50,
            simultaneous_with=[GestureType.PINCH, GestureType.ROTATE],
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.EDGE_SWIPE,
            min_touches=1, max_touches=1,
            min_distance_px=50.0,
            max_duration_ms=500.0,
            edge_margin_px=30.0,
            priority=85,
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.FORCE_TOUCH,
            min_touches=1, max_touches=1,
            min_duration_ms=100.0,
            max_duration_ms=1000.0,
            min_distance_px=0.0,
            priority=75,
        ))

        self.register_gesture(GestureConfig(
            gesture_type=GestureType.SHAKE,
            min_touches=0, max_touches=0,
            min_duration_ms=200.0,
            max_duration_ms=1000.0,
            priority=40,
        ))


_global_input_gesture_system: Optional[InputGestureSystem] = None


def get_input_gesture_system() -> InputGestureSystem:
    global _global_input_gesture_system
    if _global_input_gesture_system is None:
        _global_input_gesture_system = InputGestureSystem()
    return _global_input_gesture_system


def _get_dependency_ids(config: GestureConfig) -> Set[str]:
    ids: Set[str] = set()
    for gt in config.require_failure_of:
        ids.update({gt.value})
    return ids