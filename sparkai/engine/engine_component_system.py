"""
SparkLabs Engine - Component-Based Game Object System

A composable, data-driven architecture for game object management inspired
by the component pattern used in Phaser, GDevelop, and Godot. Game objects
are composed of reusable components that define behavior, avoiding deep
inheritance hierarchies. Each component type is defined by a
ComponentDefinition, and runtime instances are tracked as ComponentInstance
records attached to GameEntity containers.

Architecture:
  ComponentRegistry (Singleton)
    |-- ComponentDefinition  — reusable component template with metadata
    |-- ComponentInstance    — runtime component attached to an entity
    |-- GameEntity           — lightweight container aggregating components
    |-- ComponentCategory    — functional classification of components
    |-- ComponentLifecycle   — runtime state machine for component instances
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ComponentCategory(Enum):
    """Functional classification of component types."""
    TRANSFORM = "transform"
    RENDERER = "renderer"
    COLLIDER = "collider"
    RIGIDBODY = "rigidbody"
    ANIMATOR = "animator"
    SCRIPT = "script"
    AUDIO = "audio"
    PARTICLE = "particle"
    UI = "ui"
    CAMERA = "camera"
    LIGHT = "light"
    NAVIGATION = "navigation"
    CUSTOM = "custom"


class ComponentLifecycle(Enum):
    """Runtime lifecycle state of a component instance."""
    CREATED = "created"
    INITIALIZED = "initialized"
    ENABLED = "enabled"
    DISABLED = "disabled"
    DESTROYED = "destroyed"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ComponentDefinition:
    """Reusable template that describes a component type.

    Each definition carries metadata about what the component does,
    which other components it requires or conflicts with, and the
    default property values used when creating a new instance.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: ComponentCategory = ComponentCategory.CUSTOM
    description: str = ""
    default_properties: Dict[str, Any] = field(default_factory=dict)
    required_components: List[str] = field(default_factory=list)
    incompatible_with: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "default_properties": dict(self.default_properties),
            "required_components": list(self.required_components),
            "incompatible_with": list(self.incompatible_with),
        }


@dataclass
class ComponentInstance:
    """Runtime instance of a component attached to a specific entity.

    Holds the current property values, lifecycle state, and enabled
    flag. Properties are initialized from the ComponentDefinition's
    default_properties and may be overridden at creation time.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    definition_id: str = ""
    entity_id: str = ""
    lifecycle: ComponentLifecycle = ComponentLifecycle.CREATED
    enabled: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "definition_id": self.definition_id,
            "entity_id": self.entity_id,
            "lifecycle": self.lifecycle.value,
            "enabled": self.enabled,
            "properties": dict(self.properties),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class GameEntity:
    """Lightweight container that aggregates components to form a game object.

    Entities carry no intrinsic behavior; all functionality comes from
    attached components. Each entity has a type tag, a set of component
    instance IDs, and metadata for organizational purposes.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    entity_type: str = ""
    enabled: bool = True
    components: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "enabled": self.enabled,
            "components": dict(self.components),
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------------
# Pre-Defined Component Definitions
# ---------------------------------------------------------------------------


_PREDEFINED_COMPONENT_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "transform": {
        "name": "Transform",
        "category": ComponentCategory.TRANSFORM,
        "description": "Spatial position, rotation, and scale for an entity in world space.",
        "default_properties": {
            "position_x": 0.0,
            "position_y": 0.0,
            "position_z": 0.0,
            "rotation_x": 0.0,
            "rotation_y": 0.0,
            "rotation_z": 0.0,
            "scale_x": 1.0,
            "scale_y": 1.0,
            "scale_z": 1.0,
        },
        "required_components": [],
        "incompatible_with": [],
    },
    "sprite_renderer": {
        "name": "Sprite Renderer",
        "category": ComponentCategory.RENDERER,
        "description": "2D visual representation with texture, color, and sorting properties.",
        "default_properties": {
            "texture_id": "",
            "color_r": 255,
            "color_g": 255,
            "color_b": 255,
            "color_a": 255,
            "width": 32,
            "height": 32,
            "pivot_x": 0.5,
            "pivot_y": 0.5,
            "flip_x": False,
            "flip_y": False,
            "sorting_layer": 0,
            "sorting_order": 0,
            "visible": True,
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
    "box_collider": {
        "name": "Box Collider",
        "category": ComponentCategory.COLLIDER,
        "description": "Axis-aligned rectangular collision boundary with trigger support.",
        "default_properties": {
            "width": 32.0,
            "height": 32.0,
            "offset_x": 0.0,
            "offset_y": 0.0,
            "is_trigger": False,
            "physics_material": "default",
            "collision_layer": 0,
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
    "circle_collider": {
        "name": "Circle Collider",
        "category": ComponentCategory.COLLIDER,
        "description": "Circular collision boundary with configurable radius and trigger mode.",
        "default_properties": {
            "radius": 16.0,
            "offset_x": 0.0,
            "offset_y": 0.0,
            "is_trigger": False,
            "physics_material": "default",
            "collision_layer": 0,
        },
        "required_components": ["transform"],
        "incompatible_with": ["box_collider"],
    },
    "rigidbody_2d": {
        "name": "Rigidbody 2D",
        "category": ComponentCategory.RIGIDBODY,
        "description": "Physics-driven motion with mass, drag, velocity, and gravity response.",
        "default_properties": {
            "mass": 1.0,
            "drag": 0.0,
            "angular_drag": 0.05,
            "gravity_scale": 1.0,
            "is_kinematic": False,
            "velocity_x": 0.0,
            "velocity_y": 0.0,
            "angular_velocity": 0.0,
            "constraints": "none",
            "sleep_threshold": 0.005,
            "interpolation": "none",
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
    "animator": {
        "name": "Animator",
        "category": ComponentCategory.ANIMATOR,
        "description": "Animation state machine controlling sprite playback and transitions.",
        "default_properties": {
            "controller_id": "",
            "current_state": "idle",
            "speed": 1.0,
            "transition_time": 0.15,
            "parameters": {},
            "layer_count": 1,
            "apply_root_motion": False,
            "culling_mode": "always_animate",
            "update_mode": "normal",
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
    "script_behavior": {
        "name": "Script Behavior",
        "category": ComponentCategory.SCRIPT,
        "description": "Custom script-driven behavior with configurable update intervals and parameters.",
        "default_properties": {
            "script_id": "",
            "script_source": "",
            "update_interval": 0.0,
            "parameters": {},
            "run_on_start": True,
            "run_on_enable": True,
            "run_on_disable": True,
            "run_on_destroy": True,
        },
        "required_components": [],
        "incompatible_with": [],
    },
    "audio_source": {
        "name": "Audio Source",
        "category": ComponentCategory.AUDIO,
        "description": "Playback source for sound effects and music with spatial controls.",
        "default_properties": {
            "audio_clip_id": "",
            "volume": 1.0,
            "pitch": 1.0,
            "pan_stereo": 0.0,
            "spatial_blend": 0.0,
            "loop": False,
            "play_on_start": False,
            "min_distance": 1.0,
            "max_distance": 50.0,
            "rolloff_mode": "logarithmic",
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
    "particle_emitter": {
        "name": "Particle Emitter",
        "category": ComponentCategory.PARTICLE,
        "description": "Emits and manages particle effects with configurable burst and rate controls.",
        "default_properties": {
            "particle_system_id": "",
            "emission_rate": 10.0,
            "max_particles": 100,
            "duration": 5.0,
            "looping": True,
            "start_delay": 0.0,
            "burst_count": 0,
            "burst_interval": 0.0,
            "simulation_space": "world",
            "play_on_start": True,
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
    "ui_element": {
        "name": "UI Element",
        "category": ComponentCategory.UI,
        "description": "Canvas-bound UI widget with anchoring, sizing, and interaction properties.",
        "default_properties": {
            "widget_type": "panel",
            "anchor_x": 0.5,
            "anchor_y": 0.5,
            "pivot_x": 0.5,
            "pivot_y": 0.5,
            "width": 100.0,
            "height": 100.0,
            "color_r": 255,
            "color_g": 255,
            "color_b": 255,
            "color_a": 255,
            "interactable": False,
            "visible": True,
            "sorting_order": 0,
        },
        "required_components": [],
        "incompatible_with": [],
    },
    "camera_2d": {
        "name": "Camera 2D",
        "category": ComponentCategory.CAMERA,
        "description": "2D viewport camera with follow targets, bounds, and zoom controls.",
        "default_properties": {
            "orthographic_size": 5.0,
            "near_clip": 0.1,
            "far_clip": 1000.0,
            "background_color_r": 0,
            "background_color_g": 0,
            "background_color_b": 0,
            "background_color_a": 255,
            "viewport_x": 0.0,
            "viewport_y": 0.0,
            "viewport_width": 1.0,
            "viewport_height": 1.0,
            "zoom": 1.0,
            "follow_target_id": "",
            "follow_smoothness": 0.1,
            "bounds_min_x": 0.0,
            "bounds_min_y": 0.0,
            "bounds_max_x": 0.0,
            "bounds_max_y": 0.0,
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
    "light_source": {
        "name": "Light Source",
        "category": ComponentCategory.LIGHT,
        "description": "Point or directional light with configurable color, intensity, and range.",
        "default_properties": {
            "light_type": "point",
            "color_r": 255,
            "color_g": 255,
            "color_b": 255,
            "intensity": 1.0,
            "range": 10.0,
            "spot_angle": 30.0,
            "inner_spot_angle": 15.0,
            "cast_shadows": False,
            "shadow_strength": 0.5,
            "render_layer_mask": 0,
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
    "navigation_agent": {
        "name": "Navigation Agent",
        "category": ComponentCategory.NAVIGATION,
        "description": "Pathfinding agent with configurable speed, avoidance, and target tracking.",
        "default_properties": {
            "agent_radius": 0.5,
            "agent_height": 2.0,
            "max_speed": 3.5,
            "acceleration": 8.0,
            "stopping_distance": 0.1,
            "auto_braking": True,
            "avoidance_priority": 50,
            "path_update_interval": 0.25,
            "target_entity_id": "",
            "target_position_x": 0.0,
            "target_position_y": 0.0,
        },
        "required_components": ["transform"],
        "incompatible_with": [],
    },
}


def _build_default_definitions() -> Dict[str, ComponentDefinition]:
    """Build ComponentDefinition instances from the pre-defined templates."""
    definitions: Dict[str, ComponentDefinition] = {}
    for key, preset in _PREDEFINED_COMPONENT_DEFINITIONS.items():
        definition = ComponentDefinition(
            name=preset["name"],
            category=preset["category"],
            description=preset["description"],
            default_properties=dict(preset["default_properties"]),
            required_components=list(preset["required_components"]),
            incompatible_with=list(preset["incompatible_with"]),
        )
        definitions[definition.id] = definition
    return definitions


# ---------------------------------------------------------------------------
# ComponentRegistry — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class ComponentRegistry:
    """Central registry for component definitions, entity management, and
    component instance lifecycle.

    Entities are lightweight containers that gain behavior through attached
    component instances. ComponentDefinitions describe reusable templates,
    and ComponentInstances hold runtime state. The registry enforces
    dependency and incompatibility rules when attaching components.

    Thread-safe via a reentrant lock. Use get_component_registry() or
    ComponentRegistry.get_instance() to obtain the singleton.

    Usage:
        registry = get_component_registry()
        registry.initialize()
        entity = registry.create_entity("Player", "character")
        registry.add_component(entity.id, "transform", {})
        registry.add_component(entity.id, "sprite_renderer",
                                {"texture_id": "player_sprite"})
        status = registry.get_status()
    """

    _instance: Optional["ComponentRegistry"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "ComponentRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._definitions: Dict[str, ComponentDefinition] = {}
        self._instances: Dict[str, ComponentInstance] = {}
        self._entities: Dict[str, GameEntity] = {}
        self._entity_component_index: Dict[str, Dict[str, str]] = defaultdict(dict)
        self._component_entity_index: Dict[str, List[str]] = defaultdict(list)
        self._tag_index: Dict[str, List[str]] = defaultdict(list)
        self._definition_name_index: Dict[str, str] = {}
        self._operation_count: int = 0
        self._error_count: int = 0
        self._is_initialized: bool = False
        self._is_shutdown: bool = False
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "ComponentRegistry":
        """Get the singleton ComponentRegistry instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Set up the registry with default component definitions.

        Loads all pre-defined component templates (Transform, Sprite
        Renderer, Collider, Rigidbody, etc.) into the registry so they
        are available for entity construction. This should be called
        once during engine startup before any entities are created.
        """
        with self._lock:
            if self._is_shutdown:
                return
            self._definitions = _build_default_definitions()
            for definition in self._definitions.values():
                self._definition_name_index[definition.name.lower()] = definition.id
            self._is_initialized = True

    # ------------------------------------------------------------------
    # Component Definition Management
    # ------------------------------------------------------------------

    def register_component_definition(self, definition: ComponentDefinition) -> str:
        """Register a new component type in the registry.

        Args:
            definition: The ComponentDefinition to register.

        Returns:
            The definition ID on success. An existing definition with
            the same name is overwritten.
        """
        with self._lock:
            self._definitions[definition.id] = definition
            self._definition_name_index[definition.name.lower()] = definition.id
            self._operation_count += 1
            return definition.id

    def get_component_definition(self, definition_id: str) -> Optional[ComponentDefinition]:
        """Retrieve a component definition by its ID.

        Args:
            definition_id: The unique identifier of the definition.

        Returns:
            The ComponentDefinition if found, or None.
        """
        with self._lock:
            return self._definitions.get(definition_id)

    def list_component_definitions(self) -> List[ComponentDefinition]:
        """List all registered component definitions.

        Returns:
            A list of all ComponentDefinition objects in the registry.
        """
        with self._lock:
            return list(self._definitions.values())

    # ------------------------------------------------------------------
    # Entity Management
    # ------------------------------------------------------------------

    def create_entity(self, name: str = "", entity_type: str = "") -> GameEntity:
        """Create a new game entity with the given name and type.

        Args:
            name: Human-readable name for the entity.
            entity_type: Semantic type tag (e.g. 'character', 'prop').

        Returns:
            The newly created GameEntity.
        """
        with self._lock:
            entity = GameEntity(
                name=name,
                entity_type=entity_type,
            )
            self._entities[entity.id] = entity
            self._entity_component_index[entity.id] = {}
            self._operation_count += 1
            return entity

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and all of its attached components.

        All ComponentInstance records owned by the entity are removed
        from the registry and from the component-entity index.

        Args:
            entity_id: The unique identifier of the entity to remove.

        Returns:
            True if the entity was removed, False if not found.
        """
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                self._error_count += 1
                return False

            component_ids = list(entity.components.values())
            for comp_id in component_ids:
                self._remove_component_internal(entity_id, comp_id)

            for tag in entity.tags:
                tag_list = self._tag_index.get(tag, [])
                if entity_id in tag_list:
                    tag_list.remove(entity_id)

            del self._entities[entity_id]
            self._entity_component_index.pop(entity_id, None)
            self._operation_count += 1
            return True

    def get_entity(self, entity_id: str) -> Optional[GameEntity]:
        """Retrieve an entity by its ID.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            The GameEntity if found, or None.
        """
        with self._lock:
            return self._entities.get(entity_id)

    # ------------------------------------------------------------------
    # Component Instance Management
    # ------------------------------------------------------------------

    def _resolve_definition_id(self, definition_id: str) -> Optional[str]:
        """Resolve a definition ID that may be a name alias."""
        if definition_id in self._definitions:
            return definition_id
        return self._definition_name_index.get(definition_id.lower())

    def add_component(
        self,
        entity_id: str,
        definition_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[ComponentInstance]:
        """Add a component instance to an entity.

        Creates a ComponentInstance from the given definition, merges
        any provided property overrides, and attaches it to the entity.
        Dependency and incompatibility checks are performed against the
        definition's constraints.

        Args:
            entity_id: The entity to attach the component to.
            definition_id: The definition ID or name to instantiate.
            properties: Optional property overrides merged over defaults.

        Returns:
            The ComponentInstance if added, or None on failure.
        """
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                self._error_count += 1
                return None

            resolved_id = self._resolve_definition_id(definition_id)
            if resolved_id is None:
                self._error_count += 1
                return None

            definition = self._definitions.get(resolved_id)
            if definition is None:
                self._error_count += 1
                return None

            # Check incompatibility
            for incompatible_def_id in definition.incompatible_with:
                incompatible_resolved = self._resolve_definition_id(incompatible_def_id)
                if incompatible_resolved and incompatible_resolved in entity.components:
                    self._error_count += 1
                    return None

            # Check required components
            for required_def_id in definition.required_components:
                required_resolved = self._resolve_definition_id(required_def_id)
                if required_resolved and required_resolved not in entity.components:
                    self._error_count += 1
                    return None

            merged_properties = dict(definition.default_properties)
            if properties:
                merged_properties.update(properties)

            now = _time_module.time()
            instance = ComponentInstance(
                definition_id=resolved_id,
                entity_id=entity_id,
                lifecycle=ComponentLifecycle.INITIALIZED,
                enabled=True,
                properties=merged_properties,
                created_at=now,
                updated_at=now,
            )

            self._instances[instance.id] = instance
            entity.components[resolved_id] = instance.id
            self._entity_component_index[entity_id][resolved_id] = instance.id
            self._component_entity_index[resolved_id].append(entity_id)
            entity.updated_at = now
            self._operation_count += 1
            return instance

    def remove_component(self, entity_id: str, component_id: str) -> bool:
        """Remove a component instance from an entity.

        Args:
            entity_id: The entity that owns the component.
            component_id: The component instance ID to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            return self._remove_component_internal(entity_id, component_id)

    def _remove_component_internal(self, entity_id: str, component_id: str) -> bool:
        """Internal removal without lock acquisition."""
        instance = self._instances.get(component_id)
        if instance is None or instance.entity_id != entity_id:
            self._error_count += 1
            return False

        instance.lifecycle = ComponentLifecycle.DESTROYED
        instance.updated_at = _time_module.time()

        entity = self._entities.get(entity_id)
        if entity is not None:
            for def_id, inst_id in list(entity.components.items()):
                if inst_id == component_id:
                    del entity.components[def_id]
                    break
            entity.updated_at = _time_module.time()

        self._entity_component_index.get(entity_id, {}).pop(instance.definition_id, None)

        def_entity_list = self._component_entity_index.get(instance.definition_id, [])
        if entity_id in def_entity_list:
            def_entity_list.remove(entity_id)

        del self._instances[component_id]
        self._operation_count += 1
        return True

    def get_component(
        self, entity_id: str, component_id: str
    ) -> Optional[ComponentInstance]:
        """Get a specific component instance from an entity.

        Args:
            entity_id: The entity that owns the component.
            component_id: The component instance ID.

        Returns:
            The ComponentInstance if found, or None.
        """
        with self._lock:
            instance = self._instances.get(component_id)
            if instance is None or instance.entity_id != entity_id:
                return None
            return instance

    def get_entity_components(self, entity_id: str) -> List[ComponentInstance]:
        """Get all component instances attached to an entity.

        Args:
            entity_id: The entity ID.

        Returns:
            A list of ComponentInstance objects attached to the entity.
        """
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                return []
            result: List[ComponentInstance] = []
            for inst_id in entity.components.values():
                inst = self._instances.get(inst_id)
                if inst is not None:
                    result.append(inst)
            return result

    def enable_component(self, entity_id: str, component_id: str) -> bool:
        """Enable a component instance.

        Args:
            entity_id: The entity that owns the component.
            component_id: The component instance ID.

        Returns:
            True if the component was enabled, False if not found.
        """
        with self._lock:
            instance = self._instances.get(component_id)
            if instance is None or instance.entity_id != entity_id:
                self._error_count += 1
                return False
            instance.enabled = True
            instance.lifecycle = ComponentLifecycle.ENABLED
            instance.updated_at = _time_module.time()
            self._operation_count += 1
            return True

    def disable_component(self, entity_id: str, component_id: str) -> bool:
        """Disable a component instance.

        Args:
            entity_id: The entity that owns the component.
            component_id: The component instance ID.

        Returns:
            True if the component was disabled, False if not found.
        """
        with self._lock:
            instance = self._instances.get(component_id)
            if instance is None or instance.entity_id != entity_id:
                self._error_count += 1
                return False
            instance.enabled = False
            instance.lifecycle = ComponentLifecycle.DISABLED
            instance.updated_at = _time_module.time()
            self._operation_count += 1
            return True

    def update_component_properties(
        self,
        entity_id: str,
        component_id: str,
        properties: Dict[str, Any],
    ) -> bool:
        """Update the property values of a component instance.

        Merges the provided properties into the existing property
        dictionary. Existing keys are overwritten; new keys are added.

        Args:
            entity_id: The entity that owns the component.
            component_id: The component instance ID.
            properties: Dictionary of property updates to apply.

        Returns:
            True if updated, False if the component was not found.
        """
        with self._lock:
            instance = self._instances.get(component_id)
            if instance is None or instance.entity_id != entity_id:
                self._error_count += 1
                return False
            instance.properties.update(properties)
            instance.updated_at = _time_module.time()
            self._operation_count += 1
            return True

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def find_entities_by_component(self, definition_id: str) -> List[GameEntity]:
        """Find all entities that have a specific component type attached.

        Args:
            definition_id: The definition ID or name to search for.

        Returns:
            A list of GameEntity objects that have the component.
        """
        with self._lock:
            resolved_id = self._resolve_definition_id(definition_id)
            if resolved_id is None:
                return []
            entity_ids = self._component_entity_index.get(resolved_id, [])
            return [
                self._entities[eid]
                for eid in entity_ids
                if eid in self._entities
            ]

    # ------------------------------------------------------------------
    # Status and Shutdown
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a snapshot of the registry's current state.

        Includes entity counts, component counts, initialization state,
        and operational statistics.

        Returns:
            A dictionary with registry status information.
        """
        with self._lock:
            enabled_entities = sum(
                1 for e in self._entities.values() if e.enabled
            )
            enabled_components = sum(
                1 for c in self._instances.values() if c.enabled
            )
            definition_counts: Dict[str, int] = {}
            for instance in self._instances.values():
                name = instance.definition_id
                definition_counts[name] = definition_counts.get(name, 0) + 1

            category_counts: Dict[str, int] = {}
            for definition in self._definitions.values():
                cat = definition.category.value
                count = len(self._component_entity_index.get(definition.id, []))
                if count > 0:
                    category_counts[cat] = category_counts.get(cat, 0) + count

            return {
                "initialized": self._is_initialized,
                "shutdown": self._is_shutdown,
                "total_entities": len(self._entities),
                "enabled_entities": enabled_entities,
                "total_components": len(self._instances),
                "enabled_components": enabled_components,
                "total_definitions": len(self._definitions),
                "definition_names": list(self._definition_name_index.keys()),
                "definition_instance_counts": definition_counts,
                "category_distribution": category_counts,
                "tag_groups": len(self._tag_index),
                "operation_count": self._operation_count,
                "error_count": self._error_count,
            }

    def shutdown(self) -> None:
        """Perform a clean shutdown of the registry.

        Clears all entities, component instances, definitions, and
        index structures. The registry is marked as shut down and
        will reject further operations until re-initialized.
        """
        with self._lock:
            self._definitions.clear()
            self._instances.clear()
            self._entities.clear()
            self._entity_component_index.clear()
            self._component_entity_index.clear()
            self._tag_index.clear()
            self._definition_name_index.clear()
            self._is_initialized = False
            self._is_shutdown = True
            self._operation_count = 0
            self._error_count = 0


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------


def get_component_registry() -> ComponentRegistry:
    """Get the global ComponentRegistry singleton instance.

    Returns:
        The shared ComponentRegistry instance.
    """
    return ComponentRegistry.get_instance()