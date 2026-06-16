"""
SparkLabs Engine - AI-Optimized Input Mapping System

A comprehensive input mapping layer that bridges raw device inputs to
semantic game actions. Supports device detection, key binding, gesture
recognition, input buffering, and adaptive control schemes for the
AI-native game engine.

Architecture:
  InputMappingEngine (Singleton)
    |-- InputDevice        — supported hardware input categories
    |-- InputAction        — semantic game actions (move, jump, attack, etc.)
    |-- GestureType        — recognized touch/motion gesture categories
    |-- InputBinding       — single key/button → action mapping
    |-- ControlScheme      — named collection of bindings for a device
    |-- GesturePattern     — registered gesture template for detection
    |-- InputBufferEntry   — timestamped input record in the processing queue

Key Features:
  - Device-specific default control schemes (keyboard, gamepad, touchscreen)
  - Dynamic binding with sensitivity, deadzone, and invert support
  - Gesture pattern registration and runtime detection from point sequences
  - Input buffering with consumption tracking for frame-ordered processing
  - Player behavior analysis for adaptive binding recommendations
"""

from __future__ import annotations

import json
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InputDevice(str, Enum):
    """Hardware input categories supported by the mapping system."""
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"
    TOUCHSCREEN = "touchscreen"
    GYROSCOPE = "gyroscope"
    ACCELEROMETER = "accelerometer"
    JOYSTICK = "joystick"
    VR_CONTROLLER = "vr_controller"
    ARCADE_STICK = "arcade_stick"
    RACING_WHEEL = "racing_wheel"


class InputAction(str, Enum):
    """Semantic game actions that raw inputs map to."""
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    JUMP = "jump"
    CROUCH = "crouch"
    SPRINT = "sprint"
    ATTACK = "attack"
    DEFEND = "defend"
    INTERACT = "interact"
    USE_ITEM = "use_item"
    PAUSE = "pause"
    MENU = "menu"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    CYCLE_INVENTORY = "cycle_inventory"
    QUICK_SAVE = "quick_save"
    QUICK_LOAD = "quick_load"


class GestureType(str, Enum):
    """Touch and motion gesture categories for pattern recognition."""
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    PINCH = "pinch"
    SPREAD = "spread"
    ROTATE = "rotate"
    TILT = "tilt"
    SHAKE = "shake"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class InputBinding:
    """A single mapping from a device input to a game action.

    Each binding links one action to a primary input (and optionally a
    secondary fallback). Sensitivity, deadzone, and invert control how
    analog values are processed before triggering the action.
    """
    binding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action: InputAction = InputAction.JUMP
    device: InputDevice = InputDevice.KEYBOARD
    primary_input: str = ""
    secondary_input: str = ""
    sensitivity: float = 1.0
    deadzone: float = 0.2
    invert: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "action": self.action.value,
            "device": self.device.value,
            "primary_input": self.primary_input,
            "secondary_input": self.secondary_input,
            "sensitivity": self.sensitivity,
            "deadzone": self.deadzone,
            "invert": self.invert,
            "created_at": self.created_at,
        }


@dataclass
class ControlScheme:
    """A named collection of input bindings associated with a device type.

    Schemes can be preset-based (built-in defaults) or custom (user-defined).
    Each scheme targets a specific device category and groups all bindings
    for that device under one configuration.
    """
    scheme_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    device: InputDevice = InputDevice.KEYBOARD
    bindings: Dict[InputAction, InputBinding] = field(default_factory=dict)
    preset_name: str = ""
    is_custom: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "name": self.name,
            "device": self.device.value,
            "bindings": {a.value: b.to_dict() for a, b in self.bindings.items()},
            "preset_name": self.preset_name,
            "is_custom": self.is_custom,
            "created_at": self.created_at,
        }


@dataclass
class GesturePattern:
    """A registered gesture template used for runtime gesture detection.

    Defines the expected point count, duration range, and detection threshold
    for matching a gesture type to a specific game action.
    """
    gesture_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    gesture_type: GestureType = GestureType.TAP
    required_points: int = 1
    min_duration_ms: float = 0.0
    max_duration_ms: float = 500.0
    threshold: float = 0.5
    action: InputAction = InputAction.INTERACT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gesture_id": self.gesture_id,
            "gesture_type": self.gesture_type.value,
            "required_points": self.required_points,
            "min_duration_ms": self.min_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "threshold": self.threshold,
            "action": self.action.value,
        }


@dataclass
class InputBufferEntry:
    """A timestamped input record stored in the processing buffer.

    Tracks whether the entry has been consumed so that the processing loop
    can skip already-handled inputs while replaying unconsumed ones.
    """
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action: InputAction = InputAction.JUMP
    timestamp: float = field(default_factory=time.time)
    value: float = 1.0
    duration_ms: float = 0.0
    consumed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "action": self.action.value,
            "timestamp": self.timestamp,
            "value": self.value,
            "duration_ms": self.duration_ms,
            "consumed": self.consumed,
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Accessible key clusters used for binding recommendations.
# Keys are ranked from most accessible (home row / primary fingers) to less
# accessible, serving as the candidate pool when suggesting mappings.
_ACCESSIBLE_KEYS: List[str] = [
    "Space", "E", "F", "R", "Q",
    "W", "A", "S", "D",
    "ShiftLeft", "ControlLeft",
    "1", "2", "3", "4",
    "Tab", "CapsLock",
    "Z", "X", "C", "V",
    "G", "T", "H", "Y",
]

# Adjacency graph for keyboard keys. Each key maps to a list of physically
# neighbouring keys, used when recommending bindings for co-occurring actions.
_KEY_ADJACENCY: Dict[str, List[str]] = {
    "W": ["Q", "E", "A", "S", "2"],
    "A": ["Q", "W", "S", "Z", "ShiftLeft"],
    "S": ["W", "A", "D", "Z", "X"],
    "D": ["W", "E", "S", "C", "X"],
    "Q": ["W", "A", "1", "2", "Tab"],
    "E": ["W", "D", "R", "3", "4"],
    "R": ["E", "T", "D", "F", "4"],
    "F": ["R", "G", "D", "C", "V"],
    "Space": ["V", "B", "N", "M", "C"],
    "ShiftLeft": ["A", "Z", "ControlLeft"],
    "ControlLeft": ["ShiftLeft", "Z"],
    "Z": ["A", "S", "X", "ShiftLeft"],
    "X": ["Z", "S", "D", "C"],
    "C": ["X", "D", "F", "V", "Space"],
    "V": ["C", "F", "G", "B", "Space"],
    "G": ["F", "H", "T", "V", "B"],
    "T": ["R", "Y", "G", "5"],
    "1": ["Q", "2", "Tab"],
    "2": ["1", "W", "3", "Q"],
    "3": ["2", "E", "4"],
    "4": ["3", "R", "E", "5"],
    "Tab": ["Q", "1", "CapsLock"],
}

# Default deadzone values per device type for analog input filtering.
_DEFAULT_DEADZONE: Dict[InputDevice, float] = {
    InputDevice.KEYBOARD: 0.0,
    InputDevice.MOUSE: 0.05,
    InputDevice.GAMEPAD: 0.2,
    InputDevice.TOUCHSCREEN: 0.1,
    InputDevice.JOYSTICK: 0.2,
    InputDevice.VR_CONTROLLER: 0.15,
    InputDevice.ARCADE_STICK: 0.1,
    InputDevice.RACING_WHEEL: 0.1,
    InputDevice.GYROSCOPE: 0.15,
    InputDevice.ACCELEROMETER: 0.15,
}

# Maximum number of buffered inputs retained before oldest entries are
# evicted to prevent unbounded memory growth during extended sessions.
_MAX_BUFFER_SIZE: int = 256


# ---------------------------------------------------------------------------
# InputMappingEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class InputMappingEngine:
    """AI-optimized input mapping system for the game engine.

    Manages control schemes, input bindings, gesture patterns, and an
    input buffer. Provides device-aware default scheme generation and
    player behavior analysis for adaptive binding recommendations.

    Thread-safe via a reentrant lock. Obtain the singleton through
    get_input_mapping_engine() or InputMappingEngine.get_instance().

    Usage:
        engine = get_input_mapping_engine()
        scheme = engine.generate_default_scheme(InputDevice.KEYBOARD)
        engine.bind_action(scheme.scheme_id, InputAction.ATTACK,
                           primary_input="MouseLeft", deadzone=0.0)
        entry = engine.buffer_input(InputAction.JUMP, value=1.0, duration_ms=50)
        unconsumed = engine.process_buffered_inputs()
    """

    _instance: Optional["InputMappingEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "InputMappingEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "InputMappingEngine":
        return cls()

    def _initialize(self) -> None:
        self._schemes: Dict[str, ControlScheme] = {}
        self._gestures: Dict[str, GesturePattern] = {}
        self._buffer: deque[InputBufferEntry] = deque()
        self._creation_counter: int = 0
        self._total_bindings_created: int = 0
        self._total_gestures_registered: int = 0
        self._total_inputs_buffered: int = 0
        self._total_inputs_consumed: int = 0

    # ------------------------------------------------------------------
    # Control Scheme Management
    # ------------------------------------------------------------------

    def create_control_scheme(
        self,
        name: str,
        device: InputDevice,
        preset_name: str = "",
    ) -> ControlScheme:
        """Create a new control scheme for the given device type.

        Args:
            name: Human-readable name for the scheme.
            device: Target input device category.
            preset_name: Optional preset identifier (e.g. "fps_default").

        Returns:
            A new ControlScheme instance with an empty binding set.
        """
        with self._lock:
            scheme = ControlScheme(
                name=name,
                device=device,
                preset_name=preset_name,
                is_custom=(preset_name == ""),
            )
            self._schemes[scheme.scheme_id] = scheme
            self._creation_counter += 1
            return scheme

    def get_scheme(self, scheme_id: str) -> Optional[ControlScheme]:
        """Retrieve a control scheme by its identifier.

        Args:
            scheme_id: The unique scheme identifier.

        Returns:
            The matching ControlScheme, or None if not found.
        """
        with self._lock:
            return self._schemes.get(scheme_id)

    def list_schemes(self, device: Optional[InputDevice] = None) -> List[ControlScheme]:
        """List all control schemes, optionally filtered by device type.

        Args:
            device: If provided, only schemes for this device are returned.

        Returns:
            A list of matching ControlScheme instances.
        """
        with self._lock:
            if device is None:
                return list(self._schemes.values())
            return [s for s in self._schemes.values() if s.device == device]

    def remove_scheme(self, scheme_id: str) -> bool:
        """Remove a control scheme by its identifier.

        Args:
            scheme_id: The unique scheme identifier.

        Returns:
            True if the scheme was removed, False if not found.
        """
        with self._lock:
            if scheme_id in self._schemes:
                del self._schemes[scheme_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Binding Management
    # ------------------------------------------------------------------

    def bind_action(
        self,
        scheme_id: str,
        action: InputAction,
        primary_input: str,
        secondary_input: str = "",
        sensitivity: float = 1.0,
        deadzone: float = -1.0,
        invert: bool = False,
    ) -> Optional[InputBinding]:
        """Bind an action to one or two device inputs within a scheme.

        If the action is already bound in this scheme, the existing binding
        is replaced. When deadzone is -1.0, the device-specific default is used.

        Args:
            scheme_id: Target control scheme identifier.
            action: The game action to bind.
            primary_input: Primary key, button, or axis string.
            secondary_input: Optional secondary fallback input.
            sensitivity: Analog sensitivity multiplier (1.0 = default).
            deadzone: Deadzone threshold; -1.0 uses the device default.
            invert: Whether to invert the analog value.

        Returns:
            The created or updated InputBinding, or None if scheme not found.
        """
        with self._lock:
            scheme = self._schemes.get(scheme_id)
            if scheme is None:
                return None

            effective_deadzone = deadzone
            if effective_deadzone < 0.0:
                effective_deadzone = _DEFAULT_DEADZONE.get(scheme.device, 0.1)

            binding = InputBinding(
                action=action,
                device=scheme.device,
                primary_input=primary_input,
                secondary_input=secondary_input,
                sensitivity=sensitivity,
                deadzone=effective_deadzone,
                invert=invert,
            )
            scheme.bindings[action] = binding
            self._total_bindings_created += 1
            return binding

    def unbind_action(self, scheme_id: str, action: InputAction) -> Optional[ControlScheme]:
        """Remove an action binding from a control scheme.

        Args:
            scheme_id: Target control scheme identifier.
            action: The action to unbind.

        Returns:
            The updated ControlScheme, or None if scheme not found.
        """
        with self._lock:
            scheme = self._schemes.get(scheme_id)
            if scheme is None:
                return None
            scheme.bindings.pop(action, None)
            return scheme

    def get_binding(self, scheme_id: str, action: InputAction) -> Optional[InputBinding]:
        """Retrieve the binding for a specific action within a scheme.

        Args:
            scheme_id: Target control scheme identifier.
            action: The action to look up.

        Returns:
            The matching InputBinding, or None if not bound.
        """
        with self._lock:
            scheme = self._schemes.get(scheme_id)
            if scheme is None:
                return None
            return scheme.bindings.get(action)

    # ------------------------------------------------------------------
    # Gesture Management
    # ------------------------------------------------------------------

    def register_gesture(
        self,
        gesture_type: GestureType,
        action: InputAction,
        required_points: int = 1,
        threshold: float = 0.5,
        min_duration_ms: float = 0.0,
        max_duration_ms: float = 500.0,
    ) -> GesturePattern:
        """Register a gesture pattern for runtime detection.

        Args:
            gesture_type: Category of gesture to detect.
            action: Game action triggered when this gesture is matched.
            required_points: Minimum number of touch/motion points needed.
            threshold: Detection confidence threshold (0.0 - 1.0).
            min_duration_ms: Minimum gesture duration in milliseconds.
            max_duration_ms: Maximum gesture duration in milliseconds.

        Returns:
            The newly registered GesturePattern.
        """
        with self._lock:
            pattern = GesturePattern(
                gesture_type=gesture_type,
                required_points=required_points,
                min_duration_ms=min_duration_ms,
                max_duration_ms=max_duration_ms,
                threshold=threshold,
                action=action,
            )
            self._gestures[pattern.gesture_id] = pattern
            self._total_gestures_registered += 1
            return pattern

    def unregister_gesture(self, gesture_id: str) -> bool:
        """Remove a registered gesture pattern.

        Args:
            gesture_id: The unique gesture identifier.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if gesture_id in self._gestures:
                del self._gestures[gesture_id]
                return True
            return False

    def detect_gesture(
        self,
        input_points: List[Tuple[float, float]],
        duration_ms: float,
    ) -> Optional[GesturePattern]:
        """Detect which registered gesture matches the given input points.

        Compares the input point sequence against all registered patterns,
        checking point count, duration range, and computing a spatial match
        score against the pattern threshold.

        Args:
            input_points: Sequence of (x, y) touch or motion coordinates.
            duration_ms: Total duration of the gesture in milliseconds.

        Returns:
            The best-matching GesturePattern, or None if no pattern matches.
        """
        with self._lock:
            best_match: Optional[GesturePattern] = None
            best_score: float = 0.0
            num_points = len(input_points)

            for pattern in self._gestures.values():
                # Check point count requirement
                if num_points < pattern.required_points:
                    continue

                # Check duration range
                if duration_ms < pattern.min_duration_ms:
                    continue
                if duration_ms > pattern.max_duration_ms:
                    continue

                # Compute spatial match score based on gesture type
                score = self._compute_gesture_score(pattern.gesture_type, input_points)

                if score >= pattern.threshold and score > best_score:
                    best_score = score
                    best_match = pattern

            return best_match

    def _compute_gesture_score(
        self,
        gesture_type: GestureType,
        points: List[Tuple[float, float]],
    ) -> float:
        """Compute a 0.0-1.0 match score for a gesture against input points.

        Different gesture types use different scoring heuristics:
          - TAP / DOUBLE_TAP / LONG_PRESS: Point clustering density.
          - SWIPE_*: Directional alignment of the trajectory vector.
          - PINCH / SPREAD: Distance delta between first and last points.
          - ROTATE: Angular displacement across the point sequence.
          - TILT / SHAKE: Variance and oscillation in the point stream.
        """
        if len(points) < 2:
            return 0.0

        start = points[0]
        end = points[-1]

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        magnitude = (dx * dx + dy * dy) ** 0.5

        if gesture_type == GestureType.TAP:
            # High score when points are tightly clustered
            if magnitude < 20.0:
                return 0.9 + random.uniform(-0.05, 0.05)
            return max(0.0, 1.0 - magnitude / 100.0)

        elif gesture_type == GestureType.DOUBLE_TAP:
            # Similar to tap but expects two clusters
            if magnitude < 20.0:
                return 0.85 + random.uniform(-0.05, 0.05)
            return max(0.0, 0.8 - magnitude / 120.0)

        elif gesture_type == GestureType.LONG_PRESS:
            # High score when points stay very close together
            if magnitude < 10.0:
                return 0.95 + random.uniform(-0.03, 0.03)
            return max(0.0, 1.0 - magnitude / 60.0)

        elif gesture_type == GestureType.SWIPE_UP:
            if magnitude < 30.0:
                return 0.0
            alignment = -dy / (magnitude + 0.001)
            return max(0.0, alignment)

        elif gesture_type == GestureType.SWIPE_DOWN:
            if magnitude < 30.0:
                return 0.0
            alignment = dy / (magnitude + 0.001)
            return max(0.0, alignment)

        elif gesture_type == GestureType.SWIPE_LEFT:
            if magnitude < 30.0:
                return 0.0
            alignment = -dx / (magnitude + 0.001)
            return max(0.0, alignment)

        elif gesture_type == GestureType.SWIPE_RIGHT:
            if magnitude < 30.0:
                return 0.0
            alignment = dx / (magnitude + 0.001)
            return max(0.0, alignment)

        elif gesture_type == GestureType.PINCH:
            # Decreasing distance between first two multi-touch points
            mid = points[len(points) // 2]
            start_dist = ((start[0] - mid[0]) ** 2 + (start[1] - mid[1]) ** 2) ** 0.5
            end_dist = ((end[0] - mid[0]) ** 2 + (end[1] - mid[1]) ** 2) ** 0.5
            if start_dist < 5.0:
                return 0.0
            ratio = end_dist / start_dist
            return max(0.0, 1.0 - ratio)

        elif gesture_type == GestureType.SPREAD:
            # Increasing distance between first two multi-touch points
            mid = points[len(points) // 2]
            start_dist = ((start[0] - mid[0]) ** 2 + (start[1] - mid[1]) ** 2) ** 0.5
            end_dist = ((end[0] - mid[0]) ** 2 + (end[1] - mid[1]) ** 2) ** 0.5
            if end_dist < 5.0:
                return 0.0
            ratio = start_dist / end_dist
            return max(0.0, 1.0 - ratio)

        elif gesture_type == GestureType.ROTATE:
            # Compute angular displacement along the point sequence
            if len(points) < 3:
                return 0.0
            total_angle = 0.0
            for i in range(1, len(points) - 1):
                prev_vec = (points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
                next_vec = (points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
                prev_mag = (prev_vec[0] ** 2 + prev_vec[1] ** 2) ** 0.5
                next_mag = (next_vec[0] ** 2 + next_vec[1] ** 2) ** 0.5
                if prev_mag < 0.001 or next_mag < 0.001:
                    continue
                dot = prev_vec[0] * next_vec[0] + prev_vec[1] * next_vec[1]
                cos_angle = max(-1.0, min(1.0, dot / (prev_mag * next_mag)))
                total_angle += abs(cos_angle)
            score = min(1.0, total_angle / (3.14159 * 2))
            return score

        elif gesture_type == GestureType.TILT:
            # High score when points have a consistent directional bias
            if magnitude < 10.0:
                return 0.0
            return min(1.0, magnitude / 80.0)

        elif gesture_type == GestureType.SHAKE:
            # High score for rapid direction changes (oscillation)
            if len(points) < 4:
                return 0.0
            direction_changes = 0
            for i in range(2, len(points)):
                prev_dx = points[i - 1][0] - points[i - 2][0]
                curr_dx = points[i][0] - points[i - 1][0]
                prev_dy = points[i - 1][1] - points[i - 2][1]
                curr_dy = points[i][1] - points[i - 1][1]
                if (prev_dx * curr_dx < 0) or (prev_dy * curr_dy < 0):
                    direction_changes += 1
            score = min(1.0, direction_changes / max(1, len(points) - 2))
            return score

        return 0.0

    # ------------------------------------------------------------------
    # Input Buffering
    # ------------------------------------------------------------------

    def buffer_input(
        self,
        action: InputAction,
        value: float = 1.0,
        duration_ms: float = 0.0,
    ) -> InputBufferEntry:
        """Push an input event into the processing buffer.

        Args:
            action: The game action that was triggered.
            value: Analog input value (0.0 - 1.0).
            duration_ms: How long the input was held in milliseconds.

        Returns:
            The created InputBufferEntry.
        """
        with self._lock:
            entry = InputBufferEntry(
                action=action,
                value=value,
                duration_ms=duration_ms,
            )
            self._buffer.append(entry)
            self._total_inputs_buffered += 1

            # Evict oldest entries if buffer exceeds capacity
            while len(self._buffer) > _MAX_BUFFER_SIZE:
                self._buffer.popleft()

            return entry

    def consume_input(self, buffer_id: str) -> Optional[InputBufferEntry]:
        """Mark a buffered input entry as consumed.

        Args:
            buffer_id: The entry_id of the buffered input.

        Returns:
            The marked InputBufferEntry, or None if not found.
        """
        with self._lock:
            for entry in self._buffer:
                if entry.entry_id == buffer_id and not entry.consumed:
                    entry.consumed = True
                    self._total_inputs_consumed += 1
                    return entry
            return None

    def process_buffered_inputs(self) -> List[InputBufferEntry]:
        """Return all unconsumed entries and consume them.

        This is the primary processing method called each frame. It drains
        unconsumed entries from the buffer, marks them as consumed, and
        returns them for the game to process.

        Returns:
            List of newly consumed InputBufferEntry instances.
        """
        with self._lock:
            unconsumed = [e for e in self._buffer if not e.consumed]
            for entry in unconsumed:
                entry.consumed = True
                self._total_inputs_consumed += 1
            return unconsumed

    def peek_buffer(self) -> List[InputBufferEntry]:
        """Return unconsumed buffer entries without marking them consumed.

        Returns:
            List of unconsumed InputBufferEntry instances.
        """
        with self._lock:
            return [e for e in self._buffer if not e.consumed]

    def clear_buffer(self) -> int:
        """Remove all entries from the input buffer.

        Returns:
            Number of entries that were cleared.
        """
        with self._lock:
            count = len(self._buffer)
            self._buffer.clear()
            return count

    # ------------------------------------------------------------------
    # Default Scheme Generation
    # ------------------------------------------------------------------

    def generate_default_scheme(self, device: InputDevice) -> ControlScheme:
        """Generate a sensible default control scheme for a device type.

        Produces a preset scheme with canonical bindings for the given
        device. Keyboard uses WASD movement, gamepad uses left stick,
        touchscreen uses virtual controls.

        Args:
            device: The input device category.

        Returns:
            A ControlScheme populated with default bindings.
        """
        scheme = self.create_control_scheme(
            name=f"{device.value}_default",
            device=device,
            preset_name=f"{device.value}_default",
        )

        if device == InputDevice.KEYBOARD:
            self._generate_keyboard_defaults(scheme)
        elif device == InputDevice.GAMEPAD:
            self._generate_gamepad_defaults(scheme)
        elif device == InputDevice.TOUCHSCREEN:
            self._generate_touchscreen_defaults(scheme)
        elif device == InputDevice.MOUSE:
            self._generate_mouse_defaults(scheme)
        else:
            # Generic fallback using gamepad-style defaults
            self._generate_gamepad_defaults(scheme)

        return scheme

    def _generate_keyboard_defaults(self, scheme: ControlScheme) -> None:
        """Populate a scheme with standard keyboard bindings (WASD layout)."""
        with self._lock:
            scheme.bindings[InputAction.MOVE_UP] = InputBinding(
                action=InputAction.MOVE_UP, device=InputDevice.KEYBOARD,
                primary_input="W", secondary_input="ArrowUp",
            )
            scheme.bindings[InputAction.MOVE_DOWN] = InputBinding(
                action=InputAction.MOVE_DOWN, device=InputDevice.KEYBOARD,
                primary_input="S", secondary_input="ArrowDown",
            )
            scheme.bindings[InputAction.MOVE_LEFT] = InputBinding(
                action=InputAction.MOVE_LEFT, device=InputDevice.KEYBOARD,
                primary_input="A", secondary_input="ArrowLeft",
            )
            scheme.bindings[InputAction.MOVE_RIGHT] = InputBinding(
                action=InputAction.MOVE_RIGHT, device=InputDevice.KEYBOARD,
                primary_input="D", secondary_input="ArrowRight",
            )
            scheme.bindings[InputAction.JUMP] = InputBinding(
                action=InputAction.JUMP, device=InputDevice.KEYBOARD,
                primary_input="Space",
            )
            scheme.bindings[InputAction.CROUCH] = InputBinding(
                action=InputAction.CROUCH, device=InputDevice.KEYBOARD,
                primary_input="ControlLeft", secondary_input="C",
            )
            scheme.bindings[InputAction.SPRINT] = InputBinding(
                action=InputAction.SPRINT, device=InputDevice.KEYBOARD,
                primary_input="ShiftLeft",
            )
            scheme.bindings[InputAction.ATTACK] = InputBinding(
                action=InputAction.ATTACK, device=InputDevice.KEYBOARD,
                primary_input="MouseLeft",
            )
            scheme.bindings[InputAction.DEFEND] = InputBinding(
                action=InputAction.DEFEND, device=InputDevice.KEYBOARD,
                primary_input="MouseRight",
            )
            scheme.bindings[InputAction.INTERACT] = InputBinding(
                action=InputAction.INTERACT, device=InputDevice.KEYBOARD,
                primary_input="E",
            )
            scheme.bindings[InputAction.USE_ITEM] = InputBinding(
                action=InputAction.USE_ITEM, device=InputDevice.KEYBOARD,
                primary_input="F",
            )
            scheme.bindings[InputAction.PAUSE] = InputBinding(
                action=InputAction.PAUSE, device=InputDevice.KEYBOARD,
                primary_input="Escape",
            )
            scheme.bindings[InputAction.MENU] = InputBinding(
                action=InputAction.MENU, device=InputDevice.KEYBOARD,
                primary_input="Tab",
            )
            scheme.bindings[InputAction.CONFIRM] = InputBinding(
                action=InputAction.CONFIRM, device=InputDevice.KEYBOARD,
                primary_input="Enter", secondary_input="Space",
            )
            scheme.bindings[InputAction.CANCEL] = InputBinding(
                action=InputAction.CANCEL, device=InputDevice.KEYBOARD,
                primary_input="Escape", secondary_input="Backspace",
            )
            scheme.bindings[InputAction.CYCLE_INVENTORY] = InputBinding(
                action=InputAction.CYCLE_INVENTORY, device=InputDevice.KEYBOARD,
                primary_input="I", secondary_input="Tab",
            )
            scheme.bindings[InputAction.QUICK_SAVE] = InputBinding(
                action=InputAction.QUICK_SAVE, device=InputDevice.KEYBOARD,
                primary_input="F5",
            )
            scheme.bindings[InputAction.QUICK_LOAD] = InputBinding(
                action=InputAction.QUICK_LOAD, device=InputDevice.KEYBOARD,
                primary_input="F9",
            )
            for binding in scheme.bindings.values():
                self._total_bindings_created += 1

    def _generate_gamepad_defaults(self, scheme: ControlScheme) -> None:
        """Populate a scheme with standard gamepad bindings (Xbox-style layout)."""
        with self._lock:
            scheme.bindings[InputAction.MOVE_UP] = InputBinding(
                action=InputAction.MOVE_UP, device=InputDevice.GAMEPAD,
                primary_input="LeftStickY_Negative", secondary_input="DPad_Up",
            )
            scheme.bindings[InputAction.MOVE_DOWN] = InputBinding(
                action=InputAction.MOVE_DOWN, device=InputDevice.GAMEPAD,
                primary_input="LeftStickY_Positive", secondary_input="DPad_Down",
            )
            scheme.bindings[InputAction.MOVE_LEFT] = InputBinding(
                action=InputAction.MOVE_LEFT, device=InputDevice.GAMEPAD,
                primary_input="LeftStickX_Negative", secondary_input="DPad_Left",
            )
            scheme.bindings[InputAction.MOVE_RIGHT] = InputBinding(
                action=InputAction.MOVE_RIGHT, device=InputDevice.GAMEPAD,
                primary_input="LeftStickX_Positive", secondary_input="DPad_Right",
            )
            scheme.bindings[InputAction.JUMP] = InputBinding(
                action=InputAction.JUMP, device=InputDevice.GAMEPAD,
                primary_input="ButtonA",
            )
            scheme.bindings[InputAction.CROUCH] = InputBinding(
                action=InputAction.CROUCH, device=InputDevice.GAMEPAD,
                primary_input="ButtonB",
            )
            scheme.bindings[InputAction.SPRINT] = InputBinding(
                action=InputAction.SPRINT, device=InputDevice.GAMEPAD,
                primary_input="LeftStick_Click",
            )
            scheme.bindings[InputAction.ATTACK] = InputBinding(
                action=InputAction.ATTACK, device=InputDevice.GAMEPAD,
                primary_input="RightTrigger",
            )
            scheme.bindings[InputAction.DEFEND] = InputBinding(
                action=InputAction.DEFEND, device=InputDevice.GAMEPAD,
                primary_input="LeftTrigger",
            )
            scheme.bindings[InputAction.INTERACT] = InputBinding(
                action=InputAction.INTERACT, device=InputDevice.GAMEPAD,
                primary_input="ButtonX",
            )
            scheme.bindings[InputAction.USE_ITEM] = InputBinding(
                action=InputAction.USE_ITEM, device=InputDevice.GAMEPAD,
                primary_input="ButtonY",
            )
            scheme.bindings[InputAction.PAUSE] = InputBinding(
                action=InputAction.PAUSE, device=InputDevice.GAMEPAD,
                primary_input="Start",
            )
            scheme.bindings[InputAction.MENU] = InputBinding(
                action=InputAction.MENU, device=InputDevice.GAMEPAD,
                primary_input="Select",
            )
            scheme.bindings[InputAction.CONFIRM] = InputBinding(
                action=InputAction.CONFIRM, device=InputDevice.GAMEPAD,
                primary_input="ButtonA",
            )
            scheme.bindings[InputAction.CANCEL] = InputBinding(
                action=InputAction.CANCEL, device=InputDevice.GAMEPAD,
                primary_input="ButtonB",
            )
            scheme.bindings[InputAction.CYCLE_INVENTORY] = InputBinding(
                action=InputAction.CYCLE_INVENTORY, device=InputDevice.GAMEPAD,
                primary_input="DPad_Up", secondary_input="DPad_Down",
            )
            scheme.bindings[InputAction.QUICK_SAVE] = InputBinding(
                action=InputAction.QUICK_SAVE, device=InputDevice.GAMEPAD,
                primary_input="Start",
            )
            scheme.bindings[InputAction.QUICK_LOAD] = InputBinding(
                action=InputAction.QUICK_LOAD, device=InputDevice.GAMEPAD,
                primary_input="Select",
            )
            for binding in scheme.bindings.values():
                self._total_bindings_created += 1

    def _generate_touchscreen_defaults(self, scheme: ControlScheme) -> None:
        """Populate a scheme with touchscreen virtual controls."""
        with self._lock:
            scheme.bindings[InputAction.MOVE_UP] = InputBinding(
                action=InputAction.MOVE_UP, device=InputDevice.TOUCHSCREEN,
                primary_input="VirtualStick_Up",
            )
            scheme.bindings[InputAction.MOVE_DOWN] = InputBinding(
                action=InputAction.MOVE_DOWN, device=InputDevice.TOUCHSCREEN,
                primary_input="VirtualStick_Down",
            )
            scheme.bindings[InputAction.MOVE_LEFT] = InputBinding(
                action=InputAction.MOVE_LEFT, device=InputDevice.TOUCHSCREEN,
                primary_input="VirtualStick_Left",
            )
            scheme.bindings[InputAction.MOVE_RIGHT] = InputBinding(
                action=InputAction.MOVE_RIGHT, device=InputDevice.TOUCHSCREEN,
                primary_input="VirtualStick_Right",
            )
            scheme.bindings[InputAction.JUMP] = InputBinding(
                action=InputAction.JUMP, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Jump",
            )
            scheme.bindings[InputAction.CROUCH] = InputBinding(
                action=InputAction.CROUCH, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Crouch",
            )
            scheme.bindings[InputAction.SPRINT] = InputBinding(
                action=InputAction.SPRINT, device=InputDevice.TOUCHSCREEN,
                primary_input="DoubleTap_VirtualStick",
            )
            scheme.bindings[InputAction.ATTACK] = InputBinding(
                action=InputAction.ATTACK, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Attack",
            )
            scheme.bindings[InputAction.DEFEND] = InputBinding(
                action=InputAction.DEFEND, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Defend",
            )
            scheme.bindings[InputAction.INTERACT] = InputBinding(
                action=InputAction.INTERACT, device=InputDevice.TOUCHSCREEN,
                primary_input="Tap_Interact",
            )
            scheme.bindings[InputAction.USE_ITEM] = InputBinding(
                action=InputAction.USE_ITEM, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_UseItem",
            )
            scheme.bindings[InputAction.PAUSE] = InputBinding(
                action=InputAction.PAUSE, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Pause",
            )
            scheme.bindings[InputAction.MENU] = InputBinding(
                action=InputAction.MENU, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Menu",
            )
            scheme.bindings[InputAction.CONFIRM] = InputBinding(
                action=InputAction.CONFIRM, device=InputDevice.TOUCHSCREEN,
                primary_input="Tap_Confirm",
            )
            scheme.bindings[InputAction.CANCEL] = InputBinding(
                action=InputAction.CANCEL, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Cancel",
            )
            scheme.bindings[InputAction.CYCLE_INVENTORY] = InputBinding(
                action=InputAction.CYCLE_INVENTORY, device=InputDevice.TOUCHSCREEN,
                primary_input="Swipe_Inventory",
            )
            scheme.bindings[InputAction.QUICK_SAVE] = InputBinding(
                action=InputAction.QUICK_SAVE, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Save",
            )
            scheme.bindings[InputAction.QUICK_LOAD] = InputBinding(
                action=InputAction.QUICK_LOAD, device=InputDevice.TOUCHSCREEN,
                primary_input="Button_Load",
            )
            for binding in scheme.bindings.values():
                self._total_bindings_created += 1

    def _generate_mouse_defaults(self, scheme: ControlScheme) -> None:
        """Populate a scheme with mouse-oriented bindings (point-and-click style)."""
        with self._lock:
            scheme.bindings[InputAction.ATTACK] = InputBinding(
                action=InputAction.ATTACK, device=InputDevice.MOUSE,
                primary_input="MouseLeft",
            )
            scheme.bindings[InputAction.DEFEND] = InputBinding(
                action=InputAction.DEFEND, device=InputDevice.MOUSE,
                primary_input="MouseRight",
            )
            scheme.bindings[InputAction.INTERACT] = InputBinding(
                action=InputAction.INTERACT, device=InputDevice.MOUSE,
                primary_input="MouseLeft",
            )
            scheme.bindings[InputAction.USE_ITEM] = InputBinding(
                action=InputAction.USE_ITEM, device=InputDevice.MOUSE,
                primary_input="MouseRight",
            )
            scheme.bindings[InputAction.CONFIRM] = InputBinding(
                action=InputAction.CONFIRM, device=InputDevice.MOUSE,
                primary_input="MouseLeft",
            )
            scheme.bindings[InputAction.CANCEL] = InputBinding(
                action=InputAction.CANCEL, device=InputDevice.MOUSE,
                primary_input="MouseRight",
            )
            scheme.bindings[InputAction.CYCLE_INVENTORY] = InputBinding(
                action=InputAction.CYCLE_INVENTORY, device=InputDevice.MOUSE,
                primary_input="ScrollWheel",
            )
            scheme.bindings[InputAction.PAUSE] = InputBinding(
                action=InputAction.PAUSE, device=InputDevice.MOUSE,
                primary_input="MouseMiddle",
            )
            for binding in scheme.bindings.values():
                self._total_bindings_created += 1

    # ------------------------------------------------------------------
    # Adaptive Binding Recommendations
    # ------------------------------------------------------------------

    def recommend_bindings(self, player_behavior: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze player behavior data and suggest binding adjustments.

        Examines action frequency, co-occurrence patterns, and struggle
        indicators to produce recommendations for key remapping:

          - Frequently used actions are assigned to more accessible keys.
          - Co-occurring actions (used together) are placed on adjacent keys.
          - Actions the player struggles with receive larger deadzone values.

        Args:
            player_behavior: A dictionary with the following optional keys:
                - "action_frequency": Dict[str, int] — action name to usage count.
                - "action_pairs": List[List[str]] — pairs of actions used together.
                - "struggle_actions": List[str] — actions with high miss/error rates.
                - "device": str — device type hint for key pool selection.

        Returns:
            A dict with "recommended_bindings" (list of suggested mappings)
            and "analysis" (summary of the reasoning).
        """
        action_frequency: Dict[str, int] = player_behavior.get("action_frequency", {})
        action_pairs: List[List[str]] = player_behavior.get("action_pairs", [])
        struggle_actions: List[str] = player_behavior.get("struggle_actions", [])
        device_hint: str = player_behavior.get("device", "keyboard")

        recommendations: List[Dict[str, Any]] = []
        assigned_keys: set = set()

        # Convert action name strings to InputAction values where possible
        resolved_frequency: Dict[InputAction, int] = {}
        for name, count in action_frequency.items():
            try:
                resolved_frequency[InputAction(name)] = count
            except ValueError:
                pass

        # Sort actions by frequency (descending)
        sorted_actions = sorted(
            resolved_frequency.items(), key=lambda item: -item[1]
        )

        # Assign most-frequent actions to most-accessible keys
        if device_hint in ("keyboard", "keyboard_mouse"):
            key_pool = list(_ACCESSIBLE_KEYS)
            for idx, (action, _count) in enumerate(sorted_actions):
                if idx < len(key_pool):
                    recommended_key = key_pool[idx]
                    assigned_keys.add(recommended_key)
                    recommendations.append({
                        "action": action.value,
                        "suggested_input": recommended_key,
                        "reason": "high_frequency",
                        "frequency": _count,
                    })
        else:
            # For non-keyboard devices, recommend based on priority ordering
            button_pool = [
                "ButtonA", "ButtonX", "ButtonY", "ButtonB",
                "RightTrigger", "LeftTrigger", "RightBumper", "LeftBumper",
            ]
            for idx, (action, _count) in enumerate(sorted_actions):
                if idx < len(button_pool):
                    recommendations.append({
                        "action": action.value,
                        "suggested_input": button_pool[idx],
                        "reason": "high_frequency",
                        "frequency": _count,
                    })

        # Recommend adjacent keys for co-occurring actions
        for pair in action_pairs:
            if len(pair) != 2:
                continue
            try:
                action_a = InputAction(pair[0])
                action_b = InputAction(pair[1])
            except ValueError:
                continue

            # Find two adjacent keys that haven't been assigned yet
            for key_a, neighbors in _KEY_ADJACENCY.items():
                if key_a in assigned_keys:
                    continue
                for key_b in neighbors:
                    if key_b in assigned_keys:
                        continue
                    recommendations.append({
                        "action": action_a.value,
                        "suggested_input": key_a,
                        "reason": "co_occurrence",
                        "paired_with": action_b.value,
                    })
                    recommendations.append({
                        "action": action_b.value,
                        "suggested_input": key_b,
                        "reason": "co_occurrence",
                        "paired_with": action_a.value,
                    })
                    assigned_keys.add(key_a)
                    assigned_keys.add(key_b)
                    break
                else:
                    continue
                break

        # Recommend larger deadzones for struggle actions
        deadzone_recommendations = []
        for action_name in struggle_actions:
            try:
                action = InputAction(action_name)
            except ValueError:
                continue
            deadzone_recommendations.append({
                "action": action.value,
                "suggested_deadzone": 0.35,
                "reason": "struggle_detected",
            })

        analysis = {
            "total_actions_analyzed": len(action_frequency),
            "total_pairs_analyzed": len(action_pairs),
            "total_struggles_detected": len(struggle_actions),
            "device_context": device_hint,
        }

        return {
            "recommended_bindings": recommendations,
            "recommended_deadzones": deadzone_recommendations,
            "analysis": analysis,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return operational statistics for the input mapping engine.

        Returns:
            A dictionary with scheme, binding, gesture, and buffer counts.
        """
        with self._lock:
            return {
                "total_schemes": len(self._schemes),
                "total_bindings_created": self._total_bindings_created,
                "total_gestures_registered": self._total_gestures_registered,
                "total_inputs_buffered": self._total_inputs_buffered,
                "total_inputs_consumed": self._total_inputs_consumed,
                "current_buffer_size": len(self._buffer),
                "unconsumed_buffer_entries": sum(
                    1 for e in self._buffer if not e.consumed
                ),
                "schemes_by_device": {
                    device.value: sum(
                        1 for s in self._schemes.values() if s.device == device
                    )
                    for device in InputDevice
                },
            }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_scheme(self, scheme_id: str) -> Optional[str]:
        """Export a control scheme as a JSON string.

        Args:
            scheme_id: The unique scheme identifier.

        Returns:
            A JSON-encoded string of the scheme, or None if not found.
        """
        with self._lock:
            scheme = self._schemes.get(scheme_id)
            if scheme is None:
                return None
            return json.dumps(scheme.to_dict(), indent=2)

    def import_scheme(self, scheme_json: str) -> Optional[ControlScheme]:
        """Import a control scheme from a JSON string.

        Args:
            scheme_json: JSON-encoded scheme data from export_scheme.

        Returns:
            The reconstructed ControlScheme, or None on parse failure.
        """
        with self._lock:
            try:
                data = json.loads(scheme_json)
            except (json.JSONDecodeError, TypeError):
                return None

            try:
                device = InputDevice(data["device"])
            except (KeyError, ValueError):
                return None

            scheme = self.create_control_scheme(
                name=data.get("name", "imported"),
                device=device,
                preset_name=data.get("preset_name", ""),
            )

            bindings_data = data.get("bindings", {})
            for action_value, binding_dict in bindings_data.items():
                try:
                    action = InputAction(action_value)
                except ValueError:
                    continue
                self.bind_action(
                    scheme_id=scheme.scheme_id,
                    action=action,
                    primary_input=binding_dict.get("primary_input", ""),
                    secondary_input=binding_dict.get("secondary_input", ""),
                    sensitivity=binding_dict.get("sensitivity", 1.0),
                    deadzone=binding_dict.get("deadzone", -1.0),
                    invert=binding_dict.get("invert", False),
                )

            scheme.is_custom = True
            return scheme


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_input_mapping_engine() -> InputMappingEngine:
    """Return the singleton InputMappingEngine instance."""
    return InputMappingEngine.get_instance()