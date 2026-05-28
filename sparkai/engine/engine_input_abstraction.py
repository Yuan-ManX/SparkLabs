"""
SparkLabs Engine - Input Abstraction Layer

Pluggable input device abstraction layer that maps physical input devices
(keyboard, mouse, gamepad, touch, VR controllers) to logical game actions.
Supports remapping, dead zones, sensitivity curves, and multi-device
aggregation through configurable input profiles.

Architecture:
  InputAbstraction (singleton)
    |-- BindingRegistry (catalog of InputBinding entries mapping physical to logical)
    |-- ProfileManager (named input profiles with activation/deactivation)
    |-- FrameProcessor (raw input -> processed action values per frame)
    |-- ActionStateTracker (current/previous frame comparison for edge detection)
    |-- DeadZoneEngine (radial, axial, scaled-radial dead zone computation)
    |-- BindingValidator (conflict detection and parameter validation)
    |-- ProfileSerializer (import/export of profiles and bindings)

Data Flow:
  1. Physical devices emit raw input dicts
  2. process_raw_input() receives them each frame
  3. Active profile bindings match raw inputs to logical actions
  4. Dead zones, sensitivity, and inversion are applied
  5. An InputFrame is produced with active_actions mapped to values
  6. Action state queries (pressed, just_pressed, just_released) compare frames

Binding Types:
  - Simple: one physical input maps to one logical action
  - Composite: multiple physical inputs combine to produce one action value
  - Chord: multiple actions must be simultaneously active (e.g. modifiers)

Dead Zone Strategies:
  - RADIAL: magnitude below threshold yields zero, above is linearly remapped
  - AXIAL: per-axis threshold with no remapping; raw above, zero below
  - SCALED_RADIAL: quadratic remapping above threshold for smooth curves
  - NONE: raw values pass through unmodified

Sensitivity Curves:
  - 1.0: linear pass-through (no modification)
  - < 1.0: accelerated response (more sensitive to small inputs)
  - > 1.0: dampened response (less sensitive, more granular control)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


class DeviceType(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"
    TOUCH = "touch"
    VR_CONTROLLER = "vr_controller"
    ARCADE_STICK = "arcade_stick"
    RACING_WHEEL = "racing_wheel"
    FLIGHT_STICK = "flight_stick"
    MOTION_SENSOR = "motion_sensor"


class InputEvent(Enum):
    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    AXIS_CHANGE = "axis_change"
    GESTURE = "gesture"
    POINTER_MOVE = "pointer_move"


class AxisType(Enum):
    DIGITAL = "digital"
    ANALOG_1D = "analog_1d"
    ANALOG_2D = "analog_2d"
    ANALOG_3D = "analog_3d"


class DeadZoneMode(Enum):
    RADIAL = "radial"
    AXIAL = "axial"
    SCALED_RADIAL = "scaled_radial"
    NONE = "none"


# -- Device capability constants --
DEVICE_AXIS_COUNTS: Dict[DeviceType, int] = {
    DeviceType.KEYBOARD: 0,
    DeviceType.MOUSE: 2,
    DeviceType.GAMEPAD: 6,
    DeviceType.TOUCH: 2,
    DeviceType.VR_CONTROLLER: 6,
    DeviceType.ARCADE_STICK: 2,
    DeviceType.RACING_WHEEL: 3,
    DeviceType.FLIGHT_STICK: 4,
    DeviceType.MOTION_SENSOR: 3,
}

DEVICE_BUTTON_COUNTS: Dict[DeviceType, int] = {
    DeviceType.KEYBOARD: 256,
    DeviceType.MOUSE: 8,
    DeviceType.GAMEPAD: 24,
    DeviceType.TOUCH: 0,
    DeviceType.VR_CONTROLLER: 12,
    DeviceType.ARCADE_STICK: 16,
    DeviceType.RACING_WHEEL: 16,
    DeviceType.FLIGHT_STICK: 32,
    DeviceType.MOTION_SENSOR: 2,
}


@dataclass
class InputBinding:
    """Maps a single physical input to a logical game action.

    Each binding describes how a specific hardware input (key, button, axis)
    from a particular device type is transformed into a named game action.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_name: str = ""
    device_type: DeviceType = DeviceType.KEYBOARD
    physical_input: str = ""
    input_event: InputEvent = InputEvent.PRESS
    axis_type: AxisType = AxisType.DIGITAL
    dead_zone: float = 0.1
    sensitivity: float = 1.0
    invert: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_name": self.action_name,
            "device_type": self.device_type.value,
            "physical_input": self.physical_input,
            "input_event": self.input_event.value,
            "axis_type": self.axis_type.value,
            "dead_zone": self.dead_zone,
            "sensitivity": self.sensitivity,
            "invert": self.invert,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputBinding":
        binding = cls(
            action_name=data.get("action_name", ""),
            device_type=DeviceType(data.get("device_type", "keyboard")),
            physical_input=data.get("physical_input", ""),
            input_event=InputEvent(data.get("input_event", "press")),
            axis_type=AxisType(data.get("axis_type", "digital")),
            dead_zone=float(data.get("dead_zone", 0.1)),
            sensitivity=float(data.get("sensitivity", 1.0)),
            invert=bool(data.get("invert", False)),
        )
        if data.get("id"):
            binding.id = data["id"]
        if data.get("created_at"):
            binding.created_at = float(data["created_at"])
        return binding

    def is_valid(self) -> bool:
        if not self.action_name.strip():
            return False
        if not self.physical_input.strip():
            return False
        if self.dead_zone < 0.0 or self.dead_zone > 1.0:
            return False
        if self.sensitivity <= 0.0:
            return False
        return True


@dataclass
class InputProfile:
    """A named collection of input bindings representing a control scheme.

    Profiles can be activated and deactivated to switch between different
    control configurations such as gameplay, menu navigation, or vehicle
    controls. Only one profile may be active at a time.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    bindings: List[str] = field(default_factory=list)
    is_active: bool = False
    device_types: List[DeviceType] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "bindings": list(self.bindings),
            "is_active": self.is_active,
            "device_types": [dt.value for dt in self.device_types],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputProfile":
        device_types_raw = data.get("device_types", [])
        device_types = [
            DeviceType(dt) if isinstance(dt, str) else dt
            for dt in device_types_raw
        ]
        profile = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            bindings=list(data.get("bindings", [])),
            device_types=device_types,
        )
        if data.get("id"):
            profile.id = data["id"]
        if data.get("is_active"):
            profile.is_active = bool(data["is_active"])
        if data.get("created_at"):
            profile.created_at = float(data["created_at"])
        if data.get("updated_at"):
            profile.updated_at = float(data["updated_at"])
        return profile


@dataclass
class InputFrame:
    """A single frame of processed input data.

    Contains the mapping of logical action names to their computed values
    after dead zones, sensitivity curves, and inversion have been applied
    through the active profile's bindings.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    active_actions: Dict[str, float] = field(default_factory=dict)
    raw_inputs: List[Dict[str, Any]] = field(default_factory=list)
    processed_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "active_actions": dict(self.active_actions),
            "raw_input_count": len(self.raw_inputs),
            "processed_count": self.processed_count,
            "created_at": self.created_at,
        }


class InputAbstraction:
    """Singleton that provides a pluggable input device abstraction layer.

    Maps physical input devices to logical game actions with support for
    remapping, dead zones, sensitivity curves, and multi-device aggregation.
    """

    _instance: Optional["InputAbstraction"] = None
    _lock = threading.RLock()

    MAX_FRAMES = 10000
    MAX_BINDINGS = 5000
    MAX_PROFILES = 500

    def __new__(cls) -> "InputAbstraction":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._bindings: Dict[str, InputBinding] = {}
                    instance._profiles: Dict[str, InputProfile] = {}
                    instance._frames: Dict[int, InputFrame] = {}
                    instance._active_profile_id: Optional[str] = None
                    instance._current_action_values: Dict[str, float] = {}
                    instance._previous_action_values: Dict[str, float] = {}
                    instance._frame_counter: int = 0
                    instance._total_processed: int = 0
                    instance._total_frames: int = 0
                    instance._start_time: float = _time_module.time()
                    instance._action_hold_durations: Dict[str, float] = {}
                    instance._action_press_timestamps: Dict[str, float] = {}
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "InputAbstraction":
        return cls()

    # -- Binding Management --
    # ------------------------------------------------------------------

    def create_binding(
        self,
        action_name: str,
        device_type: DeviceType,
        physical_input: str,
        input_event: InputEvent,
        axis_type: AxisType = AxisType.DIGITAL,
        dead_zone: float = 0.1,
        sensitivity: float = 1.0,
        invert: bool = False,
    ) -> InputBinding:
        with self._lock:
            binding = InputBinding(
                action_name=action_name,
                device_type=device_type,
                physical_input=physical_input,
                input_event=input_event,
                axis_type=axis_type,
                dead_zone=max(0.0, min(1.0, dead_zone)),
                sensitivity=sensitivity,
                invert=invert,
            )
            self._bindings[binding.id] = binding
            if len(self._bindings) > self.MAX_BINDINGS:
                oldest = min(
                    self._bindings.keys(),
                    key=lambda k: self._bindings[k].created_at,
                )
                del self._bindings[oldest]
            return binding

    def update_binding(
        self, binding_id: str, **updates: Any
    ) -> Optional[InputBinding]:
        with self._lock:
            binding = self._bindings.get(binding_id)
            if binding is None:
                return None
            allowed_fields = {
                "action_name",
                "device_type",
                "physical_input",
                "input_event",
                "axis_type",
                "dead_zone",
                "sensitivity",
                "invert",
            }
            for key, value in updates.items():
                if key in allowed_fields:
                    if key == "dead_zone":
                        value = max(0.0, min(1.0, float(value)))
                    if key == "sensitivity":
                        value = float(value)
                    if key == "invert":
                        value = bool(value)
                    setattr(binding, key, value)
            return binding

    def remove_binding(self, binding_id: str) -> bool:
        with self._lock:
            if binding_id not in self._bindings:
                return False
            del self._bindings[binding_id]
            for profile in self._profiles.values():
                if binding_id in profile.bindings:
                    profile.bindings.remove(binding_id)
                    profile.updated_at = _time_module.time()
            return True

    def get_binding(self, binding_id: str) -> Optional[InputBinding]:
        return self._bindings.get(binding_id)

    def list_bindings(
        self,
        device_type: Optional[DeviceType] = None,
        action_name: Optional[str] = None,
    ) -> List[InputBinding]:
        results = list(self._bindings.values())
        if device_type is not None:
            results = [b for b in results if b.device_type == device_type]
        if action_name is not None:
            results = [b for b in results if b.action_name == action_name]
        return results

    def find_conflicting_bindings(
        self, device_type: DeviceType, physical_input: str
    ) -> List[InputBinding]:
        physical_upper = physical_input.upper()
        return [
            b
            for b in self._bindings.values()
            if b.device_type == device_type
            and b.physical_input.upper() == physical_upper
        ]

    def get_binding_count_by_device(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for binding in self._bindings.values():
            key = binding.device_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def clone_binding(self, binding_id: str) -> Optional[InputBinding]:
        with self._lock:
            original = self._bindings.get(binding_id)
            if original is None:
                return None
            cloned = InputBinding(
                action_name=original.action_name + "_copy",
                device_type=original.device_type,
                physical_input=original.physical_input,
                input_event=original.input_event,
                axis_type=original.axis_type,
                dead_zone=original.dead_zone,
                sensitivity=original.sensitivity,
                invert=original.invert,
            )
            self._bindings[cloned.id] = cloned
            return cloned

    def import_bindings(
        self, data_list: List[Dict[str, Any]]
    ) -> List[InputBinding]:
        imported = []
        for data in data_list:
            binding = InputBinding.from_dict(data)
            self._bindings[binding.id] = binding
            imported.append(binding)
        return imported

    def export_bindings(
        self,
        device_type: Optional[DeviceType] = None,
        action_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        bindings = self.list_bindings(
            device_type=device_type, action_name=action_name
        )
        return [b.to_dict() for b in bindings]

    # -- Profile Management --
    # ------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        description: str = "",
        device_types: Optional[List[DeviceType]] = None,
    ) -> InputProfile:
        with self._lock:
            if device_types is None:
                device_types = []
            profile = InputProfile(
                name=name,
                description=description,
                device_types=list(device_types),
            )
            self._profiles[profile.id] = profile
            if len(self._profiles) > self.MAX_PROFILES:
                oldest = min(
                    self._profiles.keys(),
                    key=lambda k: self._profiles[k].created_at,
                )
                del self._profiles[oldest]
            return profile

    def add_binding_to_profile(
        self, profile_id: str, binding_id: str
    ) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            binding = self._bindings.get(binding_id)
            if profile is None or binding is None:
                return False
            if binding_id in profile.bindings:
                return False
            profile.bindings.append(binding_id)
            profile.updated_at = _time_module.time()
            return True

    def remove_binding_from_profile(
        self, profile_id: str, binding_id: str
    ) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False
            if binding_id not in profile.bindings:
                return False
            profile.bindings.remove(binding_id)
            profile.updated_at = _time_module.time()
            return True

    def activate_profile(self, profile_id: str) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False
            if self._active_profile_id is not None:
                previous = self._profiles.get(self._active_profile_id)
                if previous is not None:
                    previous.is_active = False
            profile.is_active = True
            self._active_profile_id = profile_id
            profile.updated_at = _time_module.time()
            self._current_action_values.clear()
            self._previous_action_values.clear()
            self._action_hold_durations.clear()
            self._action_press_timestamps.clear()
            return True

    def deactivate_profile(self, profile_id: str) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False
            if not profile.is_active:
                return False
            profile.is_active = False
            profile.updated_at = _time_module.time()
            if self._active_profile_id == profile_id:
                self._active_profile_id = None
                self._current_action_values.clear()
                self._previous_action_values.clear()
                self._action_hold_durations.clear()
                self._action_press_timestamps.clear()
            return True

    def get_active_profile(self) -> Optional[InputProfile]:
        if self._active_profile_id is None:
            return None
        return self._profiles.get(self._active_profile_id)

    def get_profile(self, profile_id: str) -> Optional[InputProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[InputProfile]:
        return list(self._profiles.values())

    def delete_profile(self, profile_id: str) -> bool:
        with self._lock:
            if profile_id not in self._profiles:
                return False
            if self._active_profile_id == profile_id:
                self.deactivate_profile(profile_id)
            del self._profiles[profile_id]
            return True

    def clone_profile(self, profile_id: str) -> Optional[InputProfile]:
        with self._lock:
            original = self._profiles.get(profile_id)
            if original is None:
                return None
            cloned = InputProfile(
                name=original.name + " (Copy)",
                description=original.description,
                bindings=list(original.bindings),
                device_types=list(original.device_types),
            )
            self._profiles[cloned.id] = cloned
            return cloned

    def import_profile(self, data: Dict[str, Any]) -> InputProfile:
        profile = InputProfile.from_dict(data)
        self._profiles[profile.id] = profile
        return profile

    def export_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        return profile.to_dict()

    def export_active_profile_config(
        self,
    ) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        profile = self.get_active_profile()
        if profile is None:
            return None
        profile_data = profile.to_dict()
        bindings_data = [
            self._bindings[bid].to_dict()
            for bid in profile.bindings
            if bid in self._bindings
        ]
        return profile_data, bindings_data

    # -- Input Processing --
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_dead_zone_radial(value: float, dead_zone: float) -> float:
        magnitude = abs(value)
        if magnitude <= dead_zone:
            return 0.0
        normalized = (magnitude - dead_zone) / (1.0 - dead_zone)
        sign = -1.0 if value < 0 else 1.0
        return sign * normalized

    @staticmethod
    def _apply_dead_zone_axial(value: float, dead_zone: float) -> float:
        if abs(value) <= dead_zone:
            return 0.0
        return value

    @staticmethod
    def _apply_dead_zone_scaled_radial(
        value: float, dead_zone: float
    ) -> float:
        magnitude = abs(value)
        if magnitude <= dead_zone:
            return 0.0
        normalized = (magnitude - dead_zone) / (1.0 - dead_zone)
        sign = -1.0 if value < 0 else 1.0
        return sign * (1.0 - (1.0 - normalized) * (1.0 - normalized))

    @staticmethod
    def _apply_dead_zone(
        value: float, dead_zone: float, mode: DeadZoneMode
    ) -> float:
        if mode == DeadZoneMode.NONE or dead_zone <= 0.0:
            return value
        if mode == DeadZoneMode.RADIAL:
            return InputAbstraction._apply_dead_zone_radial(value, dead_zone)
        if mode == DeadZoneMode.AXIAL:
            return InputAbstraction._apply_dead_zone_axial(value, dead_zone)
        if mode == DeadZoneMode.SCALED_RADIAL:
            return InputAbstraction._apply_dead_zone_scaled_radial(
                value, dead_zone
            )
        return value

    @staticmethod
    def _apply_sensitivity(value: float, sensitivity: float) -> float:
        if sensitivity == 1.0 or value == 0.0:
            return value
        sign = -1.0 if value < 0 else 1.0
        return sign * (abs(value) ** (1.0 / max(0.01, sensitivity)))

    @staticmethod
    def _match_raw_to_binding(
        raw: Dict[str, Any], binding: InputBinding
    ) -> bool:
        raw_device = raw.get("device", "").upper()
        raw_input = raw.get("input", "")
        binding_device_name = binding.device_type.name
        if raw_device != binding_device_name:
            return False
        if raw_input.upper() != binding.physical_input.upper():
            return False
        return True

    def _select_dead_zone_mode(
        self, binding: InputBinding
    ) -> DeadZoneMode:
        if binding.dead_zone <= 0.0:
            return DeadZoneMode.NONE
        if binding.axis_type == AxisType.DIGITAL:
            return DeadZoneMode.AXIAL
        return DeadZoneMode.RADIAL

    @staticmethod
    def _clamp_action_value(value: float) -> float:
        return max(-1.0, min(1.0, value))

    @staticmethod
    def _resolve_action_value(
        existing: float, incoming: float
    ) -> float:
        abs_existing = abs(existing)
        abs_incoming = abs(incoming)
        if abs_incoming > abs_existing:
            return incoming
        return existing

    def _process_single_binding(
        self, binding: InputBinding, raw_value: float
    ) -> float:
        mode = self._select_dead_zone_mode(binding)
        value = self._apply_dead_zone(raw_value, binding.dead_zone, mode)
        value = self._apply_sensitivity(value, binding.sensitivity)
        if binding.invert:
            value = -value
        if binding.axis_type == AxisType.DIGITAL:
            value = 1.0 if value > 0.5 else 0.0
        return self._clamp_action_value(value)

    def process_raw_input(
        self, raw_inputs: List[Dict[str, Any]]
    ) -> InputFrame:
        with self._lock:
            self._previous_action_values = dict(
                self._current_action_values
            )
            self._current_action_values.clear()
            profile = self.get_active_profile()
            processed = 0
            if profile is not None:
                active_binding_ids = set(profile.bindings)
                for raw in raw_inputs:
                    raw_value = float(raw.get("value", 0.0))
                    for bid in active_binding_ids:
                        binding = self._bindings.get(bid)
                        if binding is None:
                            continue
                        if not self._match_raw_to_binding(raw, binding):
                            continue
                        processed += 1
                        final_value = self._process_single_binding(
                            binding, raw_value
                        )
                        action = binding.action_name
                        existing = self._current_action_values.get(
                            action, 0.0
                        )
                        self._current_action_values[
                            action
                        ] = self._resolve_action_value(
                            existing, final_value
                        )
            else:
                for raw in raw_inputs:
                    raw_device = raw.get("device", "")
                    raw_input_name = raw.get("input", "")
                    raw_value = float(raw.get("value", 0.0))
                    if raw_device and raw_input_name:
                        action_key = (
                            f"{raw_device}:{raw_input_name}".lower()
                        )
                        self._current_action_values[
                            action_key
                        ] = self._clamp_action_value(raw_value)
            self._frame_counter += 1
            self._total_frames += 1
            self._total_processed += processed
            now = _time_module.time()
            self._update_hold_durations(now)
            frame = InputFrame(
                frame_number=self._frame_counter,
                active_actions=dict(self._current_action_values),
                raw_inputs=list(raw_inputs),
                processed_count=processed,
            )
            self._frames[self._frame_counter] = frame
            while len(self._frames) > self.MAX_FRAMES:
                oldest_key = min(self._frames.keys())
                del self._frames[oldest_key]
            return frame

    def _update_hold_durations(self, now: float) -> None:
        active = set(self._current_action_values.keys())
        previous = set(self._previous_action_values.keys())
        newly_pressed = active - previous
        for action in newly_pressed:
            self._action_press_timestamps[action] = now
            self._action_hold_durations[action] = 0.0
        still_held = active & previous
        for action in still_held:
            press_time = self._action_press_timestamps.get(action, now)
            self._action_hold_durations[action] = now - press_time
        released = previous - active
        for action in released:
            self._action_press_timestamps.pop(action, None)
            self._action_hold_durations.pop(action, None)

    # -- Action State Queries --
    # ------------------------------------------------------------------

    def get_action_value(self, action_name: str) -> float:
        return self._current_action_values.get(action_name, 0.0)

    def is_action_pressed(self, action_name: str) -> bool:
        value = self._current_action_values.get(action_name, 0.0)
        return abs(value) > 0.0

    def was_action_just_pressed(self, action_name: str) -> bool:
        current = self._current_action_values.get(action_name, 0.0)
        previous = self._previous_action_values.get(action_name, 0.0)
        return abs(current) > 0.0 and abs(previous) == 0.0

    def was_action_just_released(self, action_name: str) -> bool:
        current = self._current_action_values.get(action_name, 0.0)
        previous = self._previous_action_values.get(action_name, 0.0)
        return abs(current) == 0.0 and abs(previous) > 0.0

    def get_action_hold_duration(self, action_name: str) -> float:
        return self._action_hold_durations.get(action_name, 0.0)

    def get_active_actions(self) -> List[str]:
        return [
            name
            for name, value in self._current_action_values.items()
            if abs(value) > 0.0
        ]

    def is_chord_active(
        self, required_actions: List[str], require_simultaneous: bool = True
    ) -> bool:
        if not required_actions:
            return False
        for action in required_actions:
            if not self.is_action_pressed(action):
                return False
        if require_simultaneous and required_actions:
            first_action = required_actions[0]
            base_stamp = self._action_press_timestamps.get(first_action)
            if base_stamp is None:
                return False
            for action in required_actions[1:]:
                stamp = self._action_press_timestamps.get(action)
                if stamp is None:
                    return False
                if abs(stamp - base_stamp) > 0.5:
                    return False
        return True

    # -- Frame Retrieval --
    # ------------------------------------------------------------------

    def get_input_frame(self, frame_number: int) -> Optional[InputFrame]:
        return self._frames.get(frame_number)

    def get_current_frame(self) -> Optional[InputFrame]:
        return self._frames.get(self._frame_counter)

    def get_previous_frame(self) -> Optional[InputFrame]:
        if self._frame_counter <= 1:
            return None
        return self._frames.get(self._frame_counter - 1)

    def get_recent_frames(self, count: int = 10) -> List[InputFrame]:
        start = max(1, self._frame_counter - count + 1)
        return [
            self._frames[i]
            for i in range(start, self._frame_counter + 1)
            if i in self._frames
        ]

    def get_frame_range(
        self, start_frame: int, end_frame: int
    ) -> List[InputFrame]:
        return [
            self._frames[i]
            for i in range(
                max(1, start_frame), min(end_frame, self._frame_counter) + 1
            )
            if i in self._frames
        ]

    # -- Statistics --
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        active_binding_count = 0
        covered_device_types: List[str] = []
        profile = self.get_active_profile()
        if profile is not None:
            active_binding_count = len(profile.bindings)
            covered_device_types = [
                dt.value for dt in profile.device_types
            ]
        elapsed = _time_module.time() - self._start_time
        avg_per_frame = 0.0
        if self._total_frames > 0:
            avg_per_frame = self._total_processed / self._total_frames
        return {
            "total_bindings": len(self._bindings),
            "total_profiles": len(self._profiles),
            "total_frames": self._total_frames,
            "total_processed": self._total_processed,
            "average_processed_per_frame": round(avg_per_frame, 4),
            "active_profile": (
                profile.name if profile is not None else None
            ),
            "active_binding_count": active_binding_count,
            "active_device_types": covered_device_types,
            "stored_frames": len(self._frames),
            "current_frame": self._frame_counter,
            "tracked_actions": len(self._current_action_values),
            "held_actions": len(self._action_hold_durations),
            "binding_counts_by_device": self.get_binding_count_by_device(),
            "uptime_seconds": round(elapsed, 3),
        }

    def get_device_stats(self, device_type: DeviceType) -> Dict[str, Any]:
        binding_count = sum(
            1
            for b in self._bindings.values()
            if b.device_type == device_type
        )
        axis_count = DEVICE_AXIS_COUNTS.get(device_type, 0)
        button_count = DEVICE_BUTTON_COUNTS.get(device_type, 0)
        return {
            "device_type": device_type.value,
            "binding_count": binding_count,
            "max_axes": axis_count,
            "max_buttons": button_count,
        }

    # -- Reset and Lifecycle --
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._bindings.clear()
            self._profiles.clear()
            self._frames.clear()
            self._active_profile_id = None
            self._current_action_values.clear()
            self._previous_action_values.clear()
            self._frame_counter = 0
            self._total_processed = 0
            self._total_frames = 0
            self._start_time = _time_module.time()
            self._action_hold_durations.clear()
            self._action_press_timestamps.clear()

    def clear_frames(self) -> None:
        with self._lock:
            self._frames.clear()

    def clear_bindings(self) -> None:
        with self._lock:
            self._bindings.clear()
            for profile in self._profiles.values():
                profile.bindings.clear()
                profile.updated_at = _time_module.time()

    def clear_action_state(self) -> None:
        with self._lock:
            self._current_action_values.clear()
            self._previous_action_values.clear()
            self._action_hold_durations.clear()
            self._action_press_timestamps.clear()


def get_input_abstraction() -> InputAbstraction:
    return InputAbstraction.get_instance()