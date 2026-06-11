"""
SparkAI Engine - Input Mapping System

Flexible input binding system with action maps, chord detection,
and input state management. Maps raw device input to named game
actions with priority-based action maps, analog dead zone processing,
key chord detection, and per-frame state tracking.

Architecture:
  EngineInputMapping
    |-- ActionMap (named, prioritized collection of actions)
    |-- ActionDefinition (action metadata with default bindings)
    |-- InputBinding (device input → action link with chord modifiers)
    |-- InputState (per-action runtime state tracking)
    |-- InputFrame (snapshot of all active inputs for a single frame)
    |-- ChordDefinition (multi-key simultaneous press detection)

Input Flow:
  1. Raw device events arrive via process_* methods
  2. Chord detection evaluates modifier key combinations
  3. Bindings are resolved across enabled action maps by priority
  4. Input states are updated with pressed/released/held transitions
  5. build_frame() snapshots state and resets per-frame flags
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InputDevice(str, Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"
    TOUCH = "touch"


class InputEventType(str, Enum):
    PRESSED = "pressed"
    RELEASED = "released"
    HELD = "held"
    AXIS = "axis"


class ActionType(str, Enum):
    DIGITAL = "digital"
    ANALOG_1D = "analog-1d"
    ANALOG_2D = "analog-2d"


class ChordModifier(str, Enum):
    NONE = "none"
    SHIFT = "shift"
    CTRL = "ctrl"
    ALT = "alt"


class InputZone(str, Enum):
    MOVE = "move"
    AIM = "aim"
    ACTION = "action"
    UI = "ui"
    MENU = "menu"
    DEBUG = "debug"


class DeadZoneMode(str, Enum):
    RADIAL = "radial"
    AXIAL = "axial"
    SCALED_RADIAL = "scaled-radial"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class InputBinding:
    binding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_name: str = ""
    device: InputDevice = InputDevice.KEYBOARD
    input_code: str = ""
    event_type: InputEventType = InputEventType.PRESSED
    scale: float = 1.0
    chord_modifier: ChordModifier = ChordModifier.NONE
    chord_key: str = ""
    zone: InputZone = InputZone.ACTION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "action_name": self.action_name,
            "device": self.device.value,
            "input_code": self.input_code,
            "event_type": self.event_type.value,
            "scale": self.scale,
            "chord_modifier": self.chord_modifier.value,
            "chord_key": self.chord_key,
            "zone": self.zone.value,
        }


@dataclass
class ActionDefinition:
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    display_name: str = ""
    action_type: ActionType = ActionType.DIGITAL
    default_bindings: List[InputBinding] = field(default_factory=list)
    analog_dead_zone: float = 0.2
    analog_sensitivity: float = 1.0
    is_toggle: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "display_name": self.display_name,
            "action_type": self.action_type.value,
            "default_bindings": [b.to_dict() for b in self.default_bindings],
            "analog_dead_zone": self.analog_dead_zone,
            "analog_sensitivity": self.analog_sensitivity,
            "is_toggle": self.is_toggle,
        }


@dataclass
class InputState:
    action_name: str = ""
    value: float = 0.0
    value_x: float = 0.0
    value_y: float = 0.0
    pressed: bool = False
    released: bool = False
    held: bool = False
    duration: float = 0.0
    last_change_time: float = 0.0
    chord_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_name": self.action_name,
            "value": self.value,
            "value_x": self.value_x,
            "value_y": self.value_y,
            "pressed": self.pressed,
            "released": self.released,
            "held": self.held,
            "duration": round(self.duration, 4),
            "last_change_time": self.last_change_time,
            "chord_active": self.chord_active,
        }


@dataclass
class ActionMap:
    map_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "default"
    priority: int = 0
    enabled: bool = True
    actions: Dict[str, ActionDefinition] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "map_id": self.map_id,
            "name": self.name,
            "priority": self.priority,
            "enabled": self.enabled,
            "actions": {name: a.to_dict() for name, a in self.actions.items()},
        }


@dataclass
class InputFrame:
    frame_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = 0.0
    actions: Dict[str, InputState] = field(default_factory=dict)
    mouse_position: Tuple[float, float] = (0.0, 0.0)
    mouse_delta: Tuple[float, float] = (0.0, 0.0)
    scroll_delta: Tuple[float, float] = (0.0, 0.0)
    chord_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "actions": {name: s.to_dict() for name, s in self.actions.items()},
            "mouse_position": self.mouse_position,
            "mouse_delta": self.mouse_delta,
            "scroll_delta": self.scroll_delta,
            "chord_active": self.chord_active,
        }


@dataclass
class ChordDefinition:
    chord_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    keys: List[str] = field(default_factory=list)
    action_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chord_id": self.chord_id,
            "name": self.name,
            "keys": self.keys,
            "action_name": self.action_name,
        }


# ---------------------------------------------------------------------------
# EngineInputMapping — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class EngineInputMapping:
    """
    Flexible input binding system with action maps, chord detection,
    and input state management.

    Maps raw device input (keyboard, mouse, gamepad, touch) to named
    game actions through prioritized action maps. Supports analog dead
    zone processing, key chord detection with modifier keys, and
    per-frame pressed/released/held state tracking.

    Thread-safe via a reentrant lock. Use get_input_mapping() or
    EngineInputMapping.get_instance() to obtain the singleton instance.

    Usage:
        im = get_input_mapping()
        am = im.create_action_map("gameplay", priority=10)
        im.register_action(
            am.map_id,
            ActionDefinition(name="jump", display_name="Jump", action_type=ActionType.DIGITAL),
        )
        im.bind_input(
            am.map_id,
            "jump",
            InputBinding(action_name="jump", input_code="Space", event_type=InputEventType.PRESSED),
        )
        im.process_key_event("Space", True)
        if im.is_action_pressed("jump"):
            player.jump()
    """

    _instance: Optional["EngineInputMapping"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineInputMapping":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineInputMapping":
        return cls()

    def _initialize(self) -> None:
        self._action_maps: Dict[str, ActionMap] = {}
        self._input_states: Dict[str, InputState] = {}
        self._key_codes: Dict[str, int] = {}
        self._mouse_position: Tuple[float, float] = (0.0, 0.0)
        self._mouse_delta: Tuple[float, float] = (0.0, 0.0)
        self._scroll_delta: Tuple[float, float] = (0.0, 0.0)
        self._pressed_buttons: Set[int] = set()
        self._pressed_keys: Set[str] = set()
        self._creation_counter: int = 0

        self._chords: Dict[str, ChordDefinition] = {}
        self._modifier_keys: Dict[ChordModifier, str] = {
            ChordModifier.SHIFT: "ShiftLeft",
            ChordModifier.CTRL: "ControlLeft",
            ChordModifier.ALT: "AltLeft",
        }

    # ------------------------------------------------------------------
    # Action Map Management
    # ------------------------------------------------------------------

    def create_action_map(self, name: str, priority: int = 0) -> ActionMap:
        with self._lock:
            am = ActionMap(name=name, priority=priority)
            self._action_maps[am.map_id] = am
            self._creation_counter += 1
            return am

    def register_action(self, map_id: str, action: ActionDefinition) -> bool:
        with self._lock:
            am = self._action_maps.get(map_id)
            if am is None:
                return False
            am.actions[action.name] = action
            if action.name not in self._input_states:
                self._input_states[action.name] = InputState(action_name=action.name)
            return True

    def bind_input(self, map_id: str, action_name: str, binding: InputBinding) -> bool:
        with self._lock:
            am = self._action_maps.get(map_id)
            if am is None:
                return False
            action = am.actions.get(action_name)
            if action is None:
                return False
            binding.action_name = action_name
            action.default_bindings.append(binding)
            return True

    # ------------------------------------------------------------------
    # Chord Management
    # ------------------------------------------------------------------

    def register_chord(self, chord: ChordDefinition) -> str:
        with self._lock:
            self._chords[chord.chord_id] = chord
            return chord.chord_id

    def _check_chords(self) -> List[str]:
        triggered: List[str] = []
        for chord in self._chords.values():
            all_held = all(k in self._pressed_keys for k in chord.keys)
            if all_held and chord.action_name:
                triggered.append(chord.action_name)
        return triggered

    # ------------------------------------------------------------------
    # Binding Resolution
    # ------------------------------------------------------------------

    def _find_bindings(self, action_name: str) -> List[InputBinding]:
        results: List[InputBinding] = []
        sorted_maps = sorted(
            [am for am in self._action_maps.values() if am.enabled],
            key=lambda am: -am.priority,
        )
        for am in sorted_maps:
            action = am.actions.get(action_name)
            if action is not None and action.default_bindings:
                results.extend(action.default_bindings)
        return results

    def _resolve_input(
        self, device: InputDevice, input_code: str, event_type: InputEventType, value: float = 1.0
    ) -> Dict[str, InputState]:
        triggered: Dict[str, InputState] = {}
        sorted_maps = sorted(
            [am for am in self._action_maps.values() if am.enabled],
            key=lambda am: -am.priority,
        )

        current_modifier = self._get_active_modifier()
        chord_actions = self._check_chords()

        for am in sorted_maps:
            for action_name, action_def in am.actions.items():
                for binding in action_def.default_bindings:
                    if binding.device != device:
                        continue
                    if binding.input_code.lower() != input_code.lower():
                        continue
                    if binding.event_type != event_type:
                        continue

                    modifier_match = self._check_modifier_match(binding, current_modifier)
                    if not modifier_match:
                        continue

                    state = self._input_states.get(action_name)
                    if state is None:
                        state = InputState(action_name=action_name)
                        self._input_states[action_name] = state

                    now = _time_module.time()
                    scaled_value = value * binding.scale

                    if action_def.action_type == ActionType.ANALOG_2D:
                        if event_type == InputEventType.PRESSED:
                            state.pressed = True
                            state.held = True
                            state.last_change_time = now
                            state.chord_active = current_modifier != ChordModifier.NONE
                        elif event_type == InputEventType.RELEASED:
                            state.released = True
                            state.held = False
                            state.last_change_time = now
                            state.chord_active = False
                    elif action_def.action_type == ActionType.ANALOG_1D:
                        dead_zone = action_def.analog_dead_zone
                        sensitivity = action_def.analog_sensitivity
                        processed = self.apply_dead_zone(
                            scaled_value, DeadZoneMode.AXIAL, dead_zone
                        ) * sensitivity
                        state.value = max(-1.0, min(1.0, processed))
                        if abs(state.value) > 0.001:
                            state.held = True
                            state.last_change_time = now
                        else:
                            state.held = False
                            state.released = True
                            state.last_change_time = now
                    else:
                        if event_type == InputEventType.PRESSED:
                            was_held = state.held
                            state.pressed = not was_held
                            state.held = True
                            state.value = scaled_value
                            state.last_change_time = now
                            state.chord_active = current_modifier != ChordModifier.NONE
                        elif event_type == InputEventType.RELEASED:
                            state.released = True
                            state.held = False
                            state.value = 0.0
                            state.duration = 0.0
                            state.last_change_time = now
                            state.chord_active = False
                        elif event_type == InputEventType.HELD:
                            if state.held:
                                state.duration = now - state.last_change_time
                                state.pressed = False

                    triggered[action_name] = state

        for chord_action in chord_actions:
            if chord_action not in triggered:
                state = self._input_states.get(chord_action)
                if state is None:
                    state = InputState(action_name=chord_action)
                    self._input_states[chord_action] = state
                if not state.held:
                    state.pressed = True
                state.held = True
                state.value = 1.0
                state.chord_active = True
                state.last_change_time = _time_module.time()
                triggered[chord_action] = state

        return triggered

    def _get_active_modifier(self) -> ChordModifier:
        alt_keys = {"AltLeft", "AltRight", "alt"}
        ctrl_keys = {"ControlLeft", "ControlRight", "ctrl"}
        shift_keys = {"ShiftLeft", "ShiftRight", "shift"}

        if self._pressed_keys & shift_keys:
            return ChordModifier.SHIFT
        if self._pressed_keys & ctrl_keys:
            return ChordModifier.CTRL
        if self._pressed_keys & alt_keys:
            return ChordModifier.ALT
        return ChordModifier.NONE

    def _check_modifier_match(
        self, binding: InputBinding, current_modifier: ChordModifier
    ) -> bool:
        if binding.chord_modifier == ChordModifier.NONE:
            return current_modifier == ChordModifier.NONE
        if binding.chord_modifier != current_modifier:
            return False
        if binding.chord_key:
            return binding.chord_key.lower() in self._pressed_keys
        return True

    # ------------------------------------------------------------------
    # Input Processing
    # ------------------------------------------------------------------

    def process_key_event(self, key_code: str, pressed: bool) -> Dict[str, InputState]:
        with self._lock:
            if pressed:
                self._pressed_keys.add(key_code)
                event_type = InputEventType.PRESSED
            else:
                self._pressed_keys.discard(key_code)
                event_type = InputEventType.RELEASED

            return self._resolve_input(InputDevice.KEYBOARD, key_code, event_type)

    def process_mouse_event(
        self, button_code: str, pressed: bool, x: float, y: float
    ) -> Dict[str, InputState]:
        with self._lock:
            self._mouse_position = (x, y)
            if pressed:
                event_type = InputEventType.PRESSED
            else:
                event_type = InputEventType.RELEASED

            return self._resolve_input(InputDevice.MOUSE, button_code, event_type)

    def process_mouse_move(
        self, x: float, y: float, delta_x: float = 0.0, delta_y: float = 0.0
    ) -> None:
        with self._lock:
            prev_x, prev_y = self._mouse_position
            self._mouse_position = (x, y)
            if delta_x != 0.0 or delta_y != 0.0:
                self._mouse_delta = (delta_x, delta_y)
            else:
                self._mouse_delta = (x - prev_x, y - prev_y)

    def process_scroll(self, delta_x: float, delta_y: float) -> None:
        with self._lock:
            self._scroll_delta = (delta_x, delta_y)

    def process_gamepad_button(
        self, gamepad_id: int, button_code: str, pressed: bool
    ) -> Dict[str, InputState]:
        with self._lock:
            if pressed:
                self._pressed_buttons.add(hash(button_code))
                event_type = InputEventType.PRESSED
            else:
                self._pressed_buttons.discard(hash(button_code))
                event_type = InputEventType.RELEASED

            return self._resolve_input(InputDevice.GAMEPAD, button_code, event_type)

    def process_gamepad_axis(
        self, gamepad_id: int, axis_code: str, value: float
    ) -> Dict[str, InputState]:
        with self._lock:
            return self._resolve_input(InputDevice.GAMEPAD, axis_code, InputEventType.AXIS, value)

    # ------------------------------------------------------------------
    # Action State Queries
    # ------------------------------------------------------------------

    def get_action_state(self, action_name: str) -> InputState:
        with self._lock:
            state = self._input_states.get(action_name)
            if state is None:
                return InputState(action_name=action_name)
            return state

    def is_action_pressed(self, action_name: str) -> bool:
        with self._lock:
            state = self._input_states.get(action_name)
            return state.pressed if state else False

    def is_action_released(self, action_name: str) -> bool:
        with self._lock:
            state = self._input_states.get(action_name)
            return state.released if state else False

    def is_action_held(self, action_name: str) -> bool:
        with self._lock:
            state = self._input_states.get(action_name)
            return state.held if state else False

    def get_action_value(self, action_name: str) -> float:
        with self._lock:
            state = self._input_states.get(action_name)
            return state.value if state else 0.0

    def get_action_axis_2d(self, action_name: str) -> Tuple[float, float]:
        with self._lock:
            state = self._input_states.get(action_name)
            if state is None:
                return (0.0, 0.0)
            return (state.value_x, state.value_y)

    def get_held_duration(self, action_name: str) -> float:
        with self._lock:
            state = self._input_states.get(action_name)
            if state is None:
                return 0.0
            if state.held:
                state.duration = _time_module.time() - state.last_change_time
            return state.duration

    # ------------------------------------------------------------------
    # Frame Management
    # ------------------------------------------------------------------

    def build_frame(self) -> InputFrame:
        with self._lock:
            frame = InputFrame(
                timestamp=_time_module.time(),
                actions={
                    name: InputState(
                        action_name=s.action_name,
                        value=s.value,
                        value_x=s.value_x,
                        value_y=s.value_y,
                        pressed=s.pressed,
                        released=s.released,
                        held=s.held,
                        duration=s.duration,
                        last_change_time=s.last_change_time,
                        chord_active=s.chord_active,
                    )
                    for name, s in self._input_states.items()
                },
                mouse_position=self._mouse_position,
                mouse_delta=self._mouse_delta,
                scroll_delta=self._scroll_delta,
                chord_active=self._get_active_modifier() != ChordModifier.NONE,
            )

            for state in self._input_states.values():
                state.pressed = False
                state.released = False

            self._mouse_delta = (0.0, 0.0)
            self._scroll_delta = (0.0, 0.0)

            for state in self._input_states.values():
                if not state.held:
                    state.duration = 0.0
                else:
                    state.duration = frame.timestamp - state.last_change_time

            return frame

    # ------------------------------------------------------------------
    # Dead Zone Processing
    # ------------------------------------------------------------------

    def apply_dead_zone(
        self,
        value: float,
        mode: DeadZoneMode = DeadZoneMode.RADIAL,
        threshold: float = 0.2,
    ) -> float:
        abs_value = abs(value)
        if abs_value <= threshold:
            return 0.0

        if mode == DeadZoneMode.AXIAL:
            sign = 1.0 if value > 0 else -1.0
            normalized = (abs_value - threshold) / (1.0 - threshold)
            return sign * normalized

        if mode == DeadZoneMode.RADIAL:
            normalized = (abs_value - threshold) / (1.0 - threshold)
            return normalized * (1.0 if value > 0 else -1.0)

        if mode == DeadZoneMode.SCALED_RADIAL:
            normalized = (abs_value - threshold) / (1.0 - threshold)
            scaled = normalized * normalized
            return scaled * (1.0 if value > 0 else -1.0)

        return value

    # ------------------------------------------------------------------
    # Map State Control
    # ------------------------------------------------------------------

    def set_action_map_enabled(self, map_id: str, enabled: bool) -> bool:
        with self._lock:
            am = self._action_maps.get(map_id)
            if am is None:
                return False
            am.enabled = enabled
            return True

    def disable_all_maps(self) -> None:
        with self._lock:
            for am in self._action_maps.values():
                am.enabled = False

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_input_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_actions = sum(
                len(am.actions) for am in self._action_maps.values()
            )
            total_bindings = sum(
                len(a.default_bindings)
                for am in self._action_maps.values()
                for a in am.actions.values()
            )
            active_maps = sum(
                1 for am in self._action_maps.values() if am.enabled
            )
            held_actions = sum(
                1 for s in self._input_states.values() if s.held
            )
            return {
                "active_maps": active_maps,
                "total_actions": total_actions,
                "total_bindings": total_bindings,
                "active_chords": len(self._chords),
                "held_actions": held_actions,
            }


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_input_mapping() -> EngineInputMapping:
    return EngineInputMapping.get_instance()