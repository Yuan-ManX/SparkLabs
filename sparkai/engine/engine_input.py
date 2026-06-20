"""
SparkLabs Engine - Input System

Complete input management for keyboard, mouse, touch, and gamepad.
Handles action mapping, input buffering, gesture recognition, and
event subscription with thread-safe singleton access.

Architecture:
  InputEngine (Singleton)
    |-- InputState     — per-frame snapshot of all device states
    |-- InputEvent     — timestamped raw input event with metadata
    |-- InputAction    — named game action with device bindings
    |-- GestureEvent   — recognized touch/motion gesture result
    |-- GestureDetector — tap, double-tap, long-press, swipe, pinch, rotate

Input Processing Order per frame:
  1. Platform feeds raw events via process_event()
  2. State buffers updated (press/release transitions)
  3. Action bindings evaluated (raw input → named actions)
  4. Gesture detection on touch sequences
  5. Subscriber callbacks dispatched
  6. update_actions() called to finalize per-frame state
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InputDeviceType(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    TOUCH = "touch"
    GAMEPAD = "gamepad"


class InputEventType(Enum):
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    MOUSE_MOVE = "mouse_move"
    MOUSE_WHEEL = "mouse_wheel"
    TOUCH_START = "touch_start"
    TOUCH_MOVE = "touch_move"
    TOUCH_END = "touch_end"
    GAMEPAD_BUTTON = "gamepad_button"
    GAMEPAD_AXIS = "gamepad_axis"


class GestureType(Enum):
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    PINCH = "pinch"
    ROTATE = "rotate"


class ActionTriggerType(Enum):
    PRESSED = "pressed"
    RELEASED = "released"
    HELD = "held"
    DOUBLE_TAP = "double_tap"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class InputEvent:
    """A single raw input event with device and timing metadata."""

    event_id: str
    event_type: InputEventType
    device_type: InputDeviceType
    timestamp: float
    key_code: Optional[str] = None
    key_name: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    dx: float = 0.0
    dy: float = 0.0
    button: Optional[int] = None
    pressure: float = 1.0
    modifiers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "device_type": self.device_type.value,
            "timestamp": self.timestamp,
            "key_code": self.key_code,
            "key_name": self.key_name,
            "x": self.x,
            "y": self.y,
            "dx": self.dx,
            "dy": self.dy,
            "button": self.button,
            "pressure": self.pressure,
            "modifiers": list(self.modifiers),
        }


@dataclass
class InputAction:
    """A named game action bound to one or more device inputs."""

    action_id: str
    name: str
    bindings: List[Dict[str, Any]] = field(default_factory=list)
    trigger_type: ActionTriggerType = ActionTriggerType.PRESSED
    is_active: bool = False
    hold_duration: float = 0.0
    activation_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "bindings": [dict(b) for b in self.bindings],
            "trigger_type": self.trigger_type.value,
            "is_active": self.is_active,
            "hold_duration": self.hold_duration,
            "activation_count": self.activation_count,
        }


@dataclass
class GestureEvent:
    """A recognized gesture with position, timing, and transform data."""

    gesture_id: str
    gesture_type: GestureType
    start_x: float
    start_y: float
    current_x: float
    current_y: float
    end_x: float = 0.0
    end_y: float = 0.0
    duration: float = 0.0
    distance: float = 0.0
    direction: str = ""
    scale: float = 1.0
    rotation: float = 0.0
    device_type: InputDeviceType = InputDeviceType.TOUCH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gesture_id": self.gesture_id,
            "gesture_type": self.gesture_type.value,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "current_x": self.current_x,
            "current_y": self.current_y,
            "end_x": self.end_x,
            "end_y": self.end_y,
            "duration": self.duration,
            "distance": self.distance,
            "direction": self.direction,
            "scale": self.scale,
            "rotation": self.rotation,
            "device_type": self.device_type.value,
        }


@dataclass
class InputState:
    """Per-frame snapshot of all input device states."""

    keys_pressed: Set[str] = field(default_factory=set)
    keys_just_pressed: Set[str] = field(default_factory=set)
    keys_just_released: Set[str] = field(default_factory=set)
    mouse_x: float = 0.0
    mouse_y: float = 0.0
    mouse_dx: float = 0.0
    mouse_dy: float = 0.0
    mouse_buttons: Dict[int, bool] = field(default_factory=dict)
    mouse_wheel: float = 0.0
    touch_points: Dict[int, Tuple[float, float]] = field(default_factory=dict)
    gamepad_buttons: Dict[int, float] = field(default_factory=dict)
    gamepad_axes: Dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keys_pressed": sorted(self.keys_pressed),
            "keys_just_pressed": sorted(self.keys_just_pressed),
            "keys_just_released": sorted(self.keys_just_released),
            "mouse_x": self.mouse_x,
            "mouse_y": self.mouse_y,
            "mouse_dx": self.mouse_dx,
            "mouse_dy": self.mouse_dy,
            "mouse_buttons": {
                str(k): v for k, v in self.mouse_buttons.items()
            },
            "mouse_wheel": self.mouse_wheel,
            "touch_points": {
                str(k): list(v) for k, v in self.touch_points.items()
            },
            "gamepad_buttons": {
                str(k): v for k, v in self.gamepad_buttons.items()
            },
            "gamepad_axes": {
                str(k): v for k, v in self.gamepad_axes.items()
            },
        }


# ---------------------------------------------------------------------------
# Gesture Detection Constants
# ---------------------------------------------------------------------------

_TAP_MAX_DURATION = 0.3  # seconds
_TAP_MAX_DISTANCE = 30.0  # pixels
_DOUBLE_TAP_MAX_INTERVAL = 0.5  # seconds between taps
_LONG_PRESS_MIN_DURATION = 0.5  # seconds
_SWIPE_MIN_DISTANCE = 50.0  # pixels
_PINCH_MIN_SCALE = 0.5
_PINCH_MAX_SCALE = 2.0


# ---------------------------------------------------------------------------
# InputEngine Singleton
# ---------------------------------------------------------------------------

_engine_instance: Optional[InputEngine] = None
_engine_lock: threading.RLock = threading.RLock()


class InputEngine:
    """
    Central input system managing keyboard, mouse, touch, and gamepad.

    Thread-safe singleton accessed via get_input_engine(). Processes raw
    platform events, resolves action bindings, detects gestures, and
    dispatches to subscribers.
    """

    def __init__(self) -> None:
        self._actions: Dict[str, InputAction] = {}
        self._event_history: List[InputEvent] = []
        self._gesture_tracker: Dict[int, Dict[str, Any]] = {}
        self._tap_history: Dict[int, Dict[str, Any]] = {}
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._event_callbacks: Dict[InputEventType, List[str]] = {
            et: [] for et in InputEventType
        }
        self._current_state: InputState = InputState()
        self._previous_state: InputState = InputState()
        self._lock: threading.RLock = threading.RLock()
        self._max_history: int = 1000

        # Per-frame action state tracking
        self._actions_just_pressed: Set[str] = set()
        self._actions_just_released: Set[str] = set()
        self._actions_held: Set[str] = set()

        # Double-tap tracking per action
        self._action_last_press_time: Dict[str, float] = {}

        # Mouse button per-frame tracking
        self._mouse_buttons_just_pressed: Set[int] = set()
        self._mouse_buttons_just_released: Set[int] = set()

        # Stats
        self._total_events_processed: int = 0
        self._total_gestures_detected: int = 0

    # ------------------------------------------------------------------
    # Event Processing
    # ------------------------------------------------------------------

    def process_event(
        self,
        event_type: InputEventType,
        device_type: InputDeviceType,
        **kwargs: Any,
    ) -> InputEvent:
        """
        Process a raw input event, update state, and dispatch to subscribers.

        Returns the created InputEvent.
        """
        event = InputEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            device_type=device_type,
            timestamp=time.time(),
            key_code=kwargs.get("key_code"),
            key_name=kwargs.get("key_name"),
            x=float(kwargs.get("x", 0.0)),
            y=float(kwargs.get("y", 0.0)),
            dx=float(kwargs.get("dx", 0.0)),
            dy=float(kwargs.get("dy", 0.0)),
            button=kwargs.get("button"),
            pressure=float(kwargs.get("pressure", 1.0)),
            modifiers=list(kwargs.get("modifiers", [])),
        )

        with self._lock:
            self._apply_event_to_state(event)
            self._evaluate_action_bindings(event)
            self._append_to_history(event)
            self._total_events_processed += 1

        self._dispatch_to_subscribers(event)

        return event

    def _apply_event_to_state(self, event: InputEvent) -> None:
        """Update internal state buffers based on the event type."""
        state = self._current_state

        if event.event_type == InputEventType.KEY_DOWN:
            if event.key_code:
                state.keys_pressed.add(event.key_code)
                state.keys_just_pressed.add(event.key_code)

        elif event.event_type == InputEventType.KEY_UP:
            if event.key_code:
                state.keys_pressed.discard(event.key_code)
                state.keys_just_released.add(event.key_code)

        elif event.event_type == InputEventType.MOUSE_MOVE:
            state.mouse_x = event.x
            state.mouse_y = event.y
            state.mouse_dx += event.dx
            state.mouse_dy += event.dy

        elif event.event_type == InputEventType.MOUSE_DOWN:
            if event.button is not None:
                state.mouse_buttons[event.button] = True
                self._mouse_buttons_just_pressed.add(event.button)

        elif event.event_type == InputEventType.MOUSE_UP:
            if event.button is not None:
                state.mouse_buttons[event.button] = False
                self._mouse_buttons_just_released.add(event.button)

        elif event.event_type == InputEventType.MOUSE_WHEEL:
            state.mouse_wheel += event.dy

        elif event.event_type == InputEventType.TOUCH_START:
            state.touch_points[event.button or 0] = (event.x, event.y)

        elif event.event_type == InputEventType.TOUCH_MOVE:
            state.touch_points[event.button or 0] = (event.x, event.y)

        elif event.event_type == InputEventType.TOUCH_END:
            state.touch_points.pop(event.button or 0, None)

        elif event.event_type == InputEventType.GAMEPAD_BUTTON:
            if event.button is not None:
                state.gamepad_buttons[event.button] = event.pressure

        elif event.event_type == InputEventType.GAMEPAD_AXIS:
            if event.button is not None:
                state.gamepad_axes[event.button] = event.x

    def _append_to_history(self, event: InputEvent) -> None:
        """Add event to history buffer, trimming if over max."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    # ------------------------------------------------------------------
    # Action Binding
    # ------------------------------------------------------------------

    def _event_matches_binding(
        self, event: InputEvent, binding: Dict[str, Any]
    ) -> bool:
        """Check whether an input event matches a single action binding."""
        device = binding.get("device", "")
        if device and event.device_type.value != device:
            return False

        if event.device_type == InputDeviceType.KEYBOARD:
            bound_key = binding.get("key")
            if bound_key and event.key_code != bound_key:
                return False

        elif event.device_type == InputDeviceType.MOUSE:
            bound_button = binding.get("button")
            if bound_button is not None and event.button != bound_button:
                return False

        elif event.device_type == InputDeviceType.GAMEPAD:
            bound_button = binding.get("button")
            bound_axis = binding.get("axis")
            if bound_button is not None and event.button != bound_button:
                return False
            if bound_axis is not None and event.event_type != InputEventType.GAMEPAD_AXIS:
                return False

        elif event.device_type == InputDeviceType.TOUCH:
            bound_button = binding.get("button")
            if bound_button is not None and event.button != bound_button:
                return False

        return True

    def _evaluate_action_bindings(self, event: InputEvent) -> None:
        """Check all registered actions against the incoming event."""
        is_press = event.event_type in (
            InputEventType.KEY_DOWN,
            InputEventType.MOUSE_DOWN,
            InputEventType.TOUCH_START,
            InputEventType.GAMEPAD_BUTTON,
        )
        is_release = event.event_type in (
            InputEventType.KEY_UP,
            InputEventType.MOUSE_UP,
            InputEventType.TOUCH_END,
        )

        for action in self._actions.values():
            for binding in action.bindings:
                if not self._event_matches_binding(event, binding):
                    continue

                if is_press:
                    self._handle_action_press(action, event.timestamp)
                elif is_release:
                    self._handle_action_release(action)
                break

    def _handle_action_press(self, action: InputAction, timestamp: float) -> None:
        """Handle activation press for a mapped action."""
        if action.trigger_type == ActionTriggerType.DOUBLE_TAP:
            last_time = self._action_last_press_time.get(action.name, 0.0)
            if timestamp - last_time <= _DOUBLE_TAP_MAX_INTERVAL:
                action.is_active = True
                action.activation_count += 1
                self._actions_just_pressed.add(action.name)
                self._actions_held.add(action.name)
                self._action_last_press_time[action.name] = 0.0
            else:
                self._action_last_press_time[action.name] = timestamp
            return

        if not action.is_active:
            action.is_active = True
            action.activation_count += 1
            action.hold_duration = 0.0
            self._actions_just_pressed.add(action.name)
            self._actions_held.add(action.name)

    def _handle_action_release(self, action: InputAction) -> None:
        """Handle release for a mapped action."""
        if action.trigger_type == ActionTriggerType.DOUBLE_TAP:
            return

        if action.is_active:
            action.is_active = False
            self._actions_just_released.add(action.name)
            self._actions_held.discard(action.name)

    def register_action(
        self,
        name: str,
        bindings: List[Dict[str, Any]],
        trigger_type: ActionTriggerType = ActionTriggerType.PRESSED,
    ) -> InputAction:
        """Register a named action with device bindings."""
        with self._lock:
            action = InputAction(
                action_id=str(uuid.uuid4()),
                name=name,
                bindings=bindings,
                trigger_type=trigger_type,
            )
            self._actions[name] = action
            return action

    def get_action(self, name: str) -> Optional[InputAction]:
        """Get a registered action by name."""
        with self._lock:
            return self._actions.get(name)

    def is_action_active(self, name: str) -> bool:
        """Check if an action is currently held."""
        with self._lock:
            action = self._actions.get(name)
            return action.is_active if action else False

    def is_action_just_pressed(self, name: str) -> bool:
        """Check if an action was pressed this frame."""
        with self._lock:
            return name in self._actions_just_pressed

    def is_action_just_released(self, name: str) -> bool:
        """Check if an action was released this frame."""
        with self._lock:
            return name in self._actions_just_released

    def get_action_hold_duration(self, name: str) -> float:
        """Get how long an action has been held, in seconds."""
        with self._lock:
            action = self._actions.get(name)
            return action.hold_duration if action else 0.0

    def remove_action(self, name: str) -> bool:
        """Remove a registered action. Returns True if it existed."""
        with self._lock:
            if name in self._actions:
                del self._actions[name]
                self._actions_just_pressed.discard(name)
                self._actions_just_released.discard(name)
                self._actions_held.discard(name)
                self._action_last_press_time.pop(name, None)
                return True
            return False

    def update_actions(self, delta_time: float) -> None:
        """
        Finalize per-frame action state. Must be called once per frame
        after all events for the frame have been processed.
        """
        with self._lock:
            # Clear per-frame key flags
            self._current_state.keys_just_pressed.clear()
            self._current_state.keys_just_released.clear()

            # Clear per-frame mouse button flags
            self._mouse_buttons_just_pressed.clear()
            self._mouse_buttons_just_released.clear()

            # Clear per-frame action flags
            self._actions_just_pressed.clear()
            self._actions_just_released.clear()

            # Reset mouse deltas and wheel
            self._current_state.mouse_dx = 0.0
            self._current_state.mouse_dy = 0.0
            self._current_state.mouse_wheel = 0.0

            # Update hold durations for active actions
            for action in self._actions.values():
                if action.is_active and action.name in self._actions_held:
                    action.hold_duration += delta_time

                # Mark held actions based on trigger type
                if action.trigger_type == ActionTriggerType.HELD and action.is_active:
                    if action.hold_duration >= 0.0:
                        self._actions_held.add(action.name)

    # ------------------------------------------------------------------
    # Subscription System
    # ------------------------------------------------------------------

    def subscribe(
        self, event_type: InputEventType, callback: Callable[[InputEvent], None]
    ) -> str:
        """Subscribe to an event type. Returns a subscription ID for unsubscribing."""
        subscription_id = str(uuid.uuid4())
        with self._lock:
            self._subscriptions[subscription_id] = {
                "event_type": event_type,
                "callback": callback,
            }
            self._event_callbacks.setdefault(event_type, []).append(subscription_id)
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by ID. Returns True if it existed."""
        with self._lock:
            sub = self._subscriptions.pop(subscription_id, None)
            if sub is None:
                return False
            event_type: InputEventType = sub["event_type"]
            callback_list = self._event_callbacks.get(event_type, [])
            if subscription_id in callback_list:
                callback_list.remove(subscription_id)
            return True

    def _dispatch_to_subscribers(self, event: InputEvent) -> None:
        """Invoke all callbacks subscribed to the event's type."""
        with self._lock:
            callback_ids = list(
                self._event_callbacks.get(event.event_type, [])
            )
            subscriptions = {
                sid: self._subscriptions[sid]
                for sid in callback_ids
                if sid in self._subscriptions
            }

        for sub in subscriptions.values():
            try:
                sub["callback"](event)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Input State Queries
    # ------------------------------------------------------------------

    def get_input_state(self) -> InputState:
        """Return a copy of the current frame's input state."""
        with self._lock:
            return InputState(
                keys_pressed=set(self._current_state.keys_pressed),
                keys_just_pressed=set(self._current_state.keys_just_pressed),
                keys_just_released=set(self._current_state.keys_just_released),
                mouse_x=self._current_state.mouse_x,
                mouse_y=self._current_state.mouse_y,
                mouse_dx=self._current_state.mouse_dx,
                mouse_dy=self._current_state.mouse_dy,
                mouse_buttons=dict(self._current_state.mouse_buttons),
                mouse_wheel=self._current_state.mouse_wheel,
                touch_points=dict(self._current_state.touch_points),
                gamepad_buttons=dict(self._current_state.gamepad_buttons),
                gamepad_axes=dict(self._current_state.gamepad_axes),
            )

    def get_mouse_position(self) -> Tuple[float, float]:
        """Get the current mouse position."""
        with self._lock:
            return (self._current_state.mouse_x, self._current_state.mouse_y)

    def is_key_pressed(self, key_code: str) -> bool:
        """Check if a key is currently held down."""
        with self._lock:
            return key_code in self._current_state.keys_pressed

    def is_key_just_pressed(self, key_code: str) -> bool:
        """Check if a key was pressed this frame."""
        with self._lock:
            return key_code in self._current_state.keys_just_pressed

    def is_key_just_released(self, key_code: str) -> bool:
        """Check if a key was released this frame."""
        with self._lock:
            return key_code in self._current_state.keys_just_released

    def is_mouse_button_pressed(self, button: int) -> bool:
        """Check if a mouse button is currently held down."""
        with self._lock:
            return self._current_state.mouse_buttons.get(button, False)

    # ------------------------------------------------------------------
    # Gesture Detection
    # ------------------------------------------------------------------

    def detect_gestures(
        self,
        touch_id: int,
        phase: str,
        x: float,
        y: float,
        timestamp: float,
    ) -> Optional[GestureEvent]:
        """
        Detect gestures from touch sequences.

        Args:
            touch_id: Unique identifier for the touch point.
            phase: One of "started", "moved", "ended", "cancelled".
            x, y: Current touch coordinates.
            timestamp: Current time in seconds.

        Returns:
            A GestureEvent if a gesture was recognized, or None.
        """
        with self._lock:
            result = self._process_gesture_phase(touch_id, phase, x, y, timestamp)
            if result is not None:
                self._total_gestures_detected += 1
            return result

    def _process_gesture_phase(
        self,
        touch_id: int,
        phase: str,
        x: float,
        y: float,
        timestamp: float,
    ) -> Optional[GestureEvent]:
        """Internal gesture state machine."""
        tracker = self._gesture_tracker

        if phase == "started":
            tap_hist = self._tap_history.get(touch_id, {})
            tap_count = tap_hist.get("tap_count", 0)
            last_tap_time = tap_hist.get("last_tap_time", 0.0)

            # Expire stale tap history
            if timestamp - last_tap_time > _DOUBLE_TAP_MAX_INTERVAL:
                tap_count = 0
                last_tap_time = 0.0
                self._tap_history.pop(touch_id, None)

            tracker[touch_id] = {
                "start_x": x,
                "start_y": y,
                "start_time": timestamp,
                "current_x": x,
                "current_y": y,
                "phase": "started",
                "tap_count": tap_count,
                "last_tap_time": last_tap_time,
                "long_press_triggered": False,
                "swipe_detected": False,
            }
            return None

        if touch_id not in tracker:
            return None

        entry = tracker[touch_id]
        entry["current_x"] = x
        entry["current_y"] = y

        if phase == "cancelled":
            self._tap_history.pop(touch_id, None)
            del tracker[touch_id]
            return None

        if phase == "moved":
            # Check for long press
            if not entry["long_press_triggered"]:
                elapsed = timestamp - entry["start_time"]
                if elapsed >= _LONG_PRESS_MIN_DURATION:
                    entry["long_press_triggered"] = True
                    return GestureEvent(
                        gesture_id=str(uuid.uuid4()),
                        gesture_type=GestureType.LONG_PRESS,
                        start_x=entry["start_x"],
                        start_y=entry["start_y"],
                        current_x=x,
                        current_y=y,
                        duration=elapsed,
                    )

            # Check for two-finger gestures (pinch / rotate)
            if len(tracker) >= 2:
                two_finger = self._detect_two_finger_gesture(tracker, timestamp)
                if two_finger is not None:
                    return two_finger

            return None

        if phase == "ended":
            elapsed = timestamp - entry["start_time"]
            dist_x = x - entry["start_x"]
            dist_y = y - entry["start_y"]
            distance = math.sqrt(dist_x * dist_x + dist_y * dist_y)

            # Swipe detection
            if distance >= _SWIPE_MIN_DISTANCE:
                self._tap_history.pop(touch_id, None)
                direction = self._compute_direction(dist_x, dist_y)
                entry["swipe_detected"] = True
                gesture = GestureEvent(
                    gesture_id=str(uuid.uuid4()),
                    gesture_type=GestureType.SWIPE,
                    start_x=entry["start_x"],
                    start_y=entry["start_y"],
                    current_x=x,
                    current_y=y,
                    end_x=x,
                    end_y=y,
                    duration=elapsed,
                    distance=distance,
                    direction=direction,
                )
                del tracker[touch_id]
                return gesture

            # Tap detection
            if elapsed <= _TAP_MAX_DURATION and distance <= _TAP_MAX_DISTANCE:
                entry["tap_count"] += 1
                time_since_last_tap = timestamp - entry["last_tap_time"]
                entry["last_tap_time"] = timestamp

                # Persist tap history
                self._tap_history[touch_id] = {
                    "tap_count": entry["tap_count"],
                    "last_tap_time": entry["last_tap_time"],
                }

                if (
                    entry["tap_count"] >= 2
                    and time_since_last_tap <= _DOUBLE_TAP_MAX_INTERVAL
                ):
                    self._tap_history.pop(touch_id, None)
                    del tracker[touch_id]
                    return GestureEvent(
                        gesture_id=str(uuid.uuid4()),
                        gesture_type=GestureType.DOUBLE_TAP,
                        start_x=entry["start_x"],
                        start_y=entry["start_y"],
                        current_x=x,
                        current_y=y,
                        end_x=x,
                        end_y=y,
                        duration=elapsed,
                        distance=distance,
                    )

                gesture = GestureEvent(
                    gesture_id=str(uuid.uuid4()),
                    gesture_type=GestureType.TAP,
                    start_x=entry["start_x"],
                    start_y=entry["start_y"],
                    current_x=x,
                    current_y=y,
                    end_x=x,
                    end_y=y,
                    duration=elapsed,
                    distance=distance,
                )
                del tracker[touch_id]
                return gesture

            # No recognized gesture
            self._tap_history.pop(touch_id, None)
            del tracker[touch_id]
            return None

        return None

    def _detect_two_finger_gesture(
        self,
        tracker: Dict[int, Dict[str, Any]],
        timestamp: float,
    ) -> Optional[GestureEvent]:
        """Detect pinch or rotate from two simultaneous touch points."""
        touch_ids = list(tracker.keys())
        if len(touch_ids) < 2:
            return None

        t0 = tracker[touch_ids[0]]
        t1 = tracker[touch_ids[1]]

        # Current distance and angle
        cx0, cy0 = t0["current_x"], t0["current_y"]
        cx1, cy1 = t1["current_x"], t1["current_y"]
        current_dist = math.sqrt((cx1 - cx0) ** 2 + (cy1 - cy0) ** 2)
        current_angle = math.atan2(cy1 - cy0, cx1 - cx0)

        # Start distance and angle
        sx0, sy0 = t0["start_x"], t0["start_y"]
        sx1, sy1 = t1["start_x"], t1["start_y"]
        start_dist = math.sqrt((sx1 - sx0) ** 2 + (sy1 - sy0) ** 2)
        start_angle = math.atan2(sy1 - sy0, sx1 - sx0)

        if start_dist < 0.001:
            return None

        scale = current_dist / start_dist
        rotation = math.degrees(current_angle - start_angle)

        center_x = (cx0 + cx1) / 2.0
        center_y = (cy0 + cy1) / 2.0

        # Pinch
        if scale < _PINCH_MIN_SCALE or scale > _PINCH_MAX_SCALE:
            return None

        if abs(scale - 1.0) > 0.05:
            return GestureEvent(
                gesture_id=str(uuid.uuid4()),
                gesture_type=GestureType.PINCH,
                start_x=center_x,
                start_y=center_y,
                current_x=center_x,
                current_y=center_y,
                scale=scale,
                device_type=InputDeviceType.TOUCH,
            )

        # Rotate
        if abs(rotation) > 3.0:
            return GestureEvent(
                gesture_id=str(uuid.uuid4()),
                gesture_type=GestureType.ROTATE,
                start_x=center_x,
                start_y=center_y,
                current_x=center_x,
                current_y=center_y,
                rotation=rotation,
                device_type=InputDeviceType.TOUCH,
            )

        return None

    @staticmethod
    def _compute_direction(dx: float, dy: float) -> str:
        """Determine swipe direction from delta vector."""
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        if abs_dx >= abs_dy:
            return "right" if dx > 0 else "left"
        else:
            return "down" if dy > 0 else "up"

    # ------------------------------------------------------------------
    # History & Stats
    # ------------------------------------------------------------------

    def get_event_history(self, limit: int = 100) -> List[InputEvent]:
        """Return the most recent input events, up to limit."""
        with self._lock:
            return list(self._event_history[-limit:])

    def clear_event_history(self) -> None:
        """Clear all buffered input events."""
        with self._lock:
            self._event_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return diagnostic statistics about the input system."""
        with self._lock:
            return {
                "total_events_processed": self._total_events_processed,
                "total_gestures_detected": self._total_gestures_detected,
                "history_size": len(self._event_history),
                "max_history": self._max_history,
                "actions_registered": len(self._actions),
                "active_actions": sum(
                    1 for a in self._actions.values() if a.is_active
                ),
                "subscriptions": len(self._subscriptions),
                "active_gestures_tracking": len(self._gesture_tracker),
                "keys_pressed": len(self._current_state.keys_pressed),
                "touch_points": len(self._current_state.touch_points),
            }

    def reset(self) -> None:
        """Fully reset the input system to initial state."""
        with self._lock:
            self._actions.clear()
            self._event_history.clear()
            self._gesture_tracker.clear()
            self._tap_history.clear()
            self._subscriptions.clear()
            for et in InputEventType:
                self._event_callbacks[et] = []
            self._current_state = InputState()
            self._previous_state = InputState()
            self._actions_just_pressed.clear()
            self._actions_just_released.clear()
            self._actions_held.clear()
            self._action_last_press_time.clear()
            self._mouse_buttons_just_pressed.clear()
            self._mouse_buttons_just_released.clear()
            self._total_events_processed = 0
            self._total_gestures_detected = 0


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_input_engine() -> InputEngine:
    """
    Return the singleton InputEngine instance.

    Uses double-checked locking for thread-safe lazy initialization.
    """
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = InputEngine()
    return _engine_instance