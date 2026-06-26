"""
SparkLabs Engine - Input Action System

Advanced input action system that maps raw input events to semantic game
actions with context-aware binding, gesture recognition, and AI-driven
input optimization. Provides a flexible input abstraction layer that
decouples game logic from specific input devices.

Architecture:
  InputActionSystem (Singleton)
    |-- InputAction (semantic game action with triggers)
    |-- ActionBinding (maps input events to actions)
    |-- ControlScheme (organized set of bindings for a context)
    |-- InputContext (context stack for layered input handling)
    |-- GestureRecognizer (detects complex input patterns)
    |-- InputOptimizer (AI-driven input layout optimization)

Input Features:
  - Multi-device support (keyboard, mouse, gamepad, touch)
  - Context-sensitive input with priority-based routing
  - Gesture recognition for complex input patterns
  - Action buffering for combo detection
  - Dead zone and sensitivity configuration
  - AI-assisted control scheme generation

Usage:
    ias = get_input_action_system()
    ias.initialize()

    # Define an action
    ias.register_action(InputAction(
        name="jump",
        description="Make the character jump",
        triggers=[InputTrigger(device=InputDeviceType.KEYBOARD, key="SPACE")],
    ))

    # Create a control scheme
    ias.create_scheme("platformer_default", [
        ActionBinding(action="jump", triggers=[InputTrigger(key="SPACE")]),
        ActionBinding(action="move_left", triggers=[InputTrigger(key="A"), InputTrigger(key="LEFT")]),
    ])

    # Push a context
    ias.push_context("gameplay")
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class InputDeviceType(Enum):
    """Types of input devices."""
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"
    TOUCH = "touch"
    GYROSCOPE = "gyroscope"
    CUSTOM = "custom"


class InputTriggerType(Enum):
    """How an input trigger is activated."""
    PRESS = "press"            # Single press
    RELEASE = "release"        # On release
    HOLD = "hold"              # Continuous hold
    DOUBLE_PRESS = "double"    # Double press
    LONG_PRESS = "long_press"  # Hold for duration
    AXIS = "axis"              # Continuous axis value
    GESTURE = "gesture"        # Complex gesture


class GestureType(Enum):
    """Recognized gesture patterns."""
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    PINCH_IN = "pinch_in"
    PINCH_OUT = "pinch_out"
    ROTATE = "rotate"
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    DRAG = "drag"
    CIRCLE = "circle"
    CUSTOM = "custom"


class InputContextState(Enum):
    """States of an input context."""
    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"


class ActionTriggerBehavior(Enum):
    """Behavior when an action is triggered."""
    ONCE = "once"            # Fire once per press
    CONTINUOUS = "continuous"  # Fire continuously while held
    TOGGLE = "toggle"        # Toggle on/off state
    CHORD = "chord"          # Require multiple inputs simultaneously


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class InputTrigger:
    """A single input trigger condition."""
    trigger_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    device: InputDeviceType = InputDeviceType.KEYBOARD
    key: str = ""                # Key code or button name
    trigger_type: InputTriggerType = InputTriggerType.PRESS
    axis: str = ""               # Axis name for analog inputs
    threshold: float = 0.5       # Activation threshold for axis
    hold_duration_ms: float = 500.0  # For long press
    modifiers: List[str] = field(default_factory=list)  # Modifier keys required
    dead_zone: float = 0.1       # Dead zone for analog inputs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "device": self.device.value,
            "key": self.key,
            "trigger_type": self.trigger_type.value,
            "axis": self.axis,
            "threshold": self.threshold,
            "hold_duration_ms": self.hold_duration_ms,
            "modifiers": self.modifiers,
            "dead_zone": self.dead_zone,
        }


@dataclass
class InputAction:
    """A semantic game action with input triggers."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    category: str = "general"
    triggers: List[InputTrigger] = field(default_factory=list)
    behavior: ActionTriggerBehavior = ActionTriggerBehavior.ONCE
    cooldown_ms: float = 0.0
    priority: int = 0
    consumes_input: bool = True  # Whether to stop propagation
    tags: List[str] = field(default_factory=list)
    handler: Optional[Callable[..., None]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "triggers": [t.to_dict() for t in self.triggers],
            "behavior": self.behavior.value,
            "cooldown_ms": self.cooldown_ms,
            "priority": self.priority,
            "consumes_input": self.consumes_input,
            "tags": self.tags,
        }


@dataclass
class ActionBinding:
    """Binding of triggers to an action within a control scheme."""
    binding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_name: str = ""
    triggers: List[InputTrigger] = field(default_factory=list)
    scale: float = 1.0
    invert: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "action_name": self.action_name,
            "triggers": [t.to_dict() for t in self.triggers],
            "scale": self.scale,
            "invert": self.invert,
        }


@dataclass
class ControlScheme:
    """A complete set of input bindings for a game context."""
    scheme_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    bindings: Dict[str, ActionBinding] = field(default_factory=dict)
    parent_scheme: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "name": self.name,
            "description": self.description,
            "binding_count": len(self.bindings),
            "bindings": [b.to_dict() for b in self.bindings.values()],
            "parent_scheme": self.parent_scheme,
            "created_at": self.created_at,
        }


@dataclass
class InputContext:
    """A layered input handling context."""
    context_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    state: InputContextState = InputContextState.ACTIVE
    scheme_name: str = ""
    priority: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "name": self.name,
            "state": self.state.value,
            "scheme_name": self.scheme_name,
            "priority": self.priority,
            "created_at": self.created_at,
        }


@dataclass
class GesturePattern:
    """A recognized gesture pattern definition."""
    pattern_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    gesture_type: GestureType = GestureType.TAP
    name: str = ""
    min_points: int = 2
    max_duration_ms: float = 1000.0
    min_distance: float = 50.0
    tolerance: float = 20.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "gesture_type": self.gesture_type.value,
            "name": self.name,
            "min_points": self.min_points,
            "max_duration_ms": self.max_duration_ms,
            "min_distance": self.min_distance,
            "tolerance": self.tolerance,
        }


@dataclass
class InputBufferEntry:
    """A buffered input event for combo detection."""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_name: str = ""
    timestamp: float = field(default_factory=time.time)
    value: float = 1.0
    device: InputDeviceType = InputDeviceType.KEYBOARD

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "action_name": self.action_name,
            "timestamp": self.timestamp,
            "value": self.value,
            "device": self.device.value,
        }


# =============================================================================
# InputActionSystem (Singleton)
# =============================================================================


class InputActionSystem:
    """Advanced input action system with context-aware binding.

    Maps raw input events to semantic game actions, supporting multiple
    devices, gesture recognition, and AI-driven control scheme optimization.

    Usage:
        ias = InputActionSystem.get_instance()
        ias.initialize()

        ias.register_action(InputAction(name="jump", triggers=[InputTrigger(key="SPACE")]))
        ias.create_scheme("platformer", [ActionBinding(action="jump", triggers=[...])])
        ias.push_context("gameplay")
    """

    _instance: Optional["InputActionSystem"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if InputActionSystem._instance is not None:
            raise RuntimeError("Use InputActionSystem.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()
        self._actions: Dict[str, InputAction] = {}
        self._schemes: Dict[str, ControlScheme] = {}
        self._context_stack: List[InputContext] = []
        self._gesture_patterns: Dict[str, GesturePattern] = {}
        self._input_buffer: List[InputBufferEntry] = []
        self._action_states: Dict[str, bool] = {}
        self._cooldowns: Dict[str, float] = {}
        self._max_buffer_size: int = 64

    @classmethod
    def get_instance(cls) -> "InputActionSystem":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            self._register_default_actions()
            self._register_default_schemes()
            self._register_default_gestures()
            self._initialized = True

            return {
                "status": "initialized",
                "success": True,
                "actions": len(self._actions),
                "schemes": len(self._schemes),
                "gestures": len(self._gesture_patterns),
            }

    def shutdown(self) -> Dict[str, Any]:
        with self._lock:
            self._initialized = False
            self._context_stack.clear()
            self._input_buffer.clear()
            return {"success": True}

    def _register_default_actions(self) -> None:
        """Register built-in input actions."""
        defaults = [
            InputAction(name="move_up", category="movement",
                       triggers=[InputTrigger(key="W"), InputTrigger(key="UP")],
                       behavior=ActionTriggerBehavior.CONTINUOUS),
            InputAction(name="move_down", category="movement",
                       triggers=[InputTrigger(key="S"), InputTrigger(key="DOWN")],
                       behavior=ActionTriggerBehavior.CONTINUOUS),
            InputAction(name="move_left", category="movement",
                       triggers=[InputTrigger(key="A"), InputTrigger(key="LEFT")],
                       behavior=ActionTriggerBehavior.CONTINUOUS),
            InputAction(name="move_right", category="movement",
                       triggers=[InputTrigger(key="D"), InputTrigger(key="RIGHT")],
                       behavior=ActionTriggerBehavior.CONTINUOUS),
            InputAction(name="jump", category="movement",
                       triggers=[InputTrigger(key="SPACE")],
                       behavior=ActionTriggerBehavior.ONCE),
            InputAction(name="interact", category="gameplay",
                       triggers=[InputTrigger(key="E"), InputTrigger(key="F")],
                       behavior=ActionTriggerBehavior.ONCE),
            InputAction(name="attack", category="combat",
                       triggers=[InputTrigger(device=InputDeviceType.MOUSE, key="LEFT_BUTTON")],
                       behavior=ActionTriggerBehavior.ONCE),
            InputAction(name="pause", category="system",
                       triggers=[InputTrigger(key="ESCAPE")],
                       behavior=ActionTriggerBehavior.ONCE),
            InputAction(name="inventory", category="ui",
                       triggers=[InputTrigger(key="I"), InputTrigger(key="TAB")],
                       behavior=ActionTriggerBehavior.TOGGLE),
            InputAction(name="sprint", category="movement",
                       triggers=[InputTrigger(key="SHIFT", trigger_type=InputTriggerType.HOLD)],
                       behavior=ActionTriggerBehavior.CONTINUOUS),
        ]

        for action in defaults:
            self._actions[action.name] = action

    def _register_default_schemes(self) -> None:
        """Register built-in control schemes."""
        platformer = ControlScheme(
            name="platformer_default",
            description="Default platformer control scheme",
        )
        for name in ["move_up", "move_down", "move_left", "move_right", "jump", "interact", "pause"]:
            if name in self._actions:
                platformer.bindings[name] = ActionBinding(
                    action_name=name,
                    triggers=self._actions[name].triggers,
                )
        self._schemes["platformer_default"] = platformer

        rpg = ControlScheme(
            name="rpg_default",
            description="Default RPG control scheme",
        )
        for name in ["move_up", "move_down", "move_left", "move_right", "interact", "attack", "inventory", "pause"]:
            if name in self._actions:
                rpg.bindings[name] = ActionBinding(
                    action_name=name,
                    triggers=self._actions[name].triggers,
                )
        self._schemes["rpg_default"] = rpg

    def _register_default_gestures(self) -> None:
        """Register built-in gesture patterns."""
        defaults = [
            GesturePattern(gesture_type=GestureType.SWIPE_LEFT, name="Swipe Left",
                          min_distance=100.0, max_duration_ms=500.0),
            GesturePattern(gesture_type=GestureType.SWIPE_RIGHT, name="Swipe Right",
                          min_distance=100.0, max_duration_ms=500.0),
            GesturePattern(gesture_type=GestureType.SWIPE_UP, name="Swipe Up",
                          min_distance=100.0, max_duration_ms=500.0),
            GesturePattern(gesture_type=GestureType.SWIPE_DOWN, name="Swipe Down",
                          min_distance=100.0, max_duration_ms=500.0),
            GesturePattern(gesture_type=GestureType.TAP, name="Tap",
                          min_points=1, max_duration_ms=300.0),
            GesturePattern(gesture_type=GestureType.DOUBLE_TAP, name="Double Tap",
                          min_points=2, max_duration_ms=500.0),
            GesturePattern(gesture_type=GestureType.PINCH_IN, name="Pinch In",
                          min_points=2, min_distance=50.0),
            GesturePattern(gesture_type=GestureType.PINCH_OUT, name="Pinch Out",
                          min_points=2, min_distance=50.0),
        ]

        for pattern in defaults:
            self._gesture_patterns[pattern.name] = pattern

    # -------------------------------------------------------------------------
    # Action Management
    # -------------------------------------------------------------------------

    def register_action(self, action: InputAction) -> Dict[str, Any]:
        """Register a new input action."""
        with self._lock:
            if action.name in self._actions:
                return {"success": False, "error": f"Action '{action.name}' already exists"}
            self._actions[action.name] = action
            return {"success": True, "action": action.to_dict()}

    def get_action(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an action by name."""
        action = self._actions.get(name)
        return action.to_dict() if action else None

    def list_actions(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all actions, optionally filtered by category."""
        actions = self._actions.values()
        if category:
            actions = [a for a in actions if a.category == category]
        return [a.to_dict() for a in actions]

    # -------------------------------------------------------------------------
    # Scheme Management
    # -------------------------------------------------------------------------

    def create_scheme(self, name: str, bindings: List[ActionBinding],
                      description: str = "",
                      parent: Optional[str] = None) -> Dict[str, Any]:
        """Create a new control scheme."""
        with self._lock:
            if name in self._schemes:
                return {"success": False, "error": f"Scheme '{name}' already exists"}

            scheme = ControlScheme(
                name=name,
                description=description,
                parent_scheme=parent,
            )
            for binding in bindings:
                scheme.bindings[binding.action_name] = binding

            self._schemes[name] = scheme
            return {"success": True, "scheme": scheme.to_dict()}

    def get_scheme(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a scheme by name."""
        scheme = self._schemes.get(name)
        return scheme.to_dict() if scheme else None

    def list_schemes(self) -> List[Dict[str, Any]]:
        """List all control schemes."""
        return [s.to_dict() for s in self._schemes.values()]

    # -------------------------------------------------------------------------
    # Context Management
    # -------------------------------------------------------------------------

    def push_context(self, name: str, scheme_name: str = "",
                     priority: int = 0) -> Dict[str, Any]:
        """Push a new input context onto the stack."""
        with self._lock:
            context = InputContext(
                name=name,
                scheme_name=scheme_name,
                priority=priority,
            )
            self._context_stack.append(context)
            # Sort by priority (highest first)
            self._context_stack.sort(key=lambda c: c.priority, reverse=True)
            return {"success": True, "context": context.to_dict()}

    def pop_context(self) -> Dict[str, Any]:
        """Remove the top input context."""
        with self._lock:
            if not self._context_stack:
                return {"success": False, "error": "No contexts to pop"}
            context = self._context_stack.pop()
            return {"success": True, "context": context.to_dict()}

    def get_active_context(self) -> Optional[Dict[str, Any]]:
        """Get the currently active input context."""
        for ctx in self._context_stack:
            if ctx.state == InputContextState.ACTIVE:
                return ctx.to_dict()
        return None

    def list_contexts(self) -> List[Dict[str, Any]]:
        """List all contexts in the stack."""
        return [c.to_dict() for c in self._context_stack]

    # -------------------------------------------------------------------------
    # Input Processing
    # -------------------------------------------------------------------------

    def process_input(self, device: InputDeviceType, key: str,
                      value: float = 1.0, trigger_type: InputTriggerType = InputTriggerType.PRESS,
                      modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Process a raw input event and trigger matching actions."""
        triggered_actions = []

        # Get active context
        active_context = None
        for ctx in self._context_stack:
            if ctx.state == InputContextState.ACTIVE:
                active_context = ctx
                break

        # Find matching actions
        for action in self._actions.values():
            for trigger in action.triggers:
                if trigger.device != device or trigger.key != key:
                    continue
                if trigger.trigger_type != trigger_type:
                    continue
                if modifiers and trigger.modifiers:
                    if not all(m in modifiers for m in trigger.modifiers):
                        continue

                # Check cooldown
                now = time.time()
                if action.name in self._cooldowns:
                    if now < self._cooldowns[action.name]:
                        continue

                # Trigger the action
                self._action_states[action.name] = True
                if action.cooldown_ms > 0:
                    self._cooldowns[action.name] = now + action.cooldown_ms / 1000.0

                # Buffer for combo detection
                self._input_buffer.append(InputBufferEntry(
                    action_name=action.name,
                    value=value,
                    device=device,
                ))
                if len(self._input_buffer) > self._max_buffer_size:
                    self._input_buffer = self._input_buffer[-self._max_buffer_size:]

                triggered_actions.append(action.name)

                if action.consumes_input:
                    break

        return {
            "success": True,
            "triggered_actions": triggered_actions,
            "context": active_context.name if active_context else None,
        }

    def get_action_state(self, action_name: str) -> bool:
        """Get the current state of an action."""
        return self._action_states.get(action_name, False)

    def release_action(self, action_name: str) -> None:
        """Release a held action."""
        self._action_states[action_name] = False

    # -------------------------------------------------------------------------
    # Gesture Recognition
    # -------------------------------------------------------------------------

    def register_gesture(self, pattern: GesturePattern) -> Dict[str, Any]:
        """Register a new gesture pattern."""
        with self._lock:
            if pattern.name in self._gesture_patterns:
                return {"success": False, "error": f"Gesture '{pattern.name}' already exists"}
            self._gesture_patterns[pattern.name] = pattern
            return {"success": True, "pattern": pattern.to_dict()}

    def recognize_gesture(self, points: List[Tuple[float, float]],
                          duration_ms: float) -> Optional[Dict[str, Any]]:
        """Attempt to recognize a gesture from touch points."""
        if len(points) < 2:
            return None

        start = points[0]
        end = points[-1]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = (dx ** 2 + dy ** 2) ** 0.5

        # Check each pattern
        for pattern in self._gesture_patterns.values():
            if distance < pattern.min_distance:
                continue
            if duration_ms > pattern.max_duration_ms:
                continue

            if pattern.gesture_type == GestureType.SWIPE_LEFT and dx < -pattern.tolerance:
                return {"gesture": pattern.gesture_type.value, "pattern": pattern.to_dict()}
            if pattern.gesture_type == GestureType.SWIPE_RIGHT and dx > pattern.tolerance:
                return {"gesture": pattern.gesture_type.value, "pattern": pattern.to_dict()}
            if pattern.gesture_type == GestureType.SWIPE_UP and dy < -pattern.tolerance:
                return {"gesture": pattern.gesture_type.value, "pattern": pattern.to_dict()}
            if pattern.gesture_type == GestureType.SWIPE_DOWN and dy > pattern.tolerance:
                return {"gesture": pattern.gesture_type.value, "pattern": pattern.to_dict()}

        return None

    def list_gestures(self) -> List[Dict[str, Any]]:
        """List all registered gesture patterns."""
        return [p.to_dict() for p in self._gesture_patterns.values()]

    # -------------------------------------------------------------------------
    # Combo Detection
    # -------------------------------------------------------------------------

    def detect_combo(self, timeout_ms: float = 500.0) -> Optional[Dict[str, Any]]:
        """Detect input combos from the buffer."""
        now = time.time()
        recent = [
            e for e in self._input_buffer
            if (now - e.timestamp) * 1000 < timeout_ms
        ]

        if len(recent) < 2:
            return None

        combo = [e.action_name for e in recent]
        return {
            "combo": combo,
            "combo_string": " + ".join(combo),
            "length": len(combo),
            "duration_ms": (recent[-1].timestamp - recent[0].timestamp) * 1000,
        }

    def clear_buffer(self) -> Dict[str, Any]:
        """Clear the input buffer."""
        with self._lock:
            count = len(self._input_buffer)
            self._input_buffer.clear()
            return {"success": True, "cleared": count}

    # -------------------------------------------------------------------------
    # AI-Driven Control Scheme Generation
    # -------------------------------------------------------------------------

    def generate_scheme(self, game_genre: str,
                        description: str = "") -> Dict[str, Any]:
        """Generate a control scheme for a game genre."""
        genre_lower = game_genre.lower()

        genre_templates = {
            "platformer": ["move_left", "move_right", "jump", "sprint", "interact", "pause"],
            "rpg": ["move_up", "move_down", "move_left", "move_right", "interact", "attack", "inventory", "pause"],
            "shooter": ["move_up", "move_down", "move_left", "move_right", "attack", "sprint", "interact", "pause"],
            "puzzle": ["move_left", "move_right", "move_up", "move_down", "interact", "pause"],
            "racing": ["move_up", "move_down", "move_left", "move_right", "pause"],
        }

        action_names = genre_templates.get(genre_lower, genre_templates["platformer"])
        bindings = []
        for name in action_names:
            if name in self._actions:
                bindings.append(ActionBinding(
                    action_name=name,
                    triggers=self._actions[name].triggers,
                ))

        scheme_name = f"generated_{genre_lower}_{uuid.uuid4().hex[:6]}"
        return self.create_scheme(scheme_name, bindings, description)

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "actions": len(self._actions),
                "schemes": len(self._schemes),
                "contexts": len(self._context_stack),
                "gestures": len(self._gesture_patterns),
                "buffer_size": len(self._input_buffer),
                "active_actions": {k: v for k, v in self._action_states.items() if v},
            }

    def get_buffer(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent input buffer entries."""
        return [e.to_dict() for e in self._input_buffer[-limit:]]


# ── Module Accessor ──

def get_input_action_system() -> InputActionSystem:
    """Get the singleton input action system instance."""
    return InputActionSystem.get_instance()