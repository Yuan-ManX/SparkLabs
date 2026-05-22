"""
SparkLabs Engine - Input Map System

Configurable input mapping system with action bindings, dead zones,
axis combinations, and multi-device support. Maps raw hardware input
events to logical game actions through a layered context stack, enabling
context-sensitive controls that switch seamlessly between gameplay,
menu navigation, and editor modes.

Architecture:
  InputMapSystem
    |-- ActionRegistry (catalog of logical input actions with bindings)
    |-- ContextStack (priority-ordered input contexts with push/pop)
    |-- DeviceManager (multi-device detection, calibration, and profiles)
    |-- GestureRecognizer (pattern-based gesture detection pipeline)
    |-- DeadZoneProcessor (configurable dead zone shapes and thresholds)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class InputDevice(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"
    TOUCH = "touch"
    JOYSTICK = "joystick"


class InputActionType(Enum):
    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    AXIS = "axis"
    GESTURE = "gesture"


class AxisMode(Enum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    SMOOTHED = "smoothed"


class DeadZoneMode(Enum):
    CIRCULAR = "circular"
    SQUARE = "square"
    CROSS = "cross"
    RAW = "raw"


@dataclass
class InputAction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    action_type: InputActionType = InputActionType.PRESS
    bindings: List[ActionBinding] = field(default_factory=list)
    axis_smoothing: float = 0.0
    is_enabled: bool = True
    category: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "action_type": self.action_type.value,
            "binding_count": len(self.bindings),
            "axis_smoothing": self.axis_smoothing,
            "is_enabled": self.is_enabled, "category": self.category,
        }


@dataclass
class ActionBinding:
    device: InputDevice = InputDevice.KEYBOARD
    input_code: str = ""
    modifiers: List[str] = field(default_factory=list)
    scale: float = 1.0
    invert: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device.value, "input_code": self.input_code,
            "modifiers": self.modifiers, "scale": self.scale,
            "invert": self.invert,
        }


@dataclass
class InputContext:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    priority: int = 0
    action_ids: List[str] = field(default_factory=list)
    is_active: bool = False
    consumes_input: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "priority": self.priority,
            "action_count": len(self.action_ids),
            "is_active": self.is_active, "consumes_input": self.consumes_input,
        }


@dataclass
class DeviceProfile:
    device: InputDevice = InputDevice.KEYBOARD
    dead_zone_mode: DeadZoneMode = DeadZoneMode.CIRCULAR
    dead_zone_threshold: float = 0.15
    axis_sensitivity: float = 1.0
    invert_x: bool = False
    invert_y: bool = False
    calibration_data: Dict[str, float] = field(default_factory=dict)
    is_connected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device.value,
            "dead_zone_mode": self.dead_zone_mode.value,
            "dead_zone_threshold": self.dead_zone_threshold,
            "axis_sensitivity": self.axis_sensitivity,
            "invert_x": self.invert_x, "invert_y": self.invert_y,
            "calibration_data": self.calibration_data,
            "is_connected": self.is_connected,
        }


@dataclass
class InputEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    device: InputDevice = InputDevice.KEYBOARD
    input_code: str = ""
    raw_value: float = 0.0
    processed_value: float = 0.0
    action_id: Optional[str] = None
    is_pressed: bool = False
    timestamp: float = field(default_factory=time.time)
    frame_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "device": self.device.value,
            "input_code": self.input_code,
            "raw_value": self.raw_value,
            "processed_value": self.processed_value,
            "action_id": self.action_id, "is_pressed": self.is_pressed,
            "timestamp": self.timestamp, "frame_number": self.frame_number,
        }


class InputMapSystem:
    """
    Configurable input mapping engine for multi-device game controls.

    Maps raw hardware events to logical game actions through a layered
    context stack. Supports action bindings across keyboard, mouse,
    gamepad, touch, and joystick devices with configurable dead zones,
    axis smoothing, gesture recognition, and device calibration.
    """

    _instance: Optional["InputMapSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_ACTIONS = 500
    MAX_BINDINGS_PER_ACTION = 20
    MAX_CONTEXTS = 100
    MAX_CONTEXT_STACK = 16
    MAX_GESTURES = 50

    def __init__(self):
        self._actions: Dict[str, InputAction] = {}
        self._contexts: Dict[str, InputContext] = {}
        self._context_stack: List[str] = []
        self._device_profiles: Dict[InputDevice, DeviceProfile] = {}
        self._gesture_patterns: Dict[str, List[Tuple[float, float]]] = {}
        self._action_states: Dict[str, float] = {}
        self._previous_frame_states: Dict[str, float] = {}
        self._event_history: List[InputEvent] = []
        self._total_events_processed: int = 0
        self._total_actions_triggered: int = 0
        self._frame_number: int = 0
        for device in InputDevice:
            self._device_profiles[device] = DeviceProfile(device=device)

    @classmethod
    def get_instance(cls) -> "InputMapSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Action Management
    # ------------------------------------------------------------------

    def define_action(
        self, name: str, action_type: InputActionType,
        default_bindings: Optional[List[Dict[str, Any]]] = None,
        category: str = "",
    ) -> Optional[InputAction]:
        if len(self._actions) >= self.MAX_ACTIONS:
            return None
        action = InputAction(name=name, action_type=action_type, category=category)
        if default_bindings:
            for b in default_bindings:
                try:
                    device = InputDevice(b.get("device", "keyboard"))
                except ValueError:
                    device = InputDevice.KEYBOARD
                binding = ActionBinding(
                    device=device, input_code=b.get("input_code", ""),
                    modifiers=b.get("modifiers", []),
                    scale=b.get("scale", 1.0), invert=b.get("invert", False),
                )
                action.bindings.append(binding)
        self._actions[action.id] = action
        self._action_states[action.id] = 0.0
        self._previous_frame_states[action.id] = 0.0
        return action

    # ------------------------------------------------------------------
    # Binding Management
    # ------------------------------------------------------------------

    def bind_action(
        self, action_id: str, device: InputDevice, input_code: str,
        modifiers: Optional[List[str]] = None, scale: float = 1.0,
        invert: bool = False,
    ) -> bool:
        action = self._actions.get(action_id)
        if action is None or len(action.bindings) >= self.MAX_BINDINGS_PER_ACTION:
            return False
        action.bindings.append(ActionBinding(
            device=device, input_code=input_code,
            modifiers=modifiers or [], scale=scale, invert=invert,
        ))
        return True

    # ------------------------------------------------------------------
    # Context Management
    # ------------------------------------------------------------------

    def create_context(
        self, name: str, priority: int = 0,
    ) -> Optional[InputContext]:
        if len(self._contexts) >= self.MAX_CONTEXTS:
            return None
        ctx = InputContext(name=name, priority=priority)
        self._contexts[ctx.id] = ctx
        return ctx

    def push_context(self, context_id: str) -> bool:
        if context_id not in self._contexts or len(self._context_stack) >= self.MAX_CONTEXT_STACK:
            return False
        if context_id in self._context_stack:
            self._context_stack.remove(context_id)
        self._context_stack.append(context_id)
        self._contexts[context_id].is_active = True
        return True

    def pop_context(self) -> Optional[str]:
        if not self._context_stack:
            return None
        ctx_id = self._context_stack.pop()
        if ctx_id in self._contexts:
            self._contexts[ctx_id].is_active = False
        return ctx_id

    # ------------------------------------------------------------------
    # Dead Zone & Axis Configuration
    # ------------------------------------------------------------------

    def set_dead_zone(
        self, device: InputDevice, mode: DeadZoneMode, threshold: float,
    ) -> bool:
        profile = self._device_profiles.get(device)
        if profile is None:
            return False
        profile.dead_zone_mode = mode
        profile.dead_zone_threshold = max(0.0, min(0.5, threshold))
        return True

    def set_axis_smoothing(self, action_id: str, smoothing_factor: float) -> bool:
        action = self._actions.get(action_id)
        if action is None or action.action_type != InputActionType.AXIS:
            return False
        action.axis_smoothing = max(0.0, min(1.0, smoothing_factor))
        return True

    def _apply_dead_zone(
        self, device: InputDevice, x: float, y: float,
    ) -> Tuple[float, float]:
        profile = self._device_profiles.get(device)
        if profile is None:
            return (x, y)
        threshold = profile.dead_zone_threshold
        mode = profile.dead_zone_mode
        if mode == DeadZoneMode.RAW:
            return (x, y)
        magnitude = math.sqrt(x * x + y * y)
        if mode == DeadZoneMode.CIRCULAR:
            if magnitude < threshold:
                return (0.0, 0.0)
            scale = (magnitude - threshold) / (1.0 - threshold)
        elif mode == DeadZoneMode.SQUARE:
            if abs(x) < threshold and abs(y) < threshold:
                return (0.0, 0.0)
            scale = 1.0
        elif mode == DeadZoneMode.CROSS:
            if abs(x) < threshold:
                x = 0.0
            if abs(y) < threshold:
                y = 0.0
            scale = 1.0
        else:
            scale = 1.0
        if magnitude > 0:
            return ((x / magnitude) * scale, (y / magnitude) * scale)
        return (0.0, 0.0)

    # ------------------------------------------------------------------
    # Input Processing
    # ------------------------------------------------------------------

    def process_raw_input(
        self, device: InputDevice, input_code: str, value: float,
    ) -> List[Dict[str, Any]]:
        profile = self._device_profiles.get(device)
        if profile is None:
            return []

        if profile.invert_x and input_code in ("axis_x", "mouse_x"):
            value = -value
        if profile.invert_y and input_code in ("axis_y", "mouse_y"):
            value = -value
        value *= profile.axis_sensitivity

        event = InputEvent(
            device=device, input_code=input_code,
            raw_value=value, processed_value=value,
            is_pressed=abs(value) > 0.5, frame_number=self._frame_number,
        )
        self._event_history.append(event)
        if len(self._event_history) > 200:
            self._event_history = self._event_history[-200:]
        self._total_events_processed += 1

        triggered: List[Dict[str, Any]] = []
        for action_id in self._get_active_action_ids():
            action = self._actions.get(action_id)
            if action is None or not action.is_enabled:
                continue
            for binding in action.bindings:
                if binding.device != device or binding.input_code != input_code:
                    continue
                processed = value * binding.scale
                if binding.invert:
                    processed = -processed
                event.action_id = action_id
                event.processed_value = processed
                self._previous_frame_states[action_id] = self._action_states.get(action_id, 0.0)
                if action.action_type == InputActionType.AXIS and action.axis_smoothing > 0:
                    prev = self._action_states.get(action_id, 0.0)
                    processed = prev + (processed - prev) * (1.0 - action.axis_smoothing)
                self._action_states[action_id] = processed
                self._total_actions_triggered += 1
                triggered.append({
                    "action_id": action_id, "action_name": action.name,
                    "value": processed, "device": device.value,
                })
                break
        return triggered

    def _get_active_action_ids(self) -> List[str]:
        result: List[str] = []
        for ctx_id in reversed(self._context_stack):
            ctx = self._contexts.get(ctx_id)
            if ctx is not None and ctx.is_active:
                result.extend(ctx.action_ids)
                if ctx.consumes_input:
                    break
        if not result:
            result.extend(self._actions.keys())
        return result

    def get_action_state(self, action_id: str) -> Dict[str, Any]:
        current = self._action_states.get(action_id, 0.0)
        previous = self._previous_frame_states.get(action_id, 0.0)
        action = self._actions.get(action_id)
        return {
            "action_id": action_id, "current_value": current,
            "previous_value": previous,
            "is_pressed": abs(current) > 0.5,
            "just_pressed": abs(current) > 0.5 and abs(previous) <= 0.5,
            "just_released": abs(current) <= 0.5 and abs(previous) > 0.5,
            "action_name": action.name if action else "",
        }

    # ------------------------------------------------------------------
    # Gesture Recognition
    # ------------------------------------------------------------------

    def add_gesture_recognizer(
        self, name: str, pattern: List[Tuple[float, float]],
    ) -> bool:
        if len(self._gesture_patterns) >= self.MAX_GESTURES:
            return False
        self._gesture_patterns[name] = pattern
        return True

    # ------------------------------------------------------------------
    # Device Calibration
    # ------------------------------------------------------------------

    def calibrate_device(self, device: InputDevice) -> Dict[str, Any]:
        profile = self._device_profiles.get(device)
        if profile is None:
            return {"error": "Unknown device"}
        profile.calibration_data = {
            "center_x": 0.0, "center_y": 0.0,
            "range_x": 1.0, "range_y": 1.0,
            "calibrated_at": time.time(),
        }
        profile.is_connected = True
        return profile.to_dict()

    # ------------------------------------------------------------------
    # Profile Import / Export
    # ------------------------------------------------------------------

    def export_input_profile(self) -> Dict[str, Any]:
        actions_data = [
            {"name": a.name, "action_type": a.action_type.value,
             "bindings": [b.to_dict() for b in a.bindings],
             "category": a.category}
            for a in self._actions.values()
        ]
        contexts_data = [
            {"name": c.name, "priority": c.priority,
             "action_ids": c.action_ids}
            for c in self._contexts.values()
        ]
        return {
            "format_version": 1, "actions": actions_data,
            "contexts": contexts_data,
            "device_profiles": {
                d.value: p.to_dict() for d, p in self._device_profiles.items()
            },
            "gestures": dict(self._gesture_patterns),
            "exported_at": time.time(),
        }

    def import_input_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        imported_actions = 0
        imported_contexts = 0
        for ad in data.get("actions", []):
            try:
                at = InputActionType(ad.get("action_type", "press"))
            except ValueError:
                at = InputActionType.PRESS
            if self.define_action(
                name=ad.get("name", ""), action_type=at,
                default_bindings=ad.get("bindings", []),
                category=ad.get("category", ""),
            ):
                imported_actions += 1
        for cd in data.get("contexts", []):
            ctx = self.create_context(
                name=cd.get("name", ""), priority=cd.get("priority", 0),
            )
            if ctx:
                ctx.action_ids = cd.get("action_ids", [])
                imported_contexts += 1
        for device_str, pd in data.get("device_profiles", {}).items():
            try:
                device = InputDevice(device_str)
            except ValueError:
                continue
            profile = self._device_profiles.get(device)
            if profile is not None:
                try:
                    profile.dead_zone_mode = DeadZoneMode(pd.get("dead_zone_mode", "circular"))
                except ValueError:
                    pass
                profile.dead_zone_threshold = pd.get("dead_zone_threshold", 0.15)
                profile.axis_sensitivity = pd.get("axis_sensitivity", 1.0)
                profile.invert_x = pd.get("invert_x", False)
                profile.invert_y = pd.get("invert_y", False)
        for name, pattern in data.get("gestures", {}).items():
            self._gesture_patterns[name] = pattern
        return {"imported_actions": imported_actions, "imported_contexts": imported_contexts}

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        device_bindings: Dict[str, int] = {}
        for action in self._actions.values():
            for b in action.bindings:
                d = b.device.value
                device_bindings[d] = device_bindings.get(d, 0) + 1
        return {
            "total_actions": len(self._actions),
            "total_contexts": len(self._contexts),
            "context_stack_depth": len(self._context_stack),
            "total_bindings": sum(len(a.bindings) for a in self._actions.values()),
            "total_gestures": len(self._gesture_patterns),
            "total_events_processed": self._total_events_processed,
            "total_actions_triggered": self._total_actions_triggered,
            "current_frame": self._frame_number,
            "connected_devices": sum(
                1 for p in self._device_profiles.values() if p.is_connected
            ),
            "bindings_by_device": device_bindings,
            "active_context": self._context_stack[-1] if self._context_stack else None,
        }


def get_input_map() -> InputMapSystem:
    return InputMapSystem.get_instance()