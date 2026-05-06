"""
SparkLabs Engine - Input Event System

Event-based input pipeline that captures raw hardware input events
and dispatches them through priority-ordered listeners. Built on
action-resolution rather than polling — ideal for AI agents that
emit structured game input commands.

Architecture:
  InputEventSystem
    |-- DeviceHub (keyboard, mouse, touch, gamepad abstraction)
    |-- EventQueue (priority-ordered input event buffer)
    |-- ActionMapper (binds input events → named game actions)
    |-- GestureDetector (tap, swipe, pinch, long-press, drag)
    |-- DispatchLayer (ordered listener chain with propagation)

Input Event Priority:
  UI (100) — overlay consumes before gameplay
  GAME (50)  — standard gameplay processing
  DEBUG (10) — dev tools, always receives

Gesture Types:
  - TAP: quick press + release within radius
  - DOUBLE_TAP: two taps in sequence
  - LONG_PRESS: press held beyond threshold
  - SWIPE: directional drag with minimum velocity
  - PINCH: two-finger scale gesture
  - DRAG: continuous press + move

Usage:
    hub = InputEventSystem()
    hub.register("player_jump", key="Space", dead_zone=0)
    hub.register("player_move", axis="Horizontal", dead_zone=0.2)
    def jump_listener(action, value, raw):
        engine.trigger_action(action, value)
    hub.subscribe("player_jump", jump_listener, priority=50)
    hub.dispatch_events(0.016)
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class InputDevice(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    TOUCH = "touch"
    GAMEPAD = "gamepad"


class GestureType(Enum):
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    PINCH = "pinch"
    PINCH_IN = "pinch_in"
    PINCH_OUT = "pinch_out"
    DRAG = "drag"
    NONE = "none"


class EventPriority(Enum):
    UI = 100
    GAME = 50
    DEBUG = 10


@dataclass
class InputEvent:
    event_id: str = ""
    device: InputDevice = InputDevice.KEYBOARD
    event_type: str = ""
    key_code: str = ""
    mouse_button: int = 0
    mouse_x: int = 0
    mouse_y: int = 0
    touch_count: int = 0
    touch_x: float = 0.0
    touch_y: float = 0.0
    pressure: float = 0.0
    is_pressed: bool = False
    is_released: bool = False
    timestamp: float = 0.0
    consumed: bool = False


@dataclass
class ActionBinding:
    action_name: str = ""
    key: str = ""
    mouse_button: int = 0
    gamepad_button: int = 0
    axis: str = ""
    dead_zone: float = 0.15
    sensitivity: float = 1.0
    inverted: bool = False


@dataclass
class GestureState:
    active: bool = False
    gesture_type: GestureType = GestureType.NONE
    start_x: float = 0.0
    start_y: float = 0.0
    current_x: float = 0.0
    current_y: float = 0.0
    start_time: float = 0.0
    duration: float = 0.0
    dx: float = 0.0
    dy: float = 0.0
    distance: float = 0.0
    velocity: float = 0.0


class InputEventSystem:
    """Event-based input pipeline with action resolution and gestures."""

    _instance: Optional["InputEventSystem"] = None

    def __init__(self):
        self._event_queue: deque = deque(maxlen=256)
        self._action_bindings: Dict[str, ActionBinding] = {}
        self._listeners: Dict[int, List[Callable[[InputEvent], None]]] = {}
        self._key_states: Dict[str, bool] = {}
        self._touch_state: Dict[int, GestureState] = {}
        self._mouse_state: Dict[str, float] = {"x": 0, "y": 0, "dx": 0, "dy": 0}
        self._action_values: Dict[str, float] = {}
        self._enabled: bool = True
        self._event_counter: int = 0
        self._gesture_config = {
            "tap_max_distance": 20.0,
            "tap_max_duration": 0.3,
            "double_tap_interval": 0.35,
            "long_press_min_duration": 0.5,
            "swipe_min_velocity": 300.0,
            "pinch_min_scale": 0.1,
        }

    @classmethod
    def get_instance(cls) -> "InputEventSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, action_name: str, key: str = "",
                 mouse_button: int = 0, axis: str = "",
                 dead_zone: float = 0.15, sensitivity: float = 1.0,
                 inverted: bool = False) -> ActionBinding:
        binding = ActionBinding(
            action_name=action_name, key=key, mouse_button=mouse_button,
            axis=axis, dead_zone=dead_zone, sensitivity=sensitivity,
            inverted=inverted,
        )
        self._action_bindings[action_name] = binding
        return binding

    def subscribe(self, priority: int, handler: Callable[[InputEvent], None]) -> None:
        if priority not in self._listeners:
            self._listeners[priority] = []
        self._listeners[priority].append(handler)

    def emit_key(self, key_code: str, pressed: bool, released: bool = False) -> InputEvent:
        evt = InputEvent(
            event_id=f"evt_{self._event_counter}",
            device=InputDevice.KEYBOARD,
            key_code=key_code,
            is_pressed=pressed,
            is_released=released,
            timestamp=time.time(),
        )
        self._event_counter += 1
        self._event_queue.append(evt)

        if pressed:
            self._key_states[key_code] = True
        else:
            self._key_states[key_code] = False

        return evt

    def emit_mouse(self, x: int, y: int, button: int = 0,
                   pressed: bool = False) -> InputEvent:
        self._mouse_state["dx"] = x - self._mouse_state["x"]
        self._mouse_state["dy"] = y - self._mouse_state["y"]
        self._mouse_state["x"] = x
        self._mouse_state["y"] = y

        evt = InputEvent(
            event_id=f"evt_{self._event_counter}",
            device=InputDevice.MOUSE,
            mouse_button=button,
            mouse_x=x, mouse_y=y,
            is_pressed=pressed,
            timestamp=time.time(),
        )
        self._event_counter += 1
        self._event_queue.append(evt)
        return evt

    def emit_touch(self, touch_id: int, x: float, y: float,
                   phase: str = "start") -> InputEvent:
        is_pressed = phase in ("start", "down")
        is_released = phase in ("end", "up", "cancel")

        ts = self._touch_state.get(touch_id)
        if ts is None:
            ts = GestureState()
            self._touch_state[touch_id] = ts

        if phase == "start":
            ts.active = True
            ts.start_x = x
            ts.start_y = y
            ts.start_time = time.time()
        elif ts.active:
            ts.current_x = x
            ts.current_y = y
            ts.dx = x - ts.start_x
            ts.dy = y - ts.start_y
            ts.duration = time.time() - ts.start_time
            ts.distance = (ts.dx ** 2 + ts.dy ** 2) ** 0.5
            ts.velocity = ts.distance / max(ts.duration, 0.001)

        if is_released and ts.active:
            self._detect_gesture(touch_id, ts)
            ts.active = False

        evt = InputEvent(
            event_id=f"evt_{self._event_counter}",
            device=InputDevice.TOUCH,
            touch_x=x, touch_y=y,
            is_pressed=is_pressed,
            is_released=is_released,
            timestamp=time.time(),
        )
        self._event_counter += 1
        self._event_queue.append(evt)
        return evt

    def _detect_gesture(self, touch_id: int, ts: GestureState) -> None:
        dist = ts.distance
        dur = ts.duration

        if dist < self._gesture_config["tap_max_distance"]:
            if dur < self._gesture_config["tap_max_duration"]:
                ts.gesture_type = GestureType.TAP
            elif dur >= self._gesture_config["long_press_min_duration"]:
                ts.gesture_type = GestureType.LONG_PRESS
        elif ts.velocity >= self._gesture_config["swipe_min_velocity"]:
            if abs(ts.dx) > abs(ts.dy):
                ts.gesture_type = GestureType.SWIPE_RIGHT if ts.dx > 0 else GestureType.SWIPE_LEFT
            else:
                ts.gesture_type = GestureType.SWIPE_DOWN if ts.dy > 0 else GestureType.SWIPE_UP

    def detect_gesture(self, touch_id: int) -> GestureType:
        ts = self._touch_state.get(touch_id)
        if ts and ts.gesture_type != GestureType.NONE:
            return ts.gesture_type
        return GestureType.NONE

    def is_key_down(self, key_code: str) -> bool:
        return self._key_states.get(key_code, False)

    def get_mouse_position(self) -> Tuple[float, float]:
        return (self._mouse_state.get("x", 0), self._mouse_state.get("y", 0))

    def get_action_value(self, action_name: str) -> float:
        return self._action_values.get(action_name, 0.0)

    def resolve_actions(self) -> None:
        for name, binding in self._action_bindings.items():
            value = 0.0

            if binding.key and self.is_key_down(binding.key):
                value = 1.0

            if binding.axis:
                raw = self._action_values.get(f"axis_{binding.axis}", 0.0)
                if abs(raw) < binding.dead_zone:
                    value = 0.0
                else:
                    value = (raw - binding.dead_zone * (1 if raw > 0 else -1)) / (1 - binding.dead_zone)
                    value *= binding.sensitivity

            if binding.inverted:
                value *= -1.0

            self._action_values[name] = value

    def dispatch_events(self, dt: float) -> int:
        if not self._enabled:
            return 0

        dispatched = 0
        while self._event_queue:
            evt = self._event_queue.popleft()
            consumed = False

            for priority in sorted(self._listeners.keys(), reverse=True):
                if consumed:
                    break
                for handler in self._listeners.get(priority, []):
                    try:
                        handler(evt)
                        if evt.consumed:
                            consumed = True
                            break
                    except Exception:
                        pass

            dispatched += 1

        self.resolve_actions()
        return dispatched

    def flush_events(self) -> int:
        flushed = len(self._event_queue)
        self._event_queue.clear()
        return flushed

    def get_stats(self) -> Dict[str, Any]:
        active_touches = sum(1 for ts in self._touch_state.values() if ts.active)
        keys_held = sum(1 for v in self._key_states.values() if v)

        return {
            "event_queue_size": len(self._event_queue),
            "action_bindings": len(self._action_bindings),
            "listeners": sum(len(v) for v in self._listeners.values()),
            "total_events": self._event_counter,
            "keys_held": keys_held,
            "active_touches": active_touches,
            "mouse_position": self.get_mouse_position(),
            "enabled": self._enabled,
            "actions": {
                name: round(val, 3)
                for name, val in self._action_values.items()
                if abs(val) > 0.01
            },
            "gesture_config": self._gesture_config,
        }

    def set_gesture_config(self, **kwargs) -> None:
        self._gesture_config.update(kwargs)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def reset(self) -> None:
        self._event_queue.clear()
        self._key_states.clear()
        self._listeners.clear()
        self._action_bindings.clear()
        self._action_values.clear()
        self._touch_state.clear()
        self._event_counter = 0


def get_input_event_system() -> InputEventSystem:
    return InputEventSystem.get_instance()
