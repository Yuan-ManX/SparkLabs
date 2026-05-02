"""
SparkLabs Engine - Input Manager

Unified input management for keyboard, mouse, touch, and gamepad.
Tracks input states across frames with press/release/repeat detection.
Maps raw inputs to named game actions with configurable bindings.

Architecture:
  InputManager
    |-- KeyboardState (per-key press/release/hold tracking)
    |-- MouseState (position, buttons, wheel delta)
    |-- TouchState (multi-touch with unique identifiers)
    |-- ActionMap (named actions bound to input combinations)
    |-- InputAxis (analog axes from keys, mouse, or gamepad)

Input Processing Order per frame:
  1. Gather raw events from platform
  2. Update state buffers (press/release transitions)
  3. Process action bindings (key combos → named actions)
  4. Compute axis values (smooth interpolation)
  5. Reset per-frame deltas (wheel, just-pressed flags)
  6. Invoke action callbacks
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class KeyState(Enum):
    UP = "up"
    PRESSED = "pressed"
    DOWN = "down"
    RELEASED = "released"


@dataclass
class KeyboardSnapshot:
    pressed: Set[str] = field(default_factory=set)
    just_pressed: Set[str] = field(default_factory=set)
    just_released: Set[str] = field(default_factory=set)
    hold_durations: Dict[str, float] = field(default_factory=dict)


@dataclass
class MouseSnapshot:
    x: float = 0.0
    y: float = 0.0
    dx: float = 0.0
    dy: float = 0.0
    left: bool = False
    middle: bool = False
    right: bool = False
    left_pressed: bool = False
    middle_pressed: bool = False
    right_pressed: bool = False
    left_released: bool = False
    wheel_x: float = 0.0
    wheel_y: float = 0.0


@dataclass
class TouchPoint:
    touch_id: int = 0
    x: float = 0.0
    y: float = 0.0
    pressure: float = 1.0
    phase: str = "stationary"


class ActionType(Enum):
    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    AXIS = "axis"


@dataclass
class ActionBinding:
    action_name: str = ""
    action_type: ActionType = ActionType.PRESS
    keys: List[str] = field(default_factory=list)
    mouse_button: Optional[str] = None
    gamepad_button: Optional[str] = None


class InputManager:
    """
    Unified input state manager.

    Aggregates keyboard, mouse, touch, and gamepad input into
    a normalized state accessible by all game systems and AI
    agents. Supports action mapping for game-specific bindings.

    Usage:
        im = InputManager()
        im.map_action("jump", keys=["Space", "W"], mouse_button="left")
        im.simulate_key_press("Space")
        if im.is_action_just_pressed("jump"):
            player.jump()
    """

    def __init__(self):
        self._keyboard = KeyboardSnapshot()
        self._mouse = MouseSnapshot()
        self._touches: Dict[int, TouchPoint] = {}
        self._actions: Dict[str, ActionBinding] = {}
        self._action_callbacks: Dict[str, List[Callable[[], None]]] = {}
        self._axis_bindings: Dict[str, Tuple[List[str], List[str]]] = {}
        self._axis_values: Dict[str, float] = {}
        self._mouse_sensitivity: float = 0.1

    @property
    def keyboard(self) -> KeyboardSnapshot:
        return self._keyboard

    @property
    def mouse(self) -> MouseSnapshot:
        return self._mouse

    def map_action(self, name: str, keys: Optional[List[str]] = None, mouse_button: Optional[str] = None) -> ActionBinding:
        binding = ActionBinding(
            action_name=name,
            action_type=ActionType.PRESS,
            keys=keys or [],
            mouse_button=mouse_button,
        )
        self._actions[name] = binding
        return binding

    def map_axis(self, name: str, positive_keys: List[str], negative_keys: List[str], sensitivity: float = 1.0) -> None:
        self._axis_bindings[name] = (positive_keys, negative_keys)

    def bind_action_callback(self, action_name: str, callback: Callable[[], None]) -> None:
        self._action_callbacks.setdefault(action_name, []).append(callback)

    def is_key_down(self, key: str) -> bool:
        return key.lower() in self._keyboard.pressed

    def is_key_just_pressed(self, key: str) -> bool:
        return key.lower() in self._keyboard.just_pressed

    def is_key_just_released(self, key: str) -> bool:
        return key.lower() in self._keyboard.just_released

    def get_axis(self, name: str) -> float:
        if name in self._axis_values:
            return self._axis_values[name]
        if name in self._axis_bindings:
            pos_keys, neg_keys = self._axis_bindings[name]
            value = 0.0
            for k in pos_keys:
                if self.is_key_down(k):
                    value += 1.0
            for k in neg_keys:
                if self.is_key_down(k):
                    value -= 1.0
            return max(-1.0, min(1.0, value))
        return 0.0

    def is_action_just_pressed(self, action_name: str) -> bool:
        binding = self._actions.get(action_name)
        if not binding:
            return any(k.lower() in self._keyboard.just_pressed for k in action_name.split(","))
        for key in binding.keys:
            if key.lower() in self._keyboard.just_pressed:
                return True
        if binding.mouse_button == "left" and self._mouse.left_pressed:
            return True
        if binding.mouse_button == "right" and self._mouse.right_pressed:
            return True
        return False

    def is_action_held(self, action_name: str) -> bool:
        binding = self._actions.get(action_name)
        if not binding:
            return any(k.lower() in self._keyboard.pressed for k in action_name.split(","))
        for key in binding.keys:
            if key.lower() in self._keyboard.pressed:
                return True
        if binding.mouse_button == "left" and self._mouse.left:
            return True
        return False

    def is_action_just_released(self, action_name: str) -> bool:
        binding = self._actions.get(action_name)
        if not binding:
            return any(k.lower() in self._keyboard.just_released for k in action_name.split(","))
        for key in binding.keys:
            if key.lower() in self._keyboard.just_released:
                return True
        if binding.mouse_button == "left" and self._mouse.left_released:
            return True
        return False

    def simulate_key_press(self, key: str) -> None:
        k = key.lower()
        if k not in self._keyboard.pressed:
            self._keyboard.pressed.add(k)
            self._keyboard.just_pressed.add(k)

    def simulate_key_release(self, key: str) -> None:
        k = key.lower()
        self._keyboard.pressed.discard(k)
        self._keyboard.just_released.add(k)

    def simulate_mouse_move(self, x: float, y: float) -> None:
        self._mouse.dx = x - self._mouse.x
        self._mouse.dy = y - self._mouse.y
        self._mouse.x = x
        self._mouse.y = y

    def simulate_mouse_press(self, button: str) -> None:
        if button == "left":
            self._mouse.left = True
            self._mouse.left_pressed = True
        elif button == "right":
            self._mouse.right = True
            self._mouse.right_pressed = True
        elif button == "middle":
            self._mouse.middle = True
            self._mouse.middle_pressed = True

    def simulate_mouse_release(self, button: str) -> None:
        if button == "left":
            self._mouse.left = False
            self._mouse.left_released = True
        elif button == "right":
            self._mouse.right = False
            self._mouse.right_released = True

    def simulate_touch(self, tid: int, x: float, y: float, phase: str = "began") -> None:
        self._touches[tid] = TouchPoint(touch_id=tid, x=x, y=y, phase=phase)
        if phase in ("ended", "cancelled"):
            self._touches.pop(tid, None)

    def post_update(self) -> None:
        self._keyboard.just_pressed.clear()
        self._keyboard.just_released.clear()
        self._mouse.dx = 0.0
        self._mouse.dy = 0.0
        self._mouse.wheel_x = 0.0
        self._mouse.wheel_y = 0.0
        self._mouse.left_pressed = False
        self._mouse.right_pressed = False
        self._mouse.middle_pressed = False
        self._mouse.left_released = False
        self._mouse.right_released = False

    def process_actions(self) -> List[str]:
        triggered: List[str] = []
        for name, binding in self._actions.items():
            if self.is_action_just_pressed(name):
                triggered.append(name)
                for cb in self._action_callbacks.get(name, []):
                    try:
                        cb()
                    except Exception:
                        pass
        return triggered

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "keyboard": {
                "pressed": list(self._keyboard.pressed),
                "just_pressed": list(self._keyboard.just_pressed),
                "just_released": list(self._keyboard.just_released),
            },
            "mouse": {
                "x": round(self._mouse.x, 1),
                "y": round(self._mouse.y, 1),
                "left": self._mouse.left,
                "right": self._mouse.right,
            },
            "touches": {
                str(tid): {"x": tp.x, "y": tp.y, "phase": tp.phase}
                for tid, tp in self._touches.items()
            },
            "axes": dict(self._axis_values),
        }

    def clear(self) -> None:
        self._keyboard = KeyboardSnapshot()
        self._mouse = MouseSnapshot()
        self._touches.clear()
        self._axis_values.clear()


_global_input_manager: Optional[InputManager] = None


def get_input_manager() -> InputManager:
    global _global_input_manager
    if _global_input_manager is None:
        _global_input_manager = InputManager()
    return _global_input_manager
