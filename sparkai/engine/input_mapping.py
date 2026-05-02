"""
Input Mapping System - Action-based input with rebindable controls and device abstraction.

Architecture:
    InputMapping/
    |-- InputDevice (keyboard, mouse, gamepad enumeration)
    |-- InputEvent (key press, axis movement, button enumeration)
    |-- ActionBinding (key/button to action mapping dataclass)
    |-- ActionContext (scoped action group dataclass)
    |-- InputMappingSystem (global input orchestration)

Bridges physical input devices to logical game actions for AI-generated games.
Supports multiple profiles, context-sensitive bindings, dead zones, sensitivity
curves, and axis-to-digital conversion for flexible control schemes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class InputDevice(Enum):
    KEYBOARD = auto()
    MOUSE = auto()
    GAMEPAD = auto()
    TOUCH = auto()


class InputEventType(Enum):
    KEY_PRESS = auto()
    KEY_RELEASE = auto()
    MOUSE_BUTTON = auto()
    MOUSE_MOVE = auto()
    MOUSE_WHEEL = auto()
    GAMEPAD_BUTTON = auto()
    GAMEPAD_AXIS = auto()
    TOUCH_TAP = auto()
    TOUCH_SWIPE = auto()


@dataclass
class ActionBinding:
    binding_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_name: str = ""
    device: InputDevice = InputDevice.KEYBOARD
    event_type: InputEventType = InputEventType.KEY_PRESS
    key_code: str = ""
    button_index: int = 0
    axis: str = ""
    axis_direction: float = 0.0
    dead_zone: float = 0.2
    sensitivity: float = 1.0
    inverted: bool = False
    modifiers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "action_name": self.action_name,
            "device": self.device.name,
            "event_type": self.event_type.name,
            "key_code": self.key_code,
            "button_index": self.button_index,
            "axis": self.axis,
            "dead_zone": self.dead_zone,
            "sensitivity": self.sensitivity,
            "inverted": self.inverted,
        }


@dataclass
class ActionContext:
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Default"
    bindings: Dict[str, List[ActionBinding]] = field(default_factory=dict)
    active: bool = True
    priority: int = 0

    def get_bindings(self, action_name: str) -> List[ActionBinding]:
        return self.bindings.get(action_name, [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "name": self.name,
            "active": self.active,
            "priority": self.priority,
            "action_count": len(self.bindings),
            "actions": list(self.bindings.keys()),
        }


class InputMappingSystem:
    _instance: Optional["InputMappingSystem"] = None

    def __init__(self):
        self._contexts: Dict[str, ActionContext] = {}
        self._profiles: Dict[str, Dict[str, List[ActionBinding]]] = {}
        self._action_states: Dict[str, float] = {}
        self._action_just_pressed: Dict[str, bool] = {}
        self._action_just_released: Dict[str, bool] = {}
        self._pending_events: List[Dict[str, Any]] = []
        self._current_profile: str = "default"

        self._create_default_context()

    def _create_default_context(self) -> None:
        ctx = self.create_context("Gameplay", priority=0)

        self._add_binding(ctx, "move_up", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="W")
        self._add_binding(ctx, "move_up", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="ArrowUp")
        self._add_binding(ctx, "move_down", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="S")
        self._add_binding(ctx, "move_down", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="ArrowDown")
        self._add_binding(ctx, "move_left", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="A")
        self._add_binding(ctx, "move_left", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="ArrowLeft")
        self._add_binding(ctx, "move_right", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="D")
        self._add_binding(ctx, "move_right", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="ArrowRight")
        self._add_binding(ctx, "jump", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="Space")
        self._add_binding(ctx, "interact", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="E")
        self._add_binding(ctx, "pause", InputDevice.KEYBOARD, InputEventType.KEY_PRESS, key_code="Escape")
        self._add_binding(ctx, "primary_action", InputDevice.MOUSE, InputEventType.MOUSE_BUTTON, button_index=0)
        self._add_binding(ctx, "secondary_action", InputDevice.MOUSE, InputEventType.MOUSE_BUTTON, button_index=1)

    def _add_binding(self, ctx: ActionContext, action_name: str, device: InputDevice,
                     event_type: InputEventType, key_code: str = "", button_index: int = 0) -> None:
        binding = ActionBinding(
            action_name=action_name,
            device=device,
            event_type=event_type,
            key_code=key_code,
            button_index=button_index,
        )
        if action_name not in ctx.bindings:
            ctx.bindings[action_name] = []
        ctx.bindings[action_name].append(binding)

    @classmethod
    def get_instance(cls) -> "InputMappingSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_context(self, name: str = "Context", priority: int = 0) -> ActionContext:
        ctx = ActionContext(name=name, priority=priority)
        self._contexts[ctx.context_id] = ctx
        return ctx

    def get_context(self, context_id: str) -> Optional[ActionContext]:
        return self._contexts.get(context_id)

    def remove_context(self, context_id: str) -> bool:
        if context_id in self._contexts:
            del self._contexts[context_id]
            return True
        return False

    def set_context_active(self, context_id: str, active: bool) -> bool:
        ctx = self._contexts.get(context_id)
        if ctx:
            ctx.active = active
            return True
        return False

    def bind_action(self, context_id: str, binding: ActionBinding) -> bool:
        ctx = self._contexts.get(context_id)
        if not ctx:
            return False
        if binding.action_name not in ctx.bindings:
            ctx.bindings[binding.action_name] = []
        ctx.bindings[binding.action_name].append(binding)
        return True

    def unbind_action(self, context_id: str, binding_id: str) -> bool:
        ctx = self._contexts.get(context_id)
        if not ctx:
            return False
        for action_name, bindings in ctx.bindings.items():
            ctx.bindings[action_name] = [b for b in bindings if b.binding_id != binding_id]
        return True

    def create_profile(self, profile_name: str) -> bool:
        if profile_name in self._profiles:
            return False
        self._profiles[profile_name] = {}
        return True

    def set_profile(self, profile_name: str) -> bool:
        if profile_name in self._profiles or profile_name == "default":
            self._current_profile = profile_name
            return True
        return False

    def get_action_value(self, action_name: str) -> float:
        return self._action_states.get(action_name, 0.0)

    def is_action_pressed(self, action_name: str) -> bool:
        return self._action_states.get(action_name, 0.0) > 0.5

    def is_action_just_pressed(self, action_name: str) -> bool:
        return self._action_just_pressed.get(action_name, False)

    def is_action_just_released(self, action_name: str) -> bool:
        return self._action_just_released.get(action_name, False)

    def process_event(self, event: Dict[str, Any]) -> None:
        self._pending_events.append(event)

    def update(self, dt: float) -> None:
        self._action_just_pressed.clear()
        self._action_just_released.clear()

        active_contexts = sorted(
            [c for c in self._contexts.values() if c.active],
            key=lambda c: c.priority,
        )

        for event in self._pending_events:
            for ctx in active_contexts:
                for action_name, bindings in ctx.bindings.items():
                    for binding in bindings:
                        if self._event_matches(event, binding):
                            prev = self._action_states.get(action_name, 0.0)
                            value = self._compute_value(event, binding)
                            self._action_states[action_name] = value
                            if value > 0.5 and prev <= 0.5:
                                self._action_just_pressed[action_name] = True
                            elif value <= 0.5 and prev > 0.5:
                                self._action_just_released[action_name] = True
                            break

        self._pending_events.clear()

    def _event_matches(self, event: Dict[str, Any], binding: ActionBinding) -> bool:
        if event.get("device") != binding.device.name.lower():
            return False
        if binding.device == InputDevice.KEYBOARD:
            return (event.get("key", "").lower() == binding.key_code.lower() and
                    event.get("type") == binding.event_type.name.lower())
        elif binding.device == InputDevice.MOUSE:
            return (event.get("button", -1) == binding.button_index and
                    event.get("type") == binding.event_type.name.lower())
        elif binding.device == InputDevice.GAMEPAD:
            return (event.get("button", -1) == binding.button_index and
                    event.get("type") == binding.event_type.name.lower())
        return False

    def _compute_value(self, event: Dict[str, Any], binding: ActionBinding) -> float:
        value = event.get("value", 1.0)
        if abs(value) < binding.dead_zone:
            return 0.0
        value *= binding.sensitivity
        if binding.inverted:
            value *= -1.0
        return min(1.0, max(-1.0, value))

    def list_contexts(self) -> List[ActionContext]:
        return list(self._contexts.values())

    def list_bindings(self, context_id: Optional[str] = None) -> List[ActionBinding]:
        if context_id:
            ctx = self._contexts.get(context_id)
            if ctx:
                return [b for blist in ctx.bindings.values() for b in blist]
            return []
        all_bindings = []
        for ctx in self._contexts.values():
            for blist in ctx.bindings.values():
                all_bindings.extend(blist)
        return all_bindings

    def get_stats(self) -> Dict[str, Any]:
        total_bindings = sum(
            len(blist) for ctx in self._contexts.values()
            for blist in ctx.bindings.values()
        )
        return {
            "context_count": len(self._contexts),
            "profile_count": len(self._profiles) + 1,
            "current_profile": self._current_profile,
            "total_bindings": total_bindings,
            "active_contexts": sum(1 for c in self._contexts.values() if c.active),
            "active_actions": len([k for k, v in self._action_states.items() if v > 0.5]),
        }


def get_input_mapping() -> InputMappingSystem:
    return InputMappingSystem.get_instance()
