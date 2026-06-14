"""
SparkLabs Engine - Extension Platform

A comprehensive plugin extension system for the SparkLabs game engine that
manages the full lifecycle of engine extensions: registration, discovery,
dependency resolution, version compatibility checking, loading, activation,
and unloading. Extensions can contribute new behaviors, object types,
conditions, actions, and visual effects to the engine.

Architecture:
  EngineExtensionPlatform (Singleton)
    |-- ExtensionManifest      — metadata, authorship, compatibility declarations
    |-- ExtensionInstance      — runtime state of a loaded extension
    |-- RegisteredBehavior     — reusable behavior definition from an extension
    |-- RegisteredObject       — custom game object type from an extension
    |-- RegisteredCondition    — event condition contributed by an extension
    |-- RegisteredAction       — event action contributed by an extension
    |-- RegisteredEffect       — visual effect contributed by an extension
    |-- ExtensionDependency    — declared dependency on another extension
    |-- ExtensionCategoryEntry — metadata for extension categories

Platform Features:
  - REGISTRY:  register, discover, and query extensions by category or state
  - LIFECYCLE: install, load, initialize, activate, deactivate, unload, uninstall
  - BEHAVIORS: reusable behavior scripts that attach to game objects
  - OBJECTS:   custom game object types with properties and rendering
  - EVENTS:    custom conditions and actions for the event scripting system
  - EFFECTS:   visual effects like particles, screen shake, post-processing
  - DEPS:      dependency declaration and resolution with version constraints
  - VERSION:   semantic versioning with engine compatibility checks
  - MARKETPLACE: available, installed, and community extension metadata

Usage:
    eep = get_engine_extension_platform()
    manifest = ExtensionManifest(name="Platformer Kit", version="1.0.0",
        category=ExtensionCategory.BEHAVIOR)
    eep.register_extension(manifest)
    eep.load_extension(manifest.extension_id)
    eep.activate_extension(manifest.extension_id)
    status = eep.get_status()
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExtensionState(str, Enum):
    """Lifecycle state of an engine extension instance."""
    AVAILABLE = "available"
    INSTALLING = "installing"
    INSTALLED = "installed"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    INACTIVE = "inactive"
    UNLOADING = "unloading"
    ERROR = "error"
    UNINSTALLING = "uninstalling"


class ExtensionCategory(str, Enum):
    """Category classification for engine extensions."""
    BEHAVIOR = "behavior"
    OBJECT = "object"
    RENDERING = "rendering"
    AUDIO = "audio"
    PHYSICS = "physics"
    INPUT = "input"
    UI = "ui"
    NETWORK = "network"
    AI = "ai"
    UTILITY = "utility"
    GAMEPLAY = "gameplay"


class PermissionLevel(str, Enum):
    """Permission scope granted to an engine extension."""
    READ_ONLY = "read_only"
    FILE_ACCESS = "file_access"
    NETWORK = "network"
    FULL_ACCESS = "full_access"
    SYSTEM = "system"


class CompatibilityStatus(str, Enum):
    """Engine version compatibility check result."""
    COMPATIBLE = "compatible"
    NEEDS_UPDATE = "needs_update"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ExtensionManifest:
    """Declarative metadata describing an engine extension.

    Contains authorship, versioning, compatibility constraints, permissions,
    and categorization information used during registration and discovery.
    """

    extension_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    category: ExtensionCategory = ExtensionCategory.UTILITY
    dependencies: List[str] = field(default_factory=list)
    engine_version_min: str = "1.0.0"
    engine_version_max: str = ""
    permissions: List[PermissionLevel] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    homepage: str = ""
    license: str = "MIT"
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the manifest to a dictionary."""
        return {
            "extension_id": self.extension_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "category": self.category.value,
            "dependencies": self.dependencies,
            "engine_version_min": self.engine_version_min,
            "engine_version_max": self.engine_version_max,
            "permissions": [p.value for p in self.permissions],
            "tags": self.tags,
            "homepage": self.homepage,
            "license": self.license,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ExtensionInstance:
    """Runtime representation of a loaded engine extension.

    Tracks the current lifecycle state, timestamps for load and activation
    events, and collections of registered contributions (behaviors, objects,
    conditions, actions, effects).
    """

    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    manifest: ExtensionManifest = field(default_factory=ExtensionManifest)
    state: ExtensionState = ExtensionState.AVAILABLE
    loaded_at: float = 0.0
    activated_at: float = 0.0
    behaviors: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the extension instance to a dictionary."""
        return {
            "instance_id": self.instance_id,
            "manifest": self.manifest.to_dict(),
            "state": self.state.value,
            "loaded_at": self.loaded_at,
            "activated_at": self.activated_at,
            "behaviors": self.behaviors,
            "objects": self.objects,
            "conditions": self.conditions,
            "actions": self.actions,
            "effects": self.effects,
        }


@dataclass
class RegisteredBehavior:
    """Reusable behavior definition contributed by an extension.

    Behaviors can be attached to game objects to provide movement patterns,
    AI routines, interaction logic, and other gameplay functionality.
    """

    behavior_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    runtime_class: str = ""
    icon: str = ""
    extension_id: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the registered behavior to a dictionary."""
        return {
            "behavior_id": self.behavior_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters,
            "runtime_class": self.runtime_class,
            "icon": self.icon,
            "extension_id": self.extension_id,
            "created_at": self.created_at,
        }


@dataclass
class RegisteredObject:
    """Custom game object type definition contributed by an extension.

    Object types define new entity blueprints with custom properties,
    rendering configurations, and default behavior bindings.
    """

    object_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    renderer_type: str = "sprite"
    icon: str = ""
    extension_id: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the registered object type to a dictionary."""
        return {
            "object_id": self.object_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "properties": self.properties,
            "renderer_type": self.renderer_type,
            "icon": self.icon,
            "extension_id": self.extension_id,
            "created_at": self.created_at,
        }


@dataclass
class RegisteredCondition:
    """Event condition definition contributed by an extension.

    Conditions are boolean predicates evaluated by the event scripting
    system to determine whether an action should execute.
    """

    condition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    evaluator: str = ""
    icon: str = ""
    extension_id: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the registered condition to a dictionary."""
        return {
            "condition_id": self.condition_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "evaluator": self.evaluator,
            "icon": self.icon,
            "extension_id": self.extension_id,
            "created_at": self.created_at,
        }


@dataclass
class RegisteredAction:
    """Event action definition contributed by an extension.

    Actions are executable operations triggered by the event scripting
    system when their associated conditions are met.
    """

    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    executor: str = ""
    icon: str = ""
    extension_id: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the registered action to a dictionary."""
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "executor": self.executor,
            "icon": self.icon,
            "extension_id": self.extension_id,
            "created_at": self.created_at,
        }


@dataclass
class RegisteredEffect:
    """Visual effect definition contributed by an extension.

    Effects provide runtime visual enhancements such as particle bursts,
    screen shake, post-processing filters, and custom shader passes.
    """

    effect_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    apply_function: str = ""
    icon: str = ""
    extension_id: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the registered effect to a dictionary."""
        return {
            "effect_id": self.effect_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "apply_function": self.apply_function,
            "icon": self.icon,
            "extension_id": self.extension_id,
            "created_at": self.created_at,
        }


@dataclass
class ExtensionDependency:
    """Declared dependency relationship between two engine extensions.

    Used for dependency graph resolution, conflict detection, and ensuring
    that required extensions are loaded before a dependent extension activates.
    """

    dependency_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    extension_id: str = ""
    version_range: str = ">=1.0.0"
    required: bool = True
    reason: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the extension dependency to a dictionary."""
        return {
            "dependency_id": self.dependency_id,
            "extension_id": self.extension_id,
            "version_range": self.version_range,
            "required": self.required,
            "reason": self.reason,
            "created_at": self.created_at,
        }


@dataclass
class ExtensionCategoryEntry:
    """Metadata descriptor for an extension category.

    Used for marketplace browsing, filtering, and UI organization of
    available engine extensions by functional domain.
    """

    category_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    icon: str = ""
    category_type: ExtensionCategory = ExtensionCategory.UTILITY
    extension_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the category entry to a dictionary."""
        return {
            "category_id": self.category_id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category_type": self.category_type.value,
            "extension_count": self.extension_count,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Singleton: EngineExtensionPlatform
# ---------------------------------------------------------------------------

class EngineExtensionPlatform:
    """Plugin extension system for the SparkLabs game engine.

    Manages the complete lifecycle of engine extensions including registration,
    discovery, dependency resolution, loading, activation, deactivation,
    and unloading. Extensions contribute new behaviors, object types,
    conditions, actions, and visual effects that integrate with the engine's
    existing systems.

    Usage:
        eep = get_engine_extension_platform()
        manifest = ExtensionManifest(name="My Kit", version="1.0.0")
        eep.register_extension(manifest)
        eep.load_extension(manifest.extension_id)
        eep.activate_extension(manifest.extension_id)
        behaviors = eep.get_available_behaviors()
    """

    _instance: Optional["EngineExtensionPlatform"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineExtensionPlatform":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineExtensionPlatform":
        """Return the singleton EngineExtensionPlatform instance."""
        return cls()

    def _initialize(self) -> None:
        """Initialize internal state (called once by __new__)."""
        if getattr(self, "_initialized", False):
            return

        # Extension registry
        self._extensions: Dict[str, ExtensionInstance] = {}
        self._manifests: Dict[str, ExtensionManifest] = {}
        self._dependencies: Dict[str, List[ExtensionDependency]] = {}

        # Contribution registries
        self._behaviors: Dict[str, RegisteredBehavior] = {}
        self._objects: Dict[str, RegisteredObject] = {}
        self._conditions: Dict[str, RegisteredCondition] = {}
        self._actions: Dict[str, RegisteredAction] = {}
        self._effects: Dict[str, RegisteredEffect] = {}

        # Marketplace
        self._marketplace_extensions: Dict[str, ExtensionManifest] = {}
        self._category_entries: Dict[str, ExtensionCategoryEntry] = {}

        # Statistics
        self._total_registered: int = 0
        self._total_loaded: int = 0
        self._total_activated: int = 0
        self._total_behaviors: int = 0
        self._total_objects: int = 0
        self._total_conditions: int = 0
        self._total_actions: int = 0
        self._total_effects: int = 0
        self._error_count: int = 0
        self._tick_count: int = 0

        self._engine_version: str = "1.0.0"
        self._initialized: bool = True

    # ------------------------------------------------------------------
    # Extension Registry
    # ------------------------------------------------------------------

    def register_extension(self, manifest: ExtensionManifest) -> ExtensionInstance:
        """Register a new extension with the platform.

        Validates the manifest, stores it in the registry, and creates a
        corresponding ExtensionInstance in AVAILABLE state.

        Args:
            manifest: The extension manifest declaring metadata and constraints.

        Returns:
            The newly created ExtensionInstance.

        Raises:
            ValueError: If an extension with the same ID is already registered.
        """
        if manifest.extension_id in self._extensions:
            raise ValueError(
                f"Extension '{manifest.extension_id}' is already registered."
            )

        compat = self.check_compatibility(manifest)
        if compat == CompatibilityStatus.INCOMPATIBLE:
            raise ValueError(
                f"Extension '{manifest.name}' is incompatible with engine "
                f"version {self._engine_version}."
            )

        instance = ExtensionInstance(
            manifest=manifest,
            state=ExtensionState.AVAILABLE,
        )
        self._extensions[manifest.extension_id] = instance
        self._manifests[manifest.extension_id] = manifest
        self._dependencies[manifest.extension_id] = []
        self._total_registered += 1

        return instance

    def load_extension(self, extension_id: str) -> ExtensionInstance:
        """Load an extension, preparing it for initialization.

        Transitions the extension from AVAILABLE/INSTALLED through LOADING
        to LOADED state. Validates that dependencies are met before loading.

        Args:
            extension_id: The unique identifier of the extension to load.

        Returns:
            The updated ExtensionInstance.

        Raises:
            ValueError: If the extension is not found or cannot be loaded.
        """
        instance = self._get_instance(extension_id)

        if instance.state not in (ExtensionState.AVAILABLE, ExtensionState.INSTALLED):
            raise ValueError(
                f"Extension '{extension_id}' is in state '{instance.state.value}' "
                f"and cannot be loaded."
            )

        # Check dependencies before loading
        dep_status = self.check_dependencies(extension_id)
        if not dep_status.get("all_met", False):
            missing = dep_status.get("missing", [])
            if missing:
                raise ValueError(
                    f"Dependencies not met for '{extension_id}': {missing}"
                )

        instance.state = ExtensionState.LOADING

        # Simulate loading work
        instance.state = ExtensionState.LOADED
        instance.loaded_at = _time_module.time()
        self._total_loaded += 1

        return instance

    def activate_extension(self, extension_id: str) -> ExtensionInstance:
        """Activate a loaded extension, making its contributions available.

        Transitions the extension from LOADED through INITIALIZING to ACTIVE
        state. Contributions (behaviors, objects, conditions, actions, effects)
        are registered in the corresponding registries.

        Args:
            extension_id: The unique identifier of the extension to activate.

        Returns:
            The updated ExtensionInstance.

        Raises:
            ValueError: If the extension is not found or not in LOADED state.
        """
        instance = self._get_instance(extension_id)

        if instance.state != ExtensionState.LOADED:
            raise ValueError(
                f"Extension '{extension_id}' must be LOADED before activation, "
                f"current state: '{instance.state.value}'."
            )

        instance.state = ExtensionState.INITIALIZING

        # Initialize extension contributions (simulated as registration happens
        # via dedicated register_* methods that the extension calls during init)

        instance.state = ExtensionState.ACTIVE
        instance.activated_at = _time_module.time()
        self._total_activated += 1

        return instance

    def deactivate_extension(self, extension_id: str) -> ExtensionInstance:
        """Deactivate an active extension, disabling its contributions.

        Transitions from ACTIVE through DEACTIVATING to INACTIVE.
        Contributions remain registered but are marked as inactive.

        Args:
            extension_id: The unique identifier of the extension to deactivate.

        Returns:
            The updated ExtensionInstance.
        """
        instance = self._get_instance(extension_id)

        if instance.state != ExtensionState.ACTIVE:
            raise ValueError(
                f"Extension '{extension_id}' must be ACTIVE to deactivate, "
                f"current state: '{instance.state.value}'."
            )

        # Check if other extensions depend on this one before deactivating
        dependents = self._find_dependents(extension_id)
        if dependents:
            raise ValueError(
                f"Cannot deactivate '{extension_id}': still required by "
                f"{dependents}."
            )

        instance.state = ExtensionState.DEACTIVATING
        instance.state = ExtensionState.INACTIVE

        return instance

    def unload_extension(self, extension_id: str) -> ExtensionInstance:
        """Unload an inactive extension, releasing runtime resources.

        Transitions from INACTIVE through UNLOADING to INSTALLED state.
        Removes contributions from active registries.

        Args:
            extension_id: The unique identifier of the extension to unload.

        Returns:
            The updated ExtensionInstance.
        """
        instance = self._get_instance(extension_id)

        if instance.state not in (ExtensionState.INACTIVE, ExtensionState.ERROR):
            raise ValueError(
                f"Extension '{extension_id}' must be INACTIVE or in ERROR state "
                f"to unload, current state: '{instance.state.value}'."
            )

        instance.state = ExtensionState.UNLOADING

        # Remove registered contributions
        for bid in instance.behaviors:
            self._behaviors.pop(bid, None)
        for oid in instance.objects:
            self._objects.pop(oid, None)
        for cid in instance.conditions:
            self._conditions.pop(cid, None)
        for aid in instance.actions:
            self._actions.pop(aid, None)
        for eid in instance.effects:
            self._effects.pop(eid, None)

        instance.behaviors.clear()
        instance.objects.clear()
        instance.conditions.clear()
        instance.actions.clear()
        instance.effects.clear()

        instance.state = ExtensionState.INSTALLED
        instance.loaded_at = 0.0
        instance.activated_at = 0.0

        return instance

    def get_extension(self, extension_id: str) -> ExtensionInstance:
        """Retrieve an extension instance by its unique identifier.

        Args:
            extension_id: The unique identifier of the extension.

        Returns:
            The ExtensionInstance.

        Raises:
            KeyError: If the extension is not found.
        """
        return self._get_instance(extension_id)

    def list_extensions(
        self,
        category: Optional[ExtensionCategory] = None,
        state: Optional[ExtensionState] = None,
    ) -> List[ExtensionInstance]:
        """List extensions with optional category and state filters.

        Args:
            category: Optional ExtensionCategory to filter by.
            state: Optional ExtensionState to filter by.

        Returns:
            A list of matching ExtensionInstance objects.
        """
        results: List[ExtensionInstance] = []
        for instance in self._extensions.values():
            if category is not None and instance.manifest.category != category:
                continue
            if state is not None and instance.state != state:
                continue
            results.append(instance)
        return results

    def delete_extension(self, extension_id: str) -> bool:
        """Permanently remove an extension from the registry.

        The extension must be in INACTIVE or ERROR state before deletion.

        Args:
            extension_id: The unique identifier of the extension to delete.

        Returns:
            True if the extension was deleted successfully.
        """
        instance = self._get_instance(extension_id)

        if instance.state in (ExtensionState.ACTIVE, ExtensionState.LOADED):
            raise ValueError(
                f"Cannot delete active/loaded extension '{extension_id}'. "
                f"Deactivate and unload it first."
            )

        self._extensions.pop(extension_id, None)
        self._manifests.pop(extension_id, None)
        self._dependencies.pop(extension_id, None)
        return True

    # ------------------------------------------------------------------
    # Behavior Extensions
    # ------------------------------------------------------------------

    def register_behavior(
        self, extension_id: str, behavior_def: RegisteredBehavior
    ) -> RegisteredBehavior:
        """Register a new behavior from an extension.

        The extension must be in an active-capable state. The behavior
        is added to the global behavior registry and linked to the extension.

        Args:
            extension_id: The extension contributing this behavior.
            behavior_def: The behavior definition to register.

        Returns:
            The registered RegisteredBehavior with assigned behavior_id.
        """
        instance = self._get_instance(extension_id)

        behavior_def.extension_id = extension_id
        if not behavior_def.behavior_id:
            behavior_def.behavior_id = uuid.uuid4().hex

        self._behaviors[behavior_def.behavior_id] = behavior_def
        instance.behaviors.append(behavior_def.behavior_id)
        self._total_behaviors += 1

        return behavior_def

    def get_available_behaviors(self) -> List[RegisteredBehavior]:
        """Get all currently registered behaviors.

        Returns:
            A list of all RegisteredBehavior definitions.
        """
        return list(self._behaviors.values())

    # ------------------------------------------------------------------
    # Object Extensions
    # ------------------------------------------------------------------

    def register_object(
        self, extension_id: str, object_def: RegisteredObject
    ) -> RegisteredObject:
        """Register a new game object type from an extension.

        Args:
            extension_id: The extension contributing this object type.
            object_def: The object type definition to register.

        Returns:
            The registered RegisteredObject with assigned object_id.
        """
        instance = self._get_instance(extension_id)

        object_def.extension_id = extension_id
        if not object_def.object_id:
            object_def.object_id = uuid.uuid4().hex

        self._objects[object_def.object_id] = object_def
        instance.objects.append(object_def.object_id)
        self._total_objects += 1

        return object_def

    def get_available_objects(self) -> List[RegisteredObject]:
        """Get all currently registered object types.

        Returns:
            A list of all RegisteredObject definitions.
        """
        return list(self._objects.values())

    # ------------------------------------------------------------------
    # Condition / Action Extensions
    # ------------------------------------------------------------------

    def register_condition(
        self, extension_id: str, condition_def: RegisteredCondition
    ) -> RegisteredCondition:
        """Register a new event condition from an extension.

        Args:
            extension_id: The extension contributing this condition.
            condition_def: The condition definition to register.

        Returns:
            The registered RegisteredCondition with assigned condition_id.
        """
        instance = self._get_instance(extension_id)

        condition_def.extension_id = extension_id
        if not condition_def.condition_id:
            condition_def.condition_id = uuid.uuid4().hex

        self._conditions[condition_def.condition_id] = condition_def
        instance.conditions.append(condition_def.condition_id)
        self._total_conditions += 1

        return condition_def

    def register_action(
        self, extension_id: str, action_def: RegisteredAction
    ) -> RegisteredAction:
        """Register a new event action from an extension.

        Args:
            extension_id: The extension contributing this action.
            action_def: The action definition to register.

        Returns:
            The registered RegisteredAction with assigned action_id.
        """
        instance = self._get_instance(extension_id)

        action_def.extension_id = extension_id
        if not action_def.action_id:
            action_def.action_id = uuid.uuid4().hex

        self._actions[action_def.action_id] = action_def
        instance.actions.append(action_def.action_id)
        self._total_actions += 1

        return action_def

    def get_available_conditions(self) -> List[RegisteredCondition]:
        """Get all currently registered conditions.

        Returns:
            A list of all RegisteredCondition definitions.
        """
        return list(self._conditions.values())

    def get_available_actions(self) -> List[RegisteredAction]:
        """Get all currently registered actions.

        Returns:
            A list of all RegisteredAction definitions.
        """
        return list(self._actions.values())

    # ------------------------------------------------------------------
    # Effect Extensions
    # ------------------------------------------------------------------

    def register_effect(
        self, extension_id: str, effect_def: RegisteredEffect
    ) -> RegisteredEffect:
        """Register a new visual effect from an extension.

        Args:
            extension_id: The extension contributing this effect.
            effect_def: The effect definition to register.

        Returns:
            The registered RegisteredEffect with assigned effect_id.
        """
        instance = self._get_instance(extension_id)

        effect_def.extension_id = extension_id
        if not effect_def.effect_id:
            effect_def.effect_id = uuid.uuid4().hex

        self._effects[effect_def.effect_id] = effect_def
        instance.effects.append(effect_def.effect_id)
        self._total_effects += 1

        return effect_def

    def get_available_effects(self) -> List[RegisteredEffect]:
        """Get all currently registered effects.

        Returns:
            A list of all RegisteredEffect definitions.
        """
        return list(self._effects.values())

    # ------------------------------------------------------------------
    # Dependency Management
    # ------------------------------------------------------------------

    def add_dependency(
        self, extension_id: str, dependency: ExtensionDependency
    ) -> ExtensionDependency:
        """Declare a dependency relationship for an extension.

        Args:
            extension_id: The extension that requires the dependency.
            dependency: The dependency declaration.

        Returns:
            The registered ExtensionDependency.
        """
        instance = self._get_instance(extension_id)

        if not dependency.dependency_id:
            dependency.dependency_id = uuid.uuid4().hex

        if extension_id not in self._dependencies:
            self._dependencies[extension_id] = []
        self._dependencies[extension_id].append(dependency)

        return dependency

    def check_dependencies(self, extension_id: str) -> Dict[str, Any]:
        """Check whether all declared dependencies for an extension are met.

        Iterates through declared dependencies and verifies each one is
        registered and in a compatible state.

        Args:
            extension_id: The extension whose dependencies to check.

        Returns:
            A dict with keys 'all_met' (bool), 'missing' (list of IDs),
            'met' (list of IDs), and 'details' (list of per-dependency info).
        """
        result: Dict[str, Any] = {
            "all_met": True,
            "missing": [],
            "met": [],
            "details": [],
        }

        deps = self._dependencies.get(extension_id, [])
        if not deps:
            return result

        for dep in deps:
            dep_info = {
                "dependency_id": dep.dependency_id,
                "extension_id": dep.extension_id,
                "required": dep.required,
                "status": "unknown",
                "reason": dep.reason,
            }

            if dep.extension_id in self._extensions:
                dep_instance = self._extensions[dep.extension_id]
                if dep_instance.state in (ExtensionState.ACTIVE, ExtensionState.LOADED):
                    dep_info["status"] = "met"
                    result["met"].append(dep.extension_id)
                else:
                    dep_info["status"] = "not_ready"
                    if dep.required:
                        result["missing"].append(dep.extension_id)
                        result["all_met"] = False
            else:
                dep_info["status"] = "missing"
                if dep.required:
                    result["missing"].append(dep.extension_id)
                    result["all_met"] = False

            result["details"].append(dep_info)

        return result

    def resolve_dependencies(self, extension_id: str) -> Dict[str, Any]:
        """Resolve and automatically load all unmet dependencies.

        Attempts to load and activate each dependency that is registered
        but not yet in an active state.

        Args:
            extension_id: The extension whose dependencies to resolve.

        Returns:
            A dict with resolution results including 'resolved' and 'failed' lists.
        """
        result: Dict[str, Any] = {
            "resolved": [],
            "failed": [],
            "already_active": [],
        }

        dep_check = self.check_dependencies(extension_id)
        deps = self._dependencies.get(extension_id, [])

        for dep in deps:
            if dep.extension_id not in self._extensions:
                result["failed"].append({
                    "extension_id": dep.extension_id,
                    "reason": "Not registered",
                })
                continue

            dep_instance = self._extensions[dep.extension_id]
            if dep_instance.state == ExtensionState.ACTIVE:
                result["already_active"].append(dep.extension_id)
                continue

            try:
                if dep_instance.state in (ExtensionState.AVAILABLE, ExtensionState.INSTALLED):
                    self.load_extension(dep.extension_id)
                if dep_instance.state == ExtensionState.LOADED:
                    self.activate_extension(dep.extension_id)
                result["resolved"].append(dep.extension_id)
            except Exception as exc:
                result["failed"].append({
                    "extension_id": dep.extension_id,
                    "reason": str(exc),
                })

        return result

    # ------------------------------------------------------------------
    # Version & Compatibility Management
    # ------------------------------------------------------------------

    def check_compatibility(self, manifest: ExtensionManifest) -> CompatibilityStatus:
        """Check whether a manifest is compatible with the current engine version.

        Performs semantic version comparison between the manifest's declared
        engine_version_min/engine_version_max constraints and the engine version.

        Args:
            manifest: The extension manifest to check.

        Returns:
            The CompatibilityStatus result.
        """
        if not manifest.engine_version_min and not manifest.engine_version_max:
            return CompatibilityStatus.UNKNOWN

        engine_parts = self._parse_semver(self._engine_version)

        if manifest.engine_version_min:
            min_parts = self._parse_semver(manifest.engine_version_min)
            if self._compare_semver(engine_parts, min_parts) < 0:
                return CompatibilityStatus.NEEDS_UPDATE

        if manifest.engine_version_max:
            max_parts = self._parse_semver(manifest.engine_version_max)
            if self._compare_semver(engine_parts, max_parts) > 0:
                return CompatibilityStatus.INCOMPATIBLE

        return CompatibilityStatus.COMPATIBLE

    @staticmethod
    def _parse_semver(version: str) -> Tuple[int, int, int]:
        """Parse a semantic version string into a (major, minor, patch) tuple."""
        try:
            parts = version.strip().split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)
        except (ValueError, IndexError):
            return (0, 0, 0)

    @staticmethod
    def _compare_semver(
        a: Tuple[int, int, int], b: Tuple[int, int, int]
    ) -> int:
        """Compare two semantic version tuples. Returns -1, 0, or 1."""
        for i in range(3):
            if a[i] < b[i]:
                return -1
            if a[i] > b[i]:
                return 1
        return 0

    # ------------------------------------------------------------------
    # Extension Marketplace
    # ------------------------------------------------------------------

    def publish_to_marketplace(self, manifest: ExtensionManifest) -> Dict[str, Any]:
        """Publish an extension to the marketplace for discovery.

        Args:
            manifest: The extension manifest to publish.

        Returns:
            A dict with publication status information.
        """
        if manifest.extension_id in self._marketplace_extensions:
            return {
                "status": "already_published",
                "extension_id": manifest.extension_id,
            }

        self._marketplace_extensions[manifest.extension_id] = manifest

        # Update category count
        cat_val = manifest.category.value
        if cat_val not in self._category_entries:
            entry = ExtensionCategoryEntry(
                category_type=manifest.category,
                name=manifest.category.value,
            )
            self._category_entries[cat_val] = entry
        self._category_entries[cat_val].extension_count += 1

        return {
            "status": "published",
            "extension_id": manifest.extension_id,
            "name": manifest.name,
            "version": manifest.version,
        }

    def list_marketplace_extensions(
        self,
        category: Optional[ExtensionCategory] = None,
    ) -> List[ExtensionManifest]:
        """List extensions available in the marketplace.

        Args:
            category: Optional category filter.

        Returns:
            A list of ExtensionManifest objects.
        """
        results: List[ExtensionManifest] = []
        for manifest in self._marketplace_extensions.values():
            if category is not None and manifest.category != category:
                continue
            results.append(manifest)
        return results

    def search_marketplace(self, query: str) -> List[ExtensionManifest]:
        """Search marketplace extensions by name, description, or tags.

        Args:
            query: The case-insensitive search query.

        Returns:
            A list of matching ExtensionManifest objects.
        """
        query_lower = query.lower()
        results: List[ExtensionManifest] = []
        for manifest in self._marketplace_extensions.values():
            if (
                query_lower in manifest.name.lower()
                or query_lower in manifest.description.lower()
                or any(query_lower in tag.lower() for tag in manifest.tags)
            ):
                results.append(manifest)
        return results

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Retrieve comprehensive platform status and statistics.

        Returns:
            A dict with counts, engine version, and category breakdown.
        """
        states_count: Dict[str, int] = {}
        for instance in self._extensions.values():
            s = instance.state.value
            states_count[s] = states_count.get(s, 0) + 1

        categories_count: Dict[str, int] = {}
        for instance in self._extensions.values():
            c = instance.manifest.category.value
            categories_count[c] = categories_count.get(c, 0) + 1

        return {
            "engine_version": self._engine_version,
            "total_registered": self._total_registered,
            "total_loaded": self._total_loaded,
            "total_activated": self._total_activated,
            "total_behaviors": self._total_behaviors,
            "total_objects": self._total_objects,
            "total_conditions": self._total_conditions,
            "total_actions": self._total_actions,
            "total_effects": self._total_effects,
            "error_count": self._error_count,
            "active_extensions": states_count.get("active", 0),
            "extension_states": states_count,
            "category_breakdown": categories_count,
            "marketplace_count": len(self._marketplace_extensions),
        }

    def reset(self) -> None:
        """Reset all platform data to its initial empty state."""
        self._extensions.clear()
        self._manifests.clear()
        self._dependencies.clear()
        self._behaviors.clear()
        self._objects.clear()
        self._conditions.clear()
        self._actions.clear()
        self._effects.clear()
        self._marketplace_extensions.clear()
        self._category_entries.clear()

        self._total_registered = 0
        self._total_loaded = 0
        self._total_activated = 0
        self._total_behaviors = 0
        self._total_objects = 0
        self._total_conditions = 0
        self._total_actions = 0
        self._total_effects = 0
        self._error_count = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _get_instance(self, extension_id: str) -> ExtensionInstance:
        """Retrieve an extension instance or raise KeyError.

        Args:
            extension_id: The unique identifier of the extension.

        Returns:
            The ExtensionInstance.

        Raises:
            KeyError: If the extension is not found.
        """
        if extension_id not in self._extensions:
            raise KeyError(f"Extension '{extension_id}' not found in registry.")
        return self._extensions[extension_id]

    def _find_dependents(self, extension_id: str) -> List[str]:
        """Find all active extensions that depend on the given extension.

        Args:
            extension_id: The extension to check for dependents.

        Returns:
            A list of extension IDs that depend on this extension.
        """
        dependents: List[str] = []
        for eid, deps in self._dependencies.items():
            for dep in deps:
                if dep.extension_id == extension_id and dep.required:
                    instance = self._extensions.get(eid)
                    if instance and instance.state == ExtensionState.ACTIVE:
                        dependents.append(eid)
                        break
        return dependents

    def set_engine_version(self, version: str) -> None:
        """Update the engine version used for compatibility checks.

        Args:
            version: The semantic version string (e.g., "2.1.0").
        """
        self._engine_version = version

    def get_engine_version(self) -> str:
        """Get the current engine version.

        Returns:
            The engine version string.
        """
        return self._engine_version


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_engine_extension_platform() -> EngineExtensionPlatform:
    """Return the singleton EngineExtensionPlatform instance.

    Usage:
        eep = get_engine_extension_platform()
        manifest = ExtensionManifest(name="My Extension", version="1.0.0")
        eep.register_extension(manifest)
    """
    return EngineExtensionPlatform()