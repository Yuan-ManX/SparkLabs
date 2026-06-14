"""
SparkLabs Engine - Object Behavior System

An attachable behavior system for game objects that allows modular
reusable components to be composed into rich interactive entities.
Each behavior is a self-contained unit with its own lifecycle hooks,
typed parameters, and event-driven communication.

Architecture:
  EngineObjectBehavior (Singleton)
    |-- BehaviorTemplate     — registered blueprint with parameter schema
    |-- BehaviorParameter    — typed parameter definition with validation
    |-- BehaviorInstance     — runtime instance attached to a game object
    |-- BehaviorEvent        — intra-object event message
    |-- BehaviorBinding      — group binding tying behaviors to an object

Features:
  - Behavior Registry with template registration and lookup
  - Full lifecycle: on_attach, on_init, on_update, on_event, on_detach
  - Typed parameters (float, int, string, bool, enum, color, vector2, object_ref)
  - Event emission and listening between behaviors on the same object
  - Priority-based execution ordering
  - Built-in behavior templates for common game patterns
  - Behavior composition through events and shared state

Usage:
    ob = get_engine_object_behavior()
    ob.register_builtin_templates()
    instance = ob.attach_behavior("player_1", "platformer_controller",
        {"move_speed": 300.0, "jump_force": 600.0})
    ob.emit_behavior_event(instance.instance_id, "on_damage", {"amount": 10})
"""

from __future__ import annotations

import json
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BehaviorState(str, Enum):
    """Lifecycle states for a behavior instance attached to an object."""
    ATTACHED = "attached"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"
    DETACHED = "detached"


class ParameterType(str, Enum):
    """Supported data types for behavior parameters."""
    FLOAT = "float"
    INT = "int"
    STRING = "string"
    BOOL = "bool"
    ENUM = "enum"
    COLOR = "color"
    VECTOR2 = "vector2"
    OBJECT_REF = "object_ref"
    FILE_PATH = "file_path"
    AUDIO_CLIP = "audio_clip"


class BehaviorCategory(str, Enum):
    """Category classification for behavior templates."""
    MOVEMENT = "movement"
    PHYSICS = "physics"
    RENDERING = "rendering"
    AI = "ai"
    COMBAT = "combat"
    UI = "ui"
    AUDIO = "audio"
    UTILITY = "utility"
    GAMEPLAY = "gameplay"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BehaviorParameter:
    """Typed parameter definition for a behavior template.

    Defines the name, type, default value, validation constraints, and
    optional enumeration options for a configurable behavior parameter.
    """

    param_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    param_type: ParameterType = ParameterType.FLOAT
    default_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: List[str] = field(default_factory=list)
    description: str = ""
    required: bool = False

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a proposed value against this parameter's constraints.

        Args:
            value: The value to validate.

        Returns:
            Tuple of (is_valid, error_message_or_none).
        """
        if value is None:
            if self.required:
                return (False, f"Parameter '{self.name}' is required")
            return (True, None)

        if self.param_type == ParameterType.FLOAT:
            if not isinstance(value, (int, float)):
                return (False, f"Expected float, got {type(value).__name__}")
            v = float(value)
            if self.min_value is not None and v < self.min_value:
                return (False, f"Value {v} below minimum {self.min_value}")
            if self.max_value is not None and v > self.max_value:
                return (False, f"Value {v} above maximum {self.max_value}")
            return (True, None)

        elif self.param_type == ParameterType.INT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return (False, f"Expected int, got {type(value).__name__}")
            v = int(value)
            if self.min_value is not None and v < self.min_value:
                return (False, f"Value {v} below minimum {int(self.min_value)}")
            if self.max_value is not None and v > self.max_value:
                return (False, f"Value {v} above maximum {int(self.max_value)}")
            return (True, None)

        elif self.param_type == ParameterType.STRING:
            if not isinstance(value, str):
                return (False, f"Expected string, got {type(value).__name__}")
            if self.min_value is not None and len(value) < self.min_value:
                return (False, f"String too short (min {int(self.min_value)})")
            if self.max_value is not None and len(value) > self.max_value:
                return (False, f"String too long (max {int(self.max_value)})")
            return (True, None)

        elif self.param_type == ParameterType.BOOL:
            if not isinstance(value, bool):
                return (False, f"Expected bool, got {type(value).__name__}")
            return (True, None)

        elif self.param_type == ParameterType.ENUM:
            if not isinstance(value, str):
                return (False, f"Expected string enum value, got {type(value).__name__}")
            if self.options and value not in self.options:
                return (False, f"Value '{value}' not in options: {self.options}")
            return (True, None)

        elif self.param_type == ParameterType.COLOR:
            if not isinstance(value, (list, tuple)) or len(value) not in (3, 4):
                return (False, "Color must be [r, g, b] or [r, g, b, a]")
            for c in value:
                if not isinstance(c, (int, float)) or c < 0 or c > 255:
                    return (False, f"Color component {c} out of range 0-255")
            return (True, None)

        elif self.param_type == ParameterType.VECTOR2:
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                return (False, "Vector2 must be [x, y]")
            return (True, None)

        elif self.param_type in (ParameterType.OBJECT_REF, ParameterType.FILE_PATH, ParameterType.AUDIO_CLIP):
            if not isinstance(value, str):
                return (False, f"Expected string reference, got {type(value).__name__}")
            return (True, None)

        return (True, None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_id": self.param_id,
            "name": self.name,
            "param_type": self.param_type.value,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "options": list(self.options),
            "description": self.description,
            "required": self.required,
        }


@dataclass
class BehaviorTemplate:
    """Registered blueprint for a behavior type.

    Describes the behavior's metadata, category, configurable parameters,
    default priority, and tags for UI discovery and filtering.
    """

    template_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: BehaviorCategory = BehaviorCategory.CUSTOM
    parameters: List[BehaviorParameter] = field(default_factory=list)
    default_priority: int = 0
    icon: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: _time_module.time())

    def get_parameter(self, name: str) -> Optional[BehaviorParameter]:
        """Look up a parameter definition by name."""
        for p in self.parameters:
            if p.name == name:
                return p
        return None

    def get_default_parameters(self) -> Dict[str, Any]:
        """Return a dict of parameter name -> default value."""
        return {p.name: p.default_value for p in self.parameters}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "default_priority": self.default_priority,
            "icon": self.icon,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


@dataclass
class BehaviorEvent:
    """Event emitted by a behavior and broadcast to sibling behaviors on the same object."""

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_behavior_id: str = ""
    event_type: str = ""
    event_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: _time_module.time())
    consumed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source_behavior_id": self.source_behavior_id,
            "event_type": self.event_type,
            "event_data": dict(self.event_data),
            "timestamp": self.timestamp,
            "consumed": self.consumed,
        }


@dataclass
class BehaviorInstance:
    """Runtime instance of a behavior attached to a specific game object.

    Tracks the current parameter overrides, lifecycle state, execution
    ordering via priority, and hook callback registrations.
    """

    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    template_id: str = ""
    object_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    state: BehaviorState = BehaviorState.ATTACHED
    attached_at: float = field(default_factory=lambda: _time_module.time())
    last_update: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Lifecycle hook registrations (callable(instance, *args))
    _on_attach: Optional[Callable[..., None]] = field(default=None, repr=False)
    _on_init: Optional[Callable[..., None]] = field(default=None, repr=False)
    _on_update: Optional[Callable[..., None]] = field(default=None, repr=False)
    _on_event: Optional[Callable[..., None]] = field(default=None, repr=False)
    _on_detach: Optional[Callable[..., None]] = field(default=None, repr=False)

    def set_hook(self, hook_name: str, callback: Callable[..., None]) -> None:
        """Register a lifecycle hook callback.

        Args:
            hook_name: One of 'on_attach', 'on_init', 'on_update', 'on_event', 'on_detach'.
            callback: A callable accepting (instance, *args).
        """
        valid_hooks = {"on_attach", "on_init", "on_update", "on_event", "on_detach"}
        if hook_name not in valid_hooks:
            raise ValueError(f"Invalid hook name '{hook_name}'. Must be one of {valid_hooks}")
        setattr(self, f"_{hook_name}", callback)

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get the current value of a parameter.

        Args:
            name: Parameter name.
            default: Fallback value if parameter is not set.

        Returns:
            The parameter value or default.
        """
        return self.parameters.get(name, default)

    def set_parameter(self, name: str, value: Any) -> None:
        """Set a parameter value at runtime.

        Args:
            name: Parameter name.
            value: New value to assign.
        """
        self.parameters[name] = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "template_id": self.template_id,
            "object_id": self.object_id,
            "parameters": dict(self.parameters),
            "priority": self.priority,
            "enabled": self.enabled,
            "state": self.state.value,
            "attached_at": self.attached_at,
            "last_update": self.last_update,
            "metadata": dict(self.metadata),
        }


@dataclass
class BehaviorBinding:
    """Group binding that associates a collection of behavior instances with a game object."""

    binding_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    object_id: str = ""
    behavior_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "object_id": self.object_id,
            "behavior_ids": list(self.behavior_ids),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# EngineObjectBehavior — Thread-Safe Singleton
# ---------------------------------------------------------------------------

class EngineObjectBehavior:
    """Attachable behavior system for composing game object functionality.

    Manages a registry of behavior templates, creates and tracks behavior
    instances attached to game objects, dispatches lifecycle hooks, and
    routes intra-object events between behaviors.

    Usage:
        ob = get_engine_object_behavior()
        ob.register_builtin_templates()
        instance = ob.attach_behavior("player_1", "health", {"max_health": 100})
    """

    _instance: Optional["EngineObjectBehavior"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineObjectBehavior":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineObjectBehavior":
        """Return the singleton EngineObjectBehavior instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._templates: Dict[str, BehaviorTemplate] = {}
        self._instances: Dict[str, BehaviorInstance] = {}
        self._bindings: Dict[str, BehaviorBinding] = {}
        self._object_index: Dict[str, List[str]] = {}  # object_id -> [instance_id, ...]

        self._total_attached: int = 0
        self._total_detached: int = 0
        self._builtin_registered: bool = False

    # ------------------------------------------------------------------
    # Template Registry
    # ------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        description: str = "",
        category: BehaviorCategory = BehaviorCategory.CUSTOM,
        parameters: Optional[List[BehaviorParameter]] = None,
        default_priority: int = 0,
        icon: str = "",
        tags: Optional[List[str]] = None,
    ) -> BehaviorTemplate:
        """Register a new behavior template in the registry.

        Args:
            name: Unique name for the template.
            description: Human-readable description of the behavior.
            category: Category classification (MOVEMENT, PHYSICS, etc.).
            parameters: List of BehaviorParameter definitions.
            default_priority: Default execution priority (lower runs first).
            icon: Optional icon identifier for UI display.
            tags: Optional tags for filtering and discovery.

        Returns:
            The created BehaviorTemplate.

        Raises:
            ValueError: If a template with the same name already exists.
        """
        with self._lock:
            # Check for name collision
            for t in self._templates.values():
                if t.name == name:
                    raise ValueError(f"Template '{name}' already registered")

            template = BehaviorTemplate(
                name=name,
                description=description,
                category=category,
                parameters=list(parameters) if parameters else [],
                default_priority=default_priority,
                icon=icon,
                tags=list(tags) if tags else [],
            )
            self._templates[template.template_id] = template
            return template

    def get_template(self, template_id: str) -> Optional[BehaviorTemplate]:
        """Retrieve a behavior template by its identifier.

        Args:
            template_id: The template's unique identifier.

        Returns:
            The BehaviorTemplate or None if not found.
        """
        return self._templates.get(template_id)

    def find_template_by_name(self, name: str) -> Optional[BehaviorTemplate]:
        """Find a behavior template by name.

        Args:
            name: The template name to search for.

        Returns:
            The BehaviorTemplate or None if not found.
        """
        for t in self._templates.values():
            if t.name == name:
                return t
        return None

    def list_templates(
        self, category: Optional[BehaviorCategory] = None,
    ) -> List[BehaviorTemplate]:
        """List all registered behavior templates, optionally filtered by category.

        Args:
            category: Optional category filter.

        Returns:
            List of matching BehaviorTemplate instances.
        """
        result = list(self._templates.values())
        if category is not None:
            result = [t for t in result if t.category == category]
        return sorted(result, key=lambda t: t.name)

    def remove_template(self, template_id: str) -> bool:
        """Remove a behavior template from the registry.

        Args:
            template_id: The template's unique identifier.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if template_id not in self._templates:
                return False
            del self._templates[template_id]
            return True

    def _validate_parameters(
        self, template: BehaviorTemplate, user_params: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Validate and merge user parameters with template defaults.

        Args:
            template: The behavior template defining parameter schema.
            user_params: User-supplied parameter overrides.

        Returns:
            Tuple of (merged_parameters, list_of_error_messages).
        """
        merged: Dict[str, Any] = {}
        errors: List[str] = []

        defaults = template.get_default_parameters()
        all_names = set(defaults.keys()) | set(user_params.keys())

        for name in all_names:
            param_def = template.get_parameter(name)
            if param_def is None:
                if name in user_params:
                    # Allow extra custom parameters
                    merged[name] = user_params[name]
                continue

            value = user_params.get(name, defaults.get(name))
            is_valid, err = param_def.validate(value)
            if not is_valid:
                errors.append(f"'{name}': {err}")
            else:
                merged[name] = value if value is not None else param_def.default_value

        return merged, errors

    # ------------------------------------------------------------------
    # Behavior Instance Management
    # ------------------------------------------------------------------

    def attach_behavior(
        self,
        object_id: str,
        template_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: Optional[int] = None,
    ) -> BehaviorInstance:
        """Attach a behavior to a game object.

        Creates a new BehaviorInstance from the specified template, validates
        and merges parameters, registers it on the object, and fires the
        on_attach lifecycle hook.

        Args:
            object_id: The game object to attach the behavior to.
            template_id: The template identifier to instantiate.
            parameters: Optional parameter overrides.
            priority: Optional execution priority override.

        Returns:
            The created BehaviorInstance.

        Raises:
            ValueError: If the template is not found.
        """
        with self._lock:
            template = self.get_template(template_id)
            if template is None:
                raise ValueError(f"Template '{template_id}' not found")

            merged_params, errors = self._validate_parameters(
                template, parameters or {},
            )

            instance = BehaviorInstance(
                template_id=template_id,
                object_id=object_id,
                parameters=merged_params,
                priority=priority if priority is not None else template.default_priority,
                enabled=True,
                state=BehaviorState.ATTACHED,
                attached_at=_time_module.time(),
            )

            # Build validation errors into metadata
            if errors:
                instance.metadata["_validation_errors"] = errors
                instance.state = BehaviorState.ERROR

            self._instances[instance.instance_id] = instance

            # Index by object
            if object_id not in self._object_index:
                self._object_index[object_id] = []
            self._object_index[object_id].append(instance.instance_id)

            # Ensure binding exists
            binding = self._ensure_binding(object_id)
            binding.behavior_ids.append(instance.instance_id)

            self._total_attached += 1

        # Fire on_attach hook (outside lock for safety)
        if instance._on_attach is not None:
            try:
                instance._on_attach(instance)
            except Exception:
                pass

        return instance

    def detach_behavior(self, instance_id: str) -> bool:
        """Detach a behavior from its object and remove it.

        Fires the on_detach lifecycle hook before removing the instance.

        Args:
            instance_id: The behavior instance identifier.

        Returns:
            True if detached, False if not found.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return False

        # Fire on_detach hook
        if instance._on_detach is not None:
            try:
                instance._on_detach(instance)
            except Exception:
                pass

        with self._lock:
            instance = self._instances.pop(instance_id, None)
            if instance is None:
                return False

            instance.state = BehaviorState.DETACHED

            # Remove from object index
            obj_list = self._object_index.get(instance.object_id, [])
            if instance_id in obj_list:
                obj_list.remove(instance_id)

            # Remove from binding
            binding = self._get_binding_for_object(instance.object_id)
            if binding and instance_id in binding.behavior_ids:
                binding.behavior_ids.remove(instance_id)

            self._total_detached += 1
            return True

    def get_behavior(self, instance_id: str) -> Optional[BehaviorInstance]:
        """Retrieve a behavior instance by its identifier.

        Args:
            instance_id: The behavior instance identifier.

        Returns:
            The BehaviorInstance or None if not found.
        """
        return self._instances.get(instance_id)

    def get_object_behaviors(self, object_id: str) -> List[BehaviorInstance]:
        """Get all behavior instances attached to a game object.

        Args:
            object_id: The game object identifier.

        Returns:
            List of BehaviorInstance objects sorted by priority.
        """
        instance_ids = self._object_index.get(object_id, [])
        instances = [self._instances[i] for i in instance_ids if i in self._instances]
        return sorted(instances, key=lambda i: i.priority)

    def enable_behavior(self, instance_id: str) -> bool:
        """Enable a previously disabled or paused behavior.

        Args:
            instance_id: The behavior instance identifier.

        Returns:
            True if enabled, False if not found.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.enabled = True
        instance.state = BehaviorState.ACTIVE
        return True

    def disable_behavior(self, instance_id: str) -> bool:
        """Disable a behavior, preventing update and event processing.

        Args:
            instance_id: The behavior instance identifier.

        Returns:
            True if disabled, False if not found.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.enabled = False
        instance.state = BehaviorState.DISABLED
        return True

    def pause_behavior(self, instance_id: str) -> bool:
        """Pause a behavior, suspending updates without disabling.

        Args:
            instance_id: The behavior instance identifier.

        Returns:
            True if paused, False if not found.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.state = BehaviorState.PAUSED
        return True

    def initialize_behavior(self, instance_id: str) -> bool:
        """Fire the on_init lifecycle hook for a behavior.

        Args:
            instance_id: The behavior instance identifier.

        Returns:
            True if initialized, False if not found.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return False

        if instance._on_init is not None:
            try:
                instance._on_init(instance)
            except Exception:
                pass

        instance.state = BehaviorState.INITIALIZED
        return True

    def update_behavior(
        self, instance_id: str, delta_time: float,
    ) -> None:
        """Fire the on_update lifecycle hook for a behavior.

        Args:
            instance_id: The behavior instance identifier.
            delta_time: Frame delta time in seconds.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return
        if not instance.enabled or instance.state not in (
            BehaviorState.ACTIVE, BehaviorState.INITIALIZED,
        ):
            return

        instance.last_update = _time_module.time()
        if instance._on_update is not None:
            try:
                instance._on_update(instance, delta_time)
            except Exception:
                pass

    def update_object_behaviors(
        self, object_id: str, delta_time: float,
    ) -> None:
        """Update all active behaviors on an object in priority order.

        Args:
            object_id: The game object identifier.
            delta_time: Frame delta time in seconds.
        """
        behaviors = self.get_object_behaviors(object_id)
        for instance in behaviors:
            self.update_behavior(instance.instance_id, delta_time)

    # ------------------------------------------------------------------
    # Parameter Management
    # ------------------------------------------------------------------

    def update_behavior_parameter(
        self, instance_id: str, param_name: str, value: Any,
    ) -> bool:
        """Update a single parameter on a behavior instance.

        Validates the new value against the original template parameter
        constraints before applying.

        Args:
            instance_id: The behavior instance identifier.
            param_name: Name of the parameter to update.
            value: New value to assign.

        Returns:
            True if updated successfully, False on validation failure or not found.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return False

        template = self._templates.get(instance.template_id)
        if template is None:
            # No template to validate against, allow direct set
            instance.set_parameter(param_name, value)
            return True

        param_def = template.get_parameter(param_name)
        if param_def is not None:
            is_valid, err = param_def.validate(value)
            if not is_valid:
                return False

        instance.set_parameter(param_name, value)
        return True

    def batch_update_parameters(
        self, instance_id: str, parameters: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """Update multiple parameters on a behavior instance at once.

        Args:
            instance_id: The behavior instance identifier.
            parameters: Dict of parameter name -> new value.

        Returns:
            Tuple of (all_succeeded, list_of_failed_parameter_names).
        """
        failed: List[str] = []
        for name, value in parameters.items():
            if not self.update_behavior_parameter(instance_id, name, value):
                failed.append(name)
        return (len(failed) == 0, failed)

    # ------------------------------------------------------------------
    # Event System
    # ------------------------------------------------------------------

    def emit_behavior_event(
        self, instance_id: str, event_type: str, event_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[BehaviorEvent]:
        """Emit an event from a behavior to sibling behaviors on the same object.

        The event is dispatched to all other behaviors on the same object
        that are enabled and have registered an on_event hook.

        Args:
            instance_id: The source behavior instance identifier.
            event_type: A string identifying the event (e.g. 'on_damage', 'on_collision').
            event_data: Optional dict of event payload data.

        Returns:
            The BehaviorEvent that was emitted, or None if source not found.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return None

        event = BehaviorEvent(
            source_behavior_id=instance_id,
            event_type=event_type,
            event_data=event_data or {},
            timestamp=_time_module.time(),
        )

        # Dispatch to sibling behaviors on the same object
        siblings = self._object_index.get(instance.object_id, [])
        for sid in siblings:
            if sid == instance_id:
                continue
            sibling = self._instances.get(sid)
            if sibling is None:
                continue
            if not sibling.enabled:
                continue
            if sibling.state in (BehaviorState.DISABLED, BehaviorState.ERROR, BehaviorState.DETACHED):
                continue
            if sibling._on_event is not None:
                try:
                    sibling._on_event(sibling, event)
                except Exception:
                    pass

        return event

    def broadcast_event(
        self, object_id: str, event_type: str, event_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[BehaviorEvent]:
        """Broadcast an event to all enabled behaviors on a game object.

        Unlike emit_behavior_event, this creates a system-level event (no
        source behavior) that all behaviors on the object receive.

        Args:
            object_id: The target game object identifier.
            event_type: A string identifying the event.
            event_data: Optional dict of event payload data.

        Returns:
            The BehaviorEvent that was broadcast.
        """
        event = BehaviorEvent(
            source_behavior_id="",  # system event
            event_type=event_type,
            event_data=event_data or {},
            timestamp=_time_module.time(),
        )

        instance_ids = self._object_index.get(object_id, [])
        for iid in instance_ids:
            instance = self._instances.get(iid)
            if instance is None:
                continue
            if not instance.enabled:
                continue
            if instance.state in (BehaviorState.DISABLED, BehaviorState.ERROR, BehaviorState.DETACHED):
                continue
            if instance._on_event is not None:
                try:
                    instance._on_event(instance, event)
                except Exception:
                    pass

        return event

    def get_recent_events(
        self, object_id: str, event_type: Optional[str] = None,
    ) -> List[BehaviorEvent]:
        """Retrieve recent events for an object. (Stub — full event history
        requires registering a listener that accumulates events.)

        Args:
            object_id: The game object identifier.
            event_type: Optional event type filter.

        Returns:
            Empty list (stub) — implement event recording via on_event hooks.
        """
        return []

    # ------------------------------------------------------------------
    # Binding Management
    # ------------------------------------------------------------------

    def _ensure_binding(self, object_id: str) -> BehaviorBinding:
        """Get or create a binding for an object.

        Args:
            object_id: The game object identifier.

        Returns:
            The existing or newly created BehaviorBinding.
        """
        for b in self._bindings.values():
            if b.object_id == object_id:
                return b
        binding = BehaviorBinding(object_id=object_id)
        self._bindings[binding.binding_id] = binding
        return binding

    def _get_binding_for_object(self, object_id: str) -> Optional[BehaviorBinding]:
        """Find the binding for a given object.

        Args:
            object_id: The game object identifier.

        Returns:
            The BehaviorBinding or None.
        """
        for b in self._bindings.values():
            if b.object_id == object_id:
                return b
        return None

    def get_binding(self, binding_id: str) -> Optional[BehaviorBinding]:
        """Retrieve a behavior binding by its identifier.

        Args:
            binding_id: The binding's unique identifier.

        Returns:
            The BehaviorBinding or None.
        """
        return self._bindings.get(binding_id)

    def get_object_binding(self, object_id: str) -> Optional[BehaviorBinding]:
        """Get the binding for a game object.

        Args:
            object_id: The game object identifier.

        Returns:
            The BehaviorBinding or None if no behaviors are attached.
        """
        return self._get_binding_for_object(object_id)

    # ------------------------------------------------------------------
    # Built-in Behavior Templates
    # ------------------------------------------------------------------

    def register_builtin_templates(self) -> List[BehaviorTemplate]:
        """Register all built-in behavior templates for common game patterns.

        Pre-built templates include platformer_controller, top_down_movement,
        health, damageable, projectile, collectible, patrol_ai, chase_ai,
        destructible, animated_sprite, rigidbody_2d, and follow_target.

        Returns:
            List of newly registered BehaviorTemplate instances.

        Raises:
            RuntimeError: If built-in templates were already registered.
        """
        with self._lock:
            if self._builtin_registered:
                raise RuntimeError("Built-in templates already registered")
            self._builtin_registered = True

        templates: List[BehaviorTemplate] = []

        # --- platformer_controller ---
        t = self.register_template(
            name="platformer_controller",
            description="Side-scrolling platformer character controller with gravity, jumping, and ground detection.",
            category=BehaviorCategory.MOVEMENT,
            parameters=[
                BehaviorParameter(name="move_speed", param_type=ParameterType.FLOAT,
                    default_value=250.0, min_value=0.0, max_value=5000.0,
                    description="Horizontal movement speed in units per second"),
                BehaviorParameter(name="jump_force", param_type=ParameterType.FLOAT,
                    default_value=500.0, min_value=0.0, max_value=10000.0,
                    description="Initial upward velocity when jumping"),
                BehaviorParameter(name="gravity", param_type=ParameterType.FLOAT,
                    default_value=980.0, min_value=0.0, max_value=10000.0,
                    description="Downward acceleration in units/s^2"),
                BehaviorParameter(name="max_fall_speed", param_type=ParameterType.FLOAT,
                    default_value=1000.0, min_value=0.0, max_value=10000.0,
                    description="Maximum vertical velocity during fall"),
                BehaviorParameter(name="acceleration", param_type=ParameterType.FLOAT,
                    default_value=1500.0, min_value=0.0, max_value=20000.0,
                    description="Horizontal acceleration in units/s^2"),
                BehaviorParameter(name="deceleration", param_type=ParameterType.FLOAT,
                    default_value=1000.0, min_value=0.0, max_value=20000.0,
                    description="Horizontal deceleration when no input"),
                BehaviorParameter(name="coyote_time", param_type=ParameterType.FLOAT,
                    default_value=0.1, min_value=0.0, max_value=1.0,
                    description="Grace period after leaving ground to still jump"),
                BehaviorParameter(name="jump_buffer_time", param_type=ParameterType.FLOAT,
                    default_value=0.1, min_value=0.0, max_value=0.5,
                    description="Buffer time to press jump slightly before landing"),
                BehaviorParameter(name="double_jump", param_type=ParameterType.BOOL,
                    default_value=False, description="Whether double jumping is allowed"),
                BehaviorParameter(name="wall_jump", param_type=ParameterType.BOOL,
                    default_value=False, description="Whether wall jumping is allowed"),
            ],
            default_priority=0,
            icon="platformer_icon",
            tags=["movement", "platformer", "2d", "physics"],
        )
        templates.append(t)

        # --- top_down_movement ---
        t = self.register_template(
            name="top_down_movement",
            description="Top-down 2D movement controller with 4 or 8 directional movement.",
            category=BehaviorCategory.MOVEMENT,
            parameters=[
                BehaviorParameter(name="move_speed", param_type=ParameterType.FLOAT,
                    default_value=200.0, min_value=0.0, max_value=5000.0,
                    description="Movement speed in units per second"),
                BehaviorParameter(name="acceleration", param_type=ParameterType.FLOAT,
                    default_value=2000.0, min_value=0.0, max_value=20000.0,
                    description="Movement acceleration in units/s^2"),
                BehaviorParameter(name="deceleration", param_type=ParameterType.FLOAT,
                    default_value=2000.0, min_value=0.0, max_value=20000.0,
                    description="Movement deceleration when no input"),
                BehaviorParameter(name="eight_directional", param_type=ParameterType.BOOL,
                    default_value=True, description="Allow 8-directional movement"),
                BehaviorParameter(name="diagonal_damping", param_type=ParameterType.FLOAT,
                    default_value=0.707, min_value=0.0, max_value=1.0,
                    description="Diagonal movement speed multiplier"),
                BehaviorParameter(name="rotate_to_direction", param_type=ParameterType.BOOL,
                    default_value=False,
                    description="Whether the object rotates to face movement direction"),
                BehaviorParameter(name="rotation_speed", param_type=ParameterType.FLOAT,
                    default_value=720.0, min_value=0.0, max_value=5000.0,
                    description="Degrees per second for rotation interpolation"),
            ],
            default_priority=0,
            icon="topdown_icon",
            tags=["movement", "topdown", "2d"],
        )
        templates.append(t)

        # --- health ---
        t = self.register_template(
            name="health",
            description="Health component with damage, healing, death events, and invulnerability frames.",
            category=BehaviorCategory.COMBAT,
            parameters=[
                BehaviorParameter(name="max_health", param_type=ParameterType.FLOAT,
                    default_value=100.0, min_value=1.0, max_value=1000000.0,
                    description="Maximum health points"),
                BehaviorParameter(name="current_health", param_type=ParameterType.FLOAT,
                    default_value=100.0, min_value=0.0, max_value=1000000.0,
                    description="Current health points"),
                BehaviorParameter(name="invulnerability_duration", param_type=ParameterType.FLOAT,
                    default_value=0.5, min_value=0.0, max_value=60.0,
                    description="Seconds of invulnerability after taking damage"),
                BehaviorParameter(name="auto_regenerate", param_type=ParameterType.BOOL,
                    default_value=False, description="Automatically regenerate health over time"),
                BehaviorParameter(name="regen_rate", param_type=ParameterType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=1000.0,
                    description="Health regenerated per second"),
                BehaviorParameter(name="regen_delay", param_type=ParameterType.FLOAT,
                    default_value=3.0, min_value=0.0, max_value=60.0,
                    description="Seconds before regeneration starts after damage"),
                BehaviorParameter(name="death_destroy", param_type=ParameterType.BOOL,
                    default_value=True,
                    description="Whether the object is destroyed on death"),
                BehaviorParameter(name="shield_amount", param_type=ParameterType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=100000.0,
                    description="Optional shield that absorbs damage first"),
            ],
            default_priority=1,
            icon="health_icon",
            tags=["combat", "health", "damage", "death"],
        )
        templates.append(t)

        # --- damageable ---
        t = self.register_template(
            name="damageable",
            description="Makes an object take damage from damage sources with hit flash and knockback.",
            category=BehaviorCategory.COMBAT,
            parameters=[
                BehaviorParameter(name="damage_multiplier", param_type=ParameterType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=100.0,
                    description="Multiplier applied to incoming damage"),
                BehaviorParameter(name="defense", param_type=ParameterType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=10000.0,
                    description="Flat damage reduction"),
                BehaviorParameter(name="damage_types_immune", param_type=ParameterType.STRING,
                    default_value="", min_value=0, max_value=500,
                    description="Comma-separated list of damage types this is immune to"),
                BehaviorParameter(name="knockback_multiplier", param_type=ParameterType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=100.0,
                    description="Multiplier for knockback force received"),
                BehaviorParameter(name="hit_flash_duration", param_type=ParameterType.FLOAT,
                    default_value=0.1, min_value=0.0, max_value=5.0,
                    description="Duration of hit flash effect in seconds"),
                BehaviorParameter(name="hit_flash_color", param_type=ParameterType.COLOR,
                    default_value=[255, 255, 255], min_value=0, max_value=255,
                    description="Color tint applied during hit flash"),
                BehaviorParameter(name="damage_particles", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Particle effect ID for damage feedback"),
            ],
            default_priority=2,
            icon="damageable_icon",
            tags=["combat", "damage", "health"],
        )
        templates.append(t)

        # --- projectile ---
        t = self.register_template(
            name="projectile",
            description="Projectile behavior with linear movement, lifespan, piercing, and on-hit effects.",
            category=BehaviorCategory.COMBAT,
            parameters=[
                BehaviorParameter(name="speed", param_type=ParameterType.FLOAT,
                    default_value=500.0, min_value=0.0, max_value=50000.0,
                    description="Projectile travel speed in units per second"),
                BehaviorParameter(name="lifespan", param_type=ParameterType.FLOAT,
                    default_value=3.0, min_value=0.01, max_value=60.0,
                    description="Maximum lifetime in seconds before auto-destruction"),
                BehaviorParameter(name="damage", param_type=ParameterType.FLOAT,
                    default_value=10.0, min_value=0.0, max_value=100000.0,
                    description="Damage dealt on impact"),
                BehaviorParameter(name="pierce_count", param_type=ParameterType.INT,
                    default_value=0, min_value=0, max_value=100,
                    description="How many targets the projectile can pierce through"),
                BehaviorParameter(name="homing", param_type=ParameterType.BOOL,
                    default_value=False, description="Whether projectile homes in on targets"),
                BehaviorParameter(name="homing_strength", param_type=ParameterType.FLOAT,
                    default_value=360.0, min_value=0.0, max_value=10000.0,
                    description="Degrees per second for homing rotation"),
                BehaviorParameter(name="explosion_radius", param_type=ParameterType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=5000.0,
                    description="If > 0, creates an area explosion on impact"),
                BehaviorParameter(name="gravity_affected", param_type=ParameterType.BOOL,
                    default_value=False,
                    description="Whether the projectile is affected by gravity"),
                BehaviorParameter(name="bounce_count", param_type=ParameterType.INT,
                    default_value=0, min_value=0, max_value=100,
                    description="Number of times the projectile bounces off surfaces"),
            ],
            default_priority=5,
            icon="projectile_icon",
            tags=["combat", "projectile", "bullet"],
        )
        templates.append(t)

        # --- collectible ---
        t = self.register_template(
            name="collectible",
            description="Makes an object collectible with pickup radius, floating animation, and collection events.",
            category=BehaviorCategory.GAMEPLAY,
            parameters=[
                BehaviorParameter(name="pickup_radius", param_type=ParameterType.FLOAT,
                    default_value=32.0, min_value=0.0, max_value=2000.0,
                    description="Radius within which the item can be picked up"),
                BehaviorParameter(name="float_amplitude", param_type=ParameterType.FLOAT,
                    default_value=4.0, min_value=0.0, max_value=200.0,
                    description="Vertical bobbing amplitude in pixels"),
                BehaviorParameter(name="float_frequency", param_type=ParameterType.FLOAT,
                    default_value=2.0, min_value=0.0, max_value=20.0,
                    description="Bobbing frequency in cycles per second"),
                BehaviorParameter(name="auto_collect", param_type=ParameterType.BOOL,
                    default_value=False,
                    description="Automatically collect when player is in range"),
                BehaviorParameter(name="collect_sound", param_type=ParameterType.AUDIO_CLIP,
                    default_value="", description="Sound played on collection"),
                BehaviorParameter(name="collect_particles", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Particle effect on collection"),
                BehaviorParameter(name="respawn_time", param_type=ParameterType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=3600.0,
                    description="Seconds before respawning; 0 means never respawn"),
                BehaviorParameter(name="consume_on_collect", param_type=ParameterType.BOOL,
                    default_value=True,
                    description="Whether the object is destroyed on collection"),
            ],
            default_priority=5,
            icon="collectible_icon",
            tags=["gameplay", "collectible", "pickup", "item"],
        )
        templates.append(t)

        # --- patrol_ai ---
        t = self.register_template(
            name="patrol_ai",
            description="AI behavior that moves an object between a series of patrol waypoints.",
            category=BehaviorCategory.AI,
            parameters=[
                BehaviorParameter(name="waypoints", param_type=ParameterType.STRING,
                    default_value="[]", min_value=0, max_value=10000,
                    description="JSON-encoded list of [[x, y], ...] waypoint positions"),
                BehaviorParameter(name="patrol_speed", param_type=ParameterType.FLOAT,
                    default_value=150.0, min_value=0.0, max_value=5000.0,
                    description="Movement speed during patrol"),
                BehaviorParameter(name="wait_at_waypoint", param_type=ParameterType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=60.0,
                    description="Seconds to wait at each waypoint"),
                BehaviorParameter(name="waypoint_radius", param_type=ParameterType.FLOAT,
                    default_value=8.0, min_value=1.0, max_value=500.0,
                    description="Distance threshold to consider waypoint reached"),
                BehaviorParameter(name="loop_mode", param_type=ParameterType.ENUM,
                    default_value="loop", options=["loop", "pingpong", "once"],
                    description="Patrol loop behavior: loop, pingpong, or once"),
                BehaviorParameter(name="facing_forward", param_type=ParameterType.BOOL,
                    default_value=True,
                    description="Whether the object faces the direction of movement"),
                BehaviorParameter(name="idle_animation", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Animation clip ID for idle state"),
                BehaviorParameter(name="walk_animation", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Animation clip ID for walking state"),
            ],
            default_priority=10,
            icon="patrol_icon",
            tags=["ai", "patrol", "movement", "npc"],
        )
        templates.append(t)

        # --- chase_ai ---
        t = self.register_template(
            name="chase_ai",
            description="AI behavior that makes an object chase a target, with detection range and line-of-sight.",
            category=BehaviorCategory.AI,
            parameters=[
                BehaviorParameter(name="target_id", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Object ID of the target to chase"),
                BehaviorParameter(name="chase_speed", param_type=ParameterType.FLOAT,
                    default_value=300.0, min_value=0.0, max_value=5000.0,
                    description="Movement speed while chasing"),
                BehaviorParameter(name="detection_range", param_type=ParameterType.FLOAT,
                    default_value=200.0, min_value=0.0, max_value=10000.0,
                    description="Maximum distance to detect and start chasing"),
                BehaviorParameter(name="stop_range", param_type=ParameterType.FLOAT,
                    default_value=40.0, min_value=0.0, max_value=2000.0,
                    description="Distance at which to stop and attack/interact"),
                BehaviorParameter(name="lose_range", param_type=ParameterType.FLOAT,
                    default_value=400.0, min_value=0.0, max_value=20000.0,
                    description="Distance beyond which to give up chase"),
                BehaviorParameter(name="require_line_of_sight", param_type=ParameterType.BOOL,
                    default_value=False,
                    description="Whether line-of-sight is required to detect"),
                BehaviorParameter(name="acceleration", param_type=ParameterType.FLOAT,
                    default_value=1000.0, min_value=0.0, max_value=20000.0,
                    description="Chase acceleration in units/s^2"),
                BehaviorParameter(name="pathfinding", param_type=ParameterType.BOOL,
                    default_value=False,
                    description="Whether to use pathfinding instead of direct movement"),
                BehaviorParameter(name="return_to_start", param_type=ParameterType.BOOL,
                    default_value=True,
                    description="Return to starting position when target is lost"),
            ],
            default_priority=10,
            icon="chase_icon",
            tags=["ai", "chase", "movement", "enemy"],
        )
        templates.append(t)

        # --- destructible ---
        t = self.register_template(
            name="destructible",
            description="Destructible object with health, destruction effects, debris, and staged damage.",
            category=BehaviorCategory.GAMEPLAY,
            parameters=[
                BehaviorParameter(name="max_hit_points", param_type=ParameterType.FLOAT,
                    default_value=50.0, min_value=1.0, max_value=100000.0,
                    description="Total hit points before destruction"),
                BehaviorParameter(name="current_hit_points", param_type=ParameterType.FLOAT,
                    default_value=50.0, min_value=0.0, max_value=100000.0,
                    description="Current hit points"),
                BehaviorParameter(name="destroy_effect", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Particle effect ID for destruction"),
                BehaviorParameter(name="destroy_sound", param_type=ParameterType.AUDIO_CLIP,
                    default_value="", description="Sound played on destruction"),
                BehaviorParameter(name="debris_count", param_type=ParameterType.INT,
                    default_value=4, min_value=0, max_value=100,
                    description="Number of debris pieces spawned on destruction"),
                BehaviorParameter(name="debris_prefab", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Prefab ID for debris pieces"),
                BehaviorParameter(name="damage_stages", param_type=ParameterType.INT,
                    default_value=3, min_value=1, max_value=10,
                    description="Number of visual damage stages before destruction"),
                BehaviorParameter(name="repairable", param_type=ParameterType.BOOL,
                    default_value=False, description="Whether the object can be repaired"),
                BehaviorParameter(name="respawn_after", param_type=ParameterType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=3600.0,
                    description="Seconds to respawn after destruction; 0 = never"),
            ],
            default_priority=3,
            icon="destructible_icon",
            tags=["gameplay", "destructible", "environment"],
        )
        templates.append(t)

        # --- animated_sprite ---
        t = self.register_template(
            name="animated_sprite",
            description="Sprite animation controller with multiple animation states and blend transitions.",
            category=BehaviorCategory.RENDERING,
            parameters=[
                BehaviorParameter(name="default_animation", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Animation clip ID for default state"),
                BehaviorParameter(name="animation_map", param_type=ParameterType.STRING,
                    default_value="{}", min_value=0, max_value=50000,
                    description="JSON mapping state names to animation clip IDs"),
                BehaviorParameter(name="fps", param_type=ParameterType.FLOAT,
                    default_value=30.0, min_value=1.0, max_value=120.0,
                    description="Frames per second for animation playback"),
                BehaviorParameter(name="flip_h", param_type=ParameterType.BOOL,
                    default_value=False, description="Whether sprite is flipped horizontally"),
                BehaviorParameter(name="flip_v", param_type=ParameterType.BOOL,
                    default_value=False, description="Whether sprite is flipped vertically"),
                BehaviorParameter(name="sorting_layer", param_type=ParameterType.INT,
                    default_value=0, min_value=-100, max_value=100,
                    description="Sorting layer for render ordering"),
                BehaviorParameter(name="order_in_layer", param_type=ParameterType.INT,
                    default_value=0, min_value=-10000, max_value=10000,
                    description="Order within the sorting layer"),
                BehaviorParameter(name="color_tint", param_type=ParameterType.COLOR,
                    default_value=[255, 255, 255, 255], min_value=0, max_value=255,
                    description="Color tint (RGBA) applied to the sprite"),
            ],
            default_priority=50,
            icon="sprite_icon",
            tags=["rendering", "sprite", "animation", "2d"],
        )
        templates.append(t)

        # --- rigidbody_2d ---
        t = self.register_template(
            name="rigidbody_2d",
            description="2D rigid body physics with velocity, drag, mass, and collision response.",
            category=BehaviorCategory.PHYSICS,
            parameters=[
                BehaviorParameter(name="mass", param_type=ParameterType.FLOAT,
                    default_value=1.0, min_value=0.001, max_value=100000.0,
                    description="Mass in kilograms"),
                BehaviorParameter(name="drag", param_type=ParameterType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=100.0,
                    description="Linear drag coefficient"),
                BehaviorParameter(name="angular_drag", param_type=ParameterType.FLOAT,
                    default_value=0.05, min_value=0.0, max_value=100.0,
                    description="Angular drag coefficient"),
                BehaviorParameter(name="gravity_scale", param_type=ParameterType.FLOAT,
                    default_value=1.0, min_value=-100.0, max_value=100.0,
                    description="Multiplier for global gravity"),
                BehaviorParameter(name="body_type", param_type=ParameterType.ENUM,
                    default_value="dynamic", options=["static", "kinematic", "dynamic"],
                    description="Rigid body type: static, kinematic, or dynamic"),
                BehaviorParameter(name="freeze_position_x", param_type=ParameterType.BOOL,
                    default_value=False, description="Freeze position on X axis"),
                BehaviorParameter(name="freeze_position_y", param_type=ParameterType.BOOL,
                    default_value=False, description="Freeze position on Y axis"),
                BehaviorParameter(name="freeze_rotation", param_type=ParameterType.BOOL,
                    default_value=False, description="Freeze rotation"),
                BehaviorParameter(name="collision_detection", param_type=ParameterType.ENUM,
                    default_value="discrete", options=["discrete", "continuous"],
                    description="Collision detection mode"),
            ],
            default_priority=-5,
            icon="physics_icon",
            tags=["physics", "rigidbody", "2d", "gravity"],
        )
        templates.append(t)

        # --- follow_target ---
        t = self.register_template(
            name="follow_target",
            description="Makes an object follow a target with configurable offset, smoothing, and constraints.",
            category=BehaviorCategory.MOVEMENT,
            parameters=[
                BehaviorParameter(name="target_id", param_type=ParameterType.OBJECT_REF,
                    default_value="", description="Object ID of the target to follow"),
                BehaviorParameter(name="offset_x", param_type=ParameterType.FLOAT,
                    default_value=0.0, min_value=-10000.0, max_value=10000.0,
                    description="Horizontal offset from target position"),
                BehaviorParameter(name="offset_y", param_type=ParameterType.FLOAT,
                    default_value=0.0, min_value=-10000.0, max_value=10000.0,
                    description="Vertical offset from target position"),
                BehaviorParameter(name="smooth_time", param_type=ParameterType.FLOAT,
                    default_value=0.1, min_value=0.0, max_value=10.0,
                    description="Smoothing time for interpolation (lower = snappier)"),
                BehaviorParameter(name="max_speed", param_type=ParameterType.FLOAT,
                    default_value=10000.0, min_value=0.0, max_value=50000.0,
                    description="Maximum following speed; 0 = unlimited"),
                BehaviorParameter(name="follow_x", param_type=ParameterType.BOOL,
                    default_value=True, description="Follow on X axis"),
                BehaviorParameter(name="follow_y", param_type=ParameterType.BOOL,
                    default_value=True, description="Follow on Y axis"),
                BehaviorParameter(name="snap_on_enable", param_type=ParameterType.BOOL,
                    default_value=True, description="Snap to target position on enable"),
                BehaviorParameter(name="boundary_min_x", param_type=ParameterType.FLOAT,
                    default_value=-100000.0, min_value=-100000.0, max_value=0.0,
                    description="Minimum X boundary for following"),
                BehaviorParameter(name="boundary_max_x", param_type=ParameterType.FLOAT,
                    default_value=100000.0, min_value=0.0, max_value=100000.0,
                    description="Maximum X boundary for following"),
            ],
            default_priority=1,
            icon="follow_icon",
            tags=["movement", "follow", "camera", "tracking"],
        )
        templates.append(t)

        return templates

    # ------------------------------------------------------------------
    # Statistics and Lifecycle
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return current status and statistics for the behavior system.

        Returns:
            Dict with template count, instance count, object count, and counters.
        """
        active_instances = sum(
            1 for i in self._instances.values()
            if i.state not in (BehaviorState.DETACHED, BehaviorState.ERROR)
        )
        return {
            "total_templates": len(self._templates),
            "total_instances": len(self._instances),
            "active_instances": active_instances,
            "total_objects_with_behaviors": len(self._object_index),
            "total_bindings": len(self._bindings),
            "total_attached": self._total_attached,
            "total_detached": self._total_detached,
            "builtin_registered": self._builtin_registered,
            "categories": {
                cat.value: len(self.list_templates(cat))
                for cat in BehaviorCategory
            },
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Return health/diagnostic information for the behavior system.

        Returns:
            Dict with health indicators and warnings.
        """
        warnings: List[str] = []
        error_count = sum(
            1 for i in self._instances.values()
            if i.state == BehaviorState.ERROR
        )
        orphan_count = 0
        for i in self._instances.values():
            if i.object_id not in self._object_index:
                orphan_count += 1

        if error_count > 0:
            warnings.append(f"{error_count} behavior(s) in ERROR state")
        if orphan_count > 0:
            warnings.append(f"{orphan_count} orphaned behavior(s) without object index")
        if not self._builtin_registered:
            warnings.append("Built-in templates not yet registered")

        return {
            "healthy": len(warnings) == 0,
            "warning_count": len(warnings),
            "warnings": warnings,
            "error_instances": error_count,
            "orphaned_instances": orphan_count,
        }

    def reset(self) -> None:
        """Reset all data, clearing templates, instances, bindings, and counters."""
        with self._lock:
            self._templates.clear()
            self._instances.clear()
            self._bindings.clear()
            self._object_index.clear()
            self._total_attached = 0
            self._total_detached = 0
            self._builtin_registered = False

    @staticmethod
    def create_parameter(
        name: str,
        param_type: ParameterType,
        default_value: Any = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        options: Optional[List[str]] = None,
        description: str = "",
        required: bool = False,
    ) -> BehaviorParameter:
        """Factory method to create a BehaviorParameter with a generated ID.

        Args:
            name: Parameter name.
            param_type: Parameter data type.
            default_value: Default value.
            min_value: Minimum allowed value.
            max_value: Maximum allowed value.
            options: Valid enum options (for ENUM type).
            description: Human-readable description.
            required: Whether the parameter is required.

        Returns:
            A new BehaviorParameter instance.
        """
        return BehaviorParameter(
            name=name,
            param_type=param_type,
            default_value=default_value,
            min_value=min_value,
            max_value=max_value,
            options=list(options) if options else [],
            description=description,
            required=required,
        )


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

def get_engine_object_behavior() -> EngineObjectBehavior:
    """Return the global EngineObjectBehavior singleton instance."""
    return EngineObjectBehavior.get_instance()