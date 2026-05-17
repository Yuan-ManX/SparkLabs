"""
Input Profile System - Device-aware input profile management for AI-generated games.

Architecture:
    InputProfileSystem
    |-- InputDevice (keyboard/mouse, gamepad variants, touch, specialty controllers)
    |-- ActionType (press, release, hold, double-tap, axis, gesture)
    |-- DeadZoneMode (none, radial, axial)
    |-- InputBinding (individual action-to-input mapping)
    |-- ProfileDefinition (collection of bindings for a device)
    |-- ProfileExporter (serialize/deserialize profiles)
    |-- ProfileValidator (check binding conflicts and dead-zone coherence)

Manages player input profiles across different controller types. Each profile
groups bindings for a specific device, supports auto-configuration via device
detection, and enables runtime profile switching for multi-controller games.
"""

from __future__ import annotations

import copy
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class InputDevice(Enum):
    KEYBOARD_MOUSE = "keyboard_mouse"
    GAMEPAD_XBOX = "gamepad_xbox"
    GAMEPAD_PS = "gamepad_ps"
    GAMEPAD_SWITCH = "gamepad_switch"
    TOUCHSCREEN = "touchscreen"
    ARCADE_STICK = "arcade_stick"
    STEERING_WHEEL = "steering_wheel"
    FLIGHT_STICK = "flight_stick"
    VR_CONTROLLER = "vr_controller"


class ActionType(Enum):
    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    DOUBLE_TAP = "double_tap"
    AXIS = "axis"
    GESTURE = "gesture"


class DeadZoneMode(Enum):
    NONE = "none"
    RADIAL = "radial"
    AXIAL = "axial"


@dataclass
class InputBinding:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_name: str = ""
    action_type: ActionType = ActionType.PRESS
    device: InputDevice = InputDevice.KEYBOARD_MOUSE
    primary_input: str = ""
    secondary_input: str = ""
    dead_zone: float = 0.2
    sensitivity: float = 1.0
    invert: bool = False
    rumble_intensity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_name": self.action_name,
            "action_type": self.action_type.value,
            "device": self.device.value,
            "primary_input": self.primary_input,
            "secondary_input": self.secondary_input,
            "dead_zone": self.dead_zone,
            "sensitivity": self.sensitivity,
            "invert": self.invert,
            "rumble_intensity": self.rumble_intensity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputBinding":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            action_name=data.get("action_name", ""),
            action_type=ActionType(data.get("action_type", "press")),
            device=InputDevice(data.get("device", "keyboard_mouse")),
            primary_input=data.get("primary_input", ""),
            secondary_input=data.get("secondary_input", ""),
            dead_zone=data.get("dead_zone", 0.2),
            sensitivity=data.get("sensitivity", 1.0),
            invert=data.get("invert", False),
            rumble_intensity=data.get("rumble_intensity", 0.0),
        )


@dataclass
class ProfileDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    device: InputDevice = InputDevice.KEYBOARD_MOUSE
    bindings: Dict[str, InputBinding] = field(default_factory=dict)
    is_active: bool = False
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "device": self.device.value,
            "bindings": {k: v.to_dict() for k, v in self.bindings.items()},
            "is_active": self.is_active,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileDefinition":
        profile = cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", ""),
            device=InputDevice(data.get("device", "keyboard_mouse")),
            is_active=data.get("is_active", False),
            created_at=data.get("created_at", time.time()),
            modified_at=data.get("modified_at", time.time()),
        )
        bindings_data = data.get("bindings", {})
        profile.bindings = {
            k: InputBinding.from_dict(v) for k, v in bindings_data.items()
        }
        return profile


class InputProfileSystem:
    _instance: Optional["InputProfileSystem"] = None
    _lock = threading.RLock()

    MAX_BINDINGS_PER_PROFILE = 256
    MAX_PROFILES = 64

    def __init__(self):
        self._profiles: Dict[str, ProfileDefinition] = {}
        self._active_profile_id: Optional[str] = None
        self._profile_count: int = 0
        self._binding_count: int = 0
        self._import_count: int = 0
        self._export_count: int = 0
        self._merge_count: int = 0

    @classmethod
    def get_instance(cls) -> "InputProfileSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_profile(self, name: str, device: InputDevice) -> ProfileDefinition:
        with self._lock:
            if len(self._profiles) >= self.MAX_PROFILES:
                raise RuntimeError(f"Maximum number of profiles ({self.MAX_PROFILES}) reached")

            profile = ProfileDefinition(name=name, device=device)
            self._profiles[profile.id] = profile
            self._profile_count += 1
            return profile

    def add_binding(self, profile_id: str, binding: InputBinding) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False
            if len(profile.bindings) >= self.MAX_BINDINGS_PER_PROFILE:
                return False

            profile.bindings[binding.id] = binding
            profile.modified_at = time.time()
            self._binding_count += 1
            return True

    def remove_binding(self, profile_id: str, binding_id: str) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False
            if binding_id not in profile.bindings:
                return False

            del profile.bindings[binding_id]
            profile.modified_at = time.time()
            self._binding_count -= 1
            return True

    def get_binding(self, profile_id: str, binding_id: str) -> Optional[InputBinding]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        return profile.bindings.get(binding_id)

    def set_active_profile(self, profile_id: str) -> bool:
        with self._lock:
            if profile_id not in self._profiles:
                return False

            if self._active_profile_id:
                prev = self._profiles.get(self._active_profile_id)
                if prev:
                    prev.is_active = False

            self._active_profile_id = profile_id
            self._profiles[profile_id].is_active = True
            return True

    def detect_device(self, device_hint: Optional[str] = None) -> InputDevice:
        mapping = {
            "xbox": InputDevice.GAMEPAD_XBOX,
            "ps": InputDevice.GAMEPAD_PS,
            "ps4": InputDevice.GAMEPAD_PS,
            "ps5": InputDevice.GAMEPAD_PS,
            "dualshock": InputDevice.GAMEPAD_PS,
            "dualsense": InputDevice.GAMEPAD_PS,
            "switch": InputDevice.GAMEPAD_SWITCH,
            "nintendo": InputDevice.GAMEPAD_SWITCH,
            "touch": InputDevice.TOUCHSCREEN,
            "arcade": InputDevice.ARCADE_STICK,
            "wheel": InputDevice.STEERING_WHEEL,
            "flight": InputDevice.FLIGHT_STICK,
            "vr": InputDevice.VR_CONTROLLER,
        }
        if device_hint:
            hint_lower = device_hint.lower()
            for key, device in mapping.items():
                if key in hint_lower:
                    return device
        return InputDevice.KEYBOARD_MOUSE

    def auto_configure(self, device: InputDevice) -> ProfileDefinition:
        with self._lock:
            profile = self.create_profile(f"Auto {device.value}", device)

            presets = AUTO_CONFIGURATION_PRESETS.get(device, {})
            for action_name, (primary, secondary, action_type, dead_zone) in presets.items():
                binding = InputBinding(
                    action_name=action_name,
                    action_type=action_type,
                    device=device,
                    primary_input=primary,
                    secondary_input=secondary,
                    dead_zone=dead_zone,
                )
                profile.bindings[binding.id] = binding
                self._binding_count += 1

            self.set_active_profile(profile.id)
            return profile

    def export_profile(self, profile_id: str) -> Optional[str]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        self._export_count += 1
        return json.dumps(profile.to_dict(), indent=2)

    def import_profile(self, json_str: str) -> Optional[ProfileDefinition]:
        with self._lock:
            try:
                data = json.loads(json_str)
                profile = ProfileDefinition.from_dict(data)
                self._profiles[profile.id] = profile
                self._profile_count += 1
                self._binding_count += len(profile.bindings)
                self._import_count += 1
                return profile
            except (json.JSONDecodeError, KeyError, ValueError):
                return None

    def merge_profiles(self, target_id: str, source_id: str, overwrite: bool = True) -> bool:
        with self._lock:
            target = self._profiles.get(target_id)
            source = self._profiles.get(source_id)
            if target is None or source is None:
                return False

            for binding in source.bindings.values():
                existing_keys = list(target.bindings.keys())
                existing_names = {b.action_name for b in target.bindings.values()}

                if binding.action_name in existing_names and not overwrite:
                    continue
                if binding.action_name in existing_names and overwrite:
                    to_remove = [
                        k for k, v in target.bindings.items()
                        if v.action_name == binding.action_name
                    ]
                    for k in to_remove:
                        del target.bindings[k]
                        self._binding_count -= 1

                merged = copy.deepcopy(binding)
                merged.id = uuid.uuid4().hex
                target.bindings[merged.id] = merged
                self._binding_count += 1

            target.modified_at = time.time()
            self._merge_count += 1
            return True

    def validate_profile(self, profile_id: str) -> Dict[str, Any]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return {"valid": False, "errors": [f"Profile {profile_id} not found"]}

        errors: List[str] = []
        warnings: List[str] = []
        seen_primary: Dict[str, str] = {}

        for binding in profile.bindings.values():
            if binding.dead_zone < 0.0 or binding.dead_zone > 1.0:
                errors.append(
                    f"Binding '{binding.action_name}': dead_zone {binding.dead_zone} out of range [0.0, 1.0]"
                )
            if binding.sensitivity <= 0.0:
                errors.append(
                    f"Binding '{binding.action_name}': sensitivity must be greater than 0"
                )

            if binding.primary_input and binding.primary_input in seen_primary:
                warnings.append(
                    f"Primary input '{binding.primary_input}' used by "
                    f"'{seen_primary[binding.primary_input]}' and '{binding.action_name}'"
                )
            if binding.primary_input:
                seen_primary[binding.primary_input] = binding.action_name

        valid = len(errors) == 0
        return {
            "valid": valid,
            "profile_id": profile_id,
            "profile_name": profile.name,
            "device": profile.device.value,
            "binding_count": len(profile.bindings),
            "errors": errors,
            "warnings": warnings,
        }

    def get_stats(self) -> Dict[str, Any]:
        active_name = None
        active_device = None
        if self._active_profile_id:
            active = self._profiles.get(self._active_profile_id)
            if active:
                active_name = active.name
                active_device = active.device.value

        device_counts: Dict[str, int] = {}
        total_bindings = 0
        for profile in self._profiles.values():
            device_key = profile.device.value
            device_counts[device_key] = device_counts.get(device_key, 0) + 1
            total_bindings += len(profile.bindings)

        return {
            "total_profiles": len(self._profiles),
            "total_bindings": total_bindings,
            "active_profile": active_name,
            "active_device": active_device,
            "profiles_by_device": device_counts,
            "profile_count_created": self._profile_count,
            "binding_count_added": self._binding_count,
            "imports": self._import_count,
            "exports": self._export_count,
            "merges": self._merge_count,
            "max_profiles": self.MAX_PROFILES,
            "max_bindings_per_profile": self.MAX_BINDINGS_PER_PROFILE,
        }


AUTO_CONFIGURATION_PRESETS: Dict[InputDevice, Dict[str, tuple]] = {
    InputDevice.KEYBOARD_MOUSE: {
        "move_up": ("W", "ArrowUp", ActionType.PRESS, 0.0),
        "move_down": ("S", "ArrowDown", ActionType.PRESS, 0.0),
        "move_left": ("A", "ArrowLeft", ActionType.PRESS, 0.0),
        "move_right": ("D", "ArrowRight", ActionType.PRESS, 0.0),
        "jump": ("Space", "", ActionType.PRESS, 0.0),
        "interact": ("E", "", ActionType.PRESS, 0.0),
        "pause": ("Escape", "", ActionType.PRESS, 0.0),
        "primary_action": ("MouseLeft", "", ActionType.PRESS, 0.0),
        "secondary_action": ("MouseRight", "", ActionType.PRESS, 0.0),
    },
    InputDevice.GAMEPAD_XBOX: {
        "move_horizontal": ("LeftStickX", "DPadX", ActionType.AXIS, 0.2),
        "move_vertical": ("LeftStickY", "DPadY", ActionType.AXIS, 0.2),
        "camera_horizontal": ("RightStickX", "", ActionType.AXIS, 0.2),
        "camera_vertical": ("RightStickY", "", ActionType.AXIS, 0.2),
        "jump": ("A", "", ActionType.PRESS, 0.0),
        "interact": ("X", "", ActionType.PRESS, 0.0),
        "reload": ("B", "", ActionType.PRESS, 0.0),
        "sprint": ("LeftThumb", "", ActionType.HOLD, 0.0),
        "crouch": ("B", "", ActionType.HOLD, 0.0),
        "pause": ("Start", "", ActionType.PRESS, 0.0),
        "primary_action": ("RightTrigger", "RightBumper", ActionType.AXIS, 0.1),
        "secondary_action": ("LeftTrigger", "LeftBumper", ActionType.AXIS, 0.1),
    },
    InputDevice.GAMEPAD_PS: {
        "move_horizontal": ("LeftStickX", "DPadX", ActionType.AXIS, 0.2),
        "move_vertical": ("LeftStickY", "DPadY", ActionType.AXIS, 0.2),
        "camera_horizontal": ("RightStickX", "", ActionType.AXIS, 0.2),
        "camera_vertical": ("RightStickY", "", ActionType.AXIS, 0.2),
        "jump": ("Cross", "", ActionType.PRESS, 0.0),
        "interact": ("Square", "", ActionType.PRESS, 0.0),
        "reload": ("Circle", "", ActionType.PRESS, 0.0),
        "sprint": ("L3", "", ActionType.HOLD, 0.0),
        "crouch": ("Circle", "", ActionType.HOLD, 0.0),
        "pause": ("Options", "", ActionType.PRESS, 0.0),
        "primary_action": ("R2", "R1", ActionType.AXIS, 0.1),
        "secondary_action": ("L2", "L1", ActionType.AXIS, 0.1),
    },
    InputDevice.GAMEPAD_SWITCH: {
        "move_horizontal": ("LeftStickX", "DPadX", ActionType.AXIS, 0.2),
        "move_vertical": ("LeftStickY", "DPadY", ActionType.AXIS, 0.2),
        "camera_horizontal": ("RightStickX", "", ActionType.AXIS, 0.2),
        "camera_vertical": ("RightStickY", "", ActionType.AXIS, 0.2),
        "jump": ("B", "", ActionType.PRESS, 0.0),
        "interact": ("Y", "", ActionType.PRESS, 0.0),
        "reload": ("A", "", ActionType.PRESS, 0.0),
        "pause": ("Plus", "", ActionType.PRESS, 0.0),
        "primary_action": ("ZR", "R", ActionType.AXIS, 0.1),
        "secondary_action": ("ZL", "L", ActionType.AXIS, 0.1),
    },
    InputDevice.TOUCHSCREEN: {
        "move": ("Swipe", "", ActionType.GESTURE, 0.0),
        "jump": ("SwipeUp", "", ActionType.GESTURE, 0.0),
        "interact": ("Tap", "", ActionType.PRESS, 0.0),
        "primary_action": ("Tap", "", ActionType.PRESS, 0.0),
        "pause": ("TwoFingerTap", "", ActionType.GESTURE, 0.0),
    },
    InputDevice.ARCADE_STICK: {
        "move_up": ("StickUp", "", ActionType.PRESS, 0.0),
        "move_down": ("StickDown", "", ActionType.PRESS, 0.0),
        "move_left": ("StickLeft", "", ActionType.PRESS, 0.0),
        "move_right": ("StickRight", "", ActionType.PRESS, 0.0),
        "primary_action": ("Button1", "", ActionType.PRESS, 0.0),
        "secondary_action": ("Button2", "", ActionType.PRESS, 0.0),
        "special_1": ("Button3", "", ActionType.PRESS, 0.0),
        "special_2": ("Button4", "", ActionType.PRESS, 0.0),
        "pause": ("Button5", "", ActionType.PRESS, 0.0),
    },
    InputDevice.STEERING_WHEEL: {
        "steering": ("WheelAxis", "", ActionType.AXIS, 0.05),
        "accelerate": ("RightPedal", "", ActionType.AXIS, 0.05),
        "brake": ("LeftPedal", "", ActionType.AXIS, 0.05),
        "clutch": ("ClutchPedal", "", ActionType.AXIS, 0.05),
        "handbrake": ("Button1", "", ActionType.PRESS, 0.0),
        "gear_up": ("PaddleRight", "", ActionType.PRESS, 0.0),
        "gear_down": ("PaddleLeft", "", ActionType.PRESS, 0.0),
        "pause": ("Button2", "", ActionType.PRESS, 0.0),
        "look_behind": ("Button3", "", ActionType.HOLD, 0.0),
    },
    InputDevice.FLIGHT_STICK: {
        "pitch": ("StickY", "", ActionType.AXIS, 0.05),
        "roll": ("StickX", "", ActionType.AXIS, 0.05),
        "yaw": ("Twist", "RudderPedals", ActionType.AXIS, 0.05),
        "throttle": ("ThrottleAxis", "", ActionType.AXIS, 0.05),
        "primary_fire": ("Trigger", "", ActionType.PRESS, 0.0),
        "secondary_fire": ("Button2", "", ActionType.PRESS, 0.0),
        "target_lock": ("Button3", "", ActionType.HOLD, 0.0),
        "pause": ("Button4", "", ActionType.PRESS, 0.0),
    },
    InputDevice.VR_CONTROLLER: {
        "move": ("ThumbstickX", "ThumbstickY", ActionType.AXIS, 0.2),
        "grab": ("Grip", "", ActionType.HOLD, 0.0),
        "interact": ("Trigger", "", ActionType.PRESS, 0.0),
        "primary_action": ("Trigger", "", ActionType.PRESS, 0.0),
        "secondary_action": ("Grip", "", ActionType.HOLD, 0.0),
        "pause": ("MenuButton", "", ActionType.PRESS, 0.0),
        "teleport": ("ThumbstickPress", "", ActionType.PRESS, 0.0),
    },
}


def get_input_profile_system() -> InputProfileSystem:
    return InputProfileSystem.get_instance()